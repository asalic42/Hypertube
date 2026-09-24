"""
Lower resolution copies of the stored movies. They are encoded by the worker
after a movie is stored, one movie at a time, from the file kept in storage;
each becomes selectable in the player as soon as it is uploaded.
"""

import logging
import shutil

from django.db.models import Q
from django.utils import timezone

from movies_app.models import Download, Rendition
from movies_app.services import media, storage

logger = logging.getLogger(__name__)

# Download being encoded, so that the purge leaves its working directory alone.
in_progress = None


def storage_key(download, height):
    return f"{download.movie_id}/video_{height}p.mp4"


def remove_stored(download):
    """Forget the renditions of a download and erase its files from storage. Best effort."""
    storage.delete(download.storage_key)
    for key in download.renditions.exclude(storage_key="").values_list("storage_key", flat=True):
        storage.delete(key)
    download.renditions.all().delete()


def plan(download, source):
    """Read the frame size of the stored file and queue the lower resolutions worth encoding."""
    try:
        info = media.probe(source)
    except media.MediaError as error:
        logger.warning("download %s: frame size unknown, no rendition will be made: %s", download.pk, error)
        info = {"width": None, "height": None}
    download.width, download.height = info["width"], info["height"]
    download.renditions_planned = True
    download.save(update_fields=["width", "height", "renditions_planned", "updated_at"])
    for height in media.rendition_heights(download.height):
        Rendition.objects.get_or_create(download=download, height=height)


def next_download():
    """A stored movie whose renditions are still to plan or to encode, oldest first."""
    return (
        Download.objects.filter(status=Download.Status.READY)
        .filter(Q(renditions_planned=False) | Q(renditions__status=Rendition.Status.PENDING))
        .distinct()
        .order_by("completed_at", "pk")
        .first()
    )


def _encode(download, rendition, source, workdir):
    target = workdir / f"{rendition.height}p.mp4"
    key = storage_key(download, rendition.height)
    try:
        media.encode_rendition(source, target, rendition.height)
        width = media.probe(target)["width"]
        storage.upload_file(target, key, "video/mp4")
    except (media.MediaError, OSError, *storage.StorageError) as error:
        logger.exception("download %s: the %sp rendition failed", download.pk, rendition.height)
        Rendition.objects.filter(pk=rendition.pk).update(
            status=Rendition.Status.FAILED,
            error=str(error)[:1000],
            updated_at=timezone.now(),
        )
        return
    Rendition.objects.filter(pk=rendition.pk).update(
        status=Rendition.Status.READY,
        storage_key=key,
        storage_size=target.stat().st_size,
        content_type="video/mp4",
        width=width,
        updated_at=timezone.now(),
    )
    target.unlink(missing_ok=True)
    logger.info("download %s: %sp rendition stored as %s", download.pk, rendition.height, key)


def process_next():
    """Encode the missing renditions of one stored movie. True when there was something to do."""
    global in_progress  # noqa: PLW0603
    download = next_download()
    if download is None:
        return False

    in_progress = download.pk
    workdir = media.renditions_directory(download.pk)
    shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True)
    source = workdir / f"source{media.storage_suffix(download)}"
    try:
        try:
            storage.download_file(download.storage_key, source)
        except (*storage.StorageError, OSError) as error:
            # Without the source there is nothing to encode: give up on this movie rather than loop on it.
            logger.warning("download %s: stored file unavailable, no rendition will be made: %s", download.pk, error)
            Download.objects.filter(pk=download.pk).update(renditions_planned=True, updated_at=timezone.now())
            download.renditions.filter(status=Rendition.Status.PENDING).update(
                status=Rendition.Status.FAILED, error=str(error)[:1000], updated_at=timezone.now()
            )
            return True
        if not download.renditions_planned:
            plan(download, source)
        for rendition in download.renditions.filter(status=Rendition.Status.PENDING).order_by("-height"):
            _encode(download, rendition, source, workdir)
    finally:
        in_progress = None
        shutil.rmtree(workdir, ignore_errors=True)
    return True
