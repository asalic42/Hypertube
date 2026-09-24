import logging
import shutil
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import DatabaseError, close_old_connections, connection
from django.db.models import F, Q
from django.utils import timezone

from movies_app.models import Download, Movie, Subtitle
from movies_app.services import catalog, media, renditions, storage, subtitles
from movies_app.services.torrent import TorrentEngine

logger = logging.getLogger(__name__)

SUBTITLES_INTERVAL = 5
RENDITIONS_INTERVAL = 10
CATALOG_INTERVAL = 60
PURGE_INTERVAL = 3600
CATALOG_BATCH = 40


def process_subtitles():
    for subtitle in Subtitle.objects.filter(status=Subtitle.Status.PENDING).select_related("movie")[:10]:
        try:
            subtitles.process(subtitle)
        except storage.StorageError as error:
            logger.warning("subtitle %s could not be stored: %s", subtitle.pk, error)


def process_renditions():
    """Encode the lower resolutions of the stored movies, one movie per run."""
    renditions.process_next()


def warm_catalog():
    """Keep the front page listing fresh and enrich the catalogue little by little."""
    catalog.refresh_popular()
    # Never-tried movies first: retries of unmatched ones must not starve the rest of the catalogue.
    queue = Movie.objects.order_by(F("metadata_fetched_at").asc(nulls_first=True), "-popularity")
    catalog.enrich_pending(queue, limit=CATALOG_BATCH, timeout=55)


def purge():
    """Erase the movies nobody watched for a month, then sweep leftover local data."""
    limit = timezone.now() - timedelta(days=settings.MOVIE_RETENTION_DAYS)
    stale = Download.objects.filter(status=Download.Status.READY).filter(
        Q(movie__last_watched_at__lt=limit) | Q(movie__last_watched_at__isnull=True, completed_at__lt=limit)
    )
    for download in stale:
        renditions.remove_stored(download)
        download.delete()
        logger.info("movie %s was not watched for %s days: erased", download.movie_id, settings.MOVIE_RETENTION_DAYS)

    root = media.download_root()
    if root.is_dir():
        active = {str(pk) for pk in Download.objects.filter(status__in=Download.ACTIVE_STATUSES).values_list("pk", flat=True)}
        for directory in root.iterdir():
            if directory.is_dir() and directory.name.isdigit() and directory.name not in active:
                shutil.rmtree(directory, ignore_errors=True)
    encoding = root / media.RENDITIONS_DIR
    if encoding.is_dir():
        for directory in encoding.iterdir():
            if directory.name != str(renditions.in_progress):
                shutil.rmtree(directory, ignore_errors=True)


class Command(BaseCommand):
    help = "Runs the BitTorrent downloads and the background jobs of the movies service."

    def handle(self, *args, **options):
        self.running = True
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)

        self.wait_for_database()
        engine = TorrentEngine(listen_port=settings.TORRENT_LISTEN_PORT)
        background = ThreadPoolExecutor(max_workers=1, thread_name_prefix="background")
        # Encoding a film takes long: it gets its own thread so that the other jobs keep running.
        encoder = ThreadPoolExecutor(max_workers=1, thread_name_prefix="renditions")
        tasks = [
            # [callable, interval, next run, running future, executor]
            [process_subtitles, SUBTITLES_INTERVAL, 0.0, None, background],
            [warm_catalog, CATALOG_INTERVAL, 0.0, None, background],
            [purge, PURGE_INTERVAL, 0.0, None, background],
            [process_renditions, RENDITIONS_INTERVAL, 0.0, None, encoder],
        ]
        self.stdout.write("torrent worker started")

        while self.running:
            try:
                close_old_connections()
                engine.tick()
            except DatabaseError:
                logger.exception("database error, retrying")
                time.sleep(5)
            except Exception:  # noqa: BLE001 - the worker must survive a bad torrent
                logger.exception("unexpected error in the torrent loop")

            now = time.monotonic()
            for task in tasks:
                function, interval, next_run, future, executor = task
                if now >= next_run and (future is None or future.done()):
                    task[2] = now + interval
                    task[3] = executor.submit(self.run_task, function)
            time.sleep(1)

        engine.shutdown()
        background.shutdown(wait=False, cancel_futures=True)
        encoder.shutdown(wait=False, cancel_futures=True)
        self.stdout.write("torrent worker stopped")

    def stop(self, *args):
        self.running = False

    def wait_for_database(self):
        """The web container applies the migrations: wait for it instead of racing it."""
        while self.running:
            try:
                Download.objects.exists()
                return
            except DatabaseError:
                connection.close()
                self.stdout.write("waiting for the database schema...")
                time.sleep(3)

    @staticmethod
    def run_task(function):
        try:
            function()
        except Exception:  # noqa: BLE001
            logger.exception("background task %s failed", function.__name__)
        finally:
            connection.close()
