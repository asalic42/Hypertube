import logging
import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from urllib.parse import quote

import certifi
import libtorrent as lt
import requests
from django.db import connection
from django.utils import timezone

from movies_app.models import Download
from movies_app.services import catalog, http, media, storage

logger = logging.getLogger(__name__)

MAX_TORRENT_FILE_BYTES = 10 * 1024 * 1024
STALL_TIMEOUT = 180
# Pieces fetched ahead of a viewer who seeks into a part that is not downloaded yet.
SEEK_WINDOW = 8
TOP_PRIORITY = 7
# Re-checking data after a restart makes no network progress, yet is not a stall.
_BUSY_STATES = (lt.torrent_status.checking_files, lt.torrent_status.checking_resume_data)


class TorrentError(Exception):
    pass


@dataclass
class _Job:
    download_id: int
    handle: object
    first_piece: int
    last_piece: int
    last_done: int = -1
    last_progress_at: float = field(default_factory=time.monotonic)
    # Bitfield of the previous tick: a piece is advertised one tick after
    # libtorrent reports it, which leaves time for the data to reach the file.
    previous_pieces: bytes = b""
    applied_offset: int | None = None
    finalizer: object = None
    # Relative indexes of the boundary pieces whose video bytes were fetched from a web seed.
    patched: set = field(default_factory=set)


def _select_video(files):
    """Index of the file to stream: a browser-ready one when there is, else the largest video."""
    videos = [
        index
        for index in range(files.num_files())
        if files.file_path(index).lower().endswith(media.VIDEO_EXTENSIONS)
    ]
    if not videos:
        raise TorrentError("the torrent contains no video file")
    ready = [index for index in videos if not media.needs_transcode(files.file_path(index))]
    return max(ready or videos, key=files.file_size)


class TorrentEngine:
    """Owns the only libtorrent session. Jobs and their progress live in the Download table."""

    def __init__(self, listen_port=6881):
        # The OpenSSL bundled with libtorrent does not look at the system CA store:
        # without one, the HTTPS web seeds of archive.org fail certificate verification.
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        self.session = lt.session(
            {
                "listen_interfaces": f"0.0.0.0:{listen_port}",
                "user_agent": http.USER_AGENT,
                "active_downloads": 8,
                "active_limit": 20,
            }
        )
        self.jobs = {}
        self.finalizers = ThreadPoolExecutor(max_workers=2, thread_name_prefix="finalize")

    # --- lifecycle ---

    def tick(self):
        active = Download.objects.filter(status__in=Download.ACTIVE_STATUSES).select_related("torrent", "movie")
        rows = {download.pk: download for download in active}

        for download_id in [pk for pk in self.jobs if pk not in rows]:
            # The row is gone (purged or deleted): drop the torrent and its data.
            self._drop(self.jobs[download_id], delete_files=True)

        for download_id, download in rows.items():
            try:
                if download_id not in self.jobs:
                    self._start(download)
                else:
                    self._update(self.jobs[download_id], download)
            except TorrentError as error:
                self._fall_back(download, str(error))

    def shutdown(self):
        self.session.pause()
        self.finalizers.shutdown(wait=False, cancel_futures=True)

    # --- starting a job ---

    def _load_torrent(self, download, directory):
        meta_path = directory / f"{download.torrent_id}.torrent"
        if meta_path.exists():
            data = meta_path.read_bytes()
        else:
            try:
                data = http.get(download.torrent.torrent_url, timeout=(5, 30)).content
            except requests.RequestException as error:
                raise TorrentError(f"could not fetch the torrent file: {error}") from error
            if len(data) > MAX_TORRENT_FILE_BYTES:
                raise TorrentError("the torrent file is too large")
            meta_path.write_bytes(data)
        try:
            return lt.torrent_info(lt.bdecode(data))
        except RuntimeError as error:
            meta_path.unlink(missing_ok=True)
            raise TorrentError(f"invalid torrent file: {error}") from error

    def _start(self, download):
        if download.torrent is None:
            candidates = catalog.candidate_torrents(download.movie, exclude_ids=download.attempted_torrent_ids)
            if not candidates:
                raise TorrentError("no torrent available for this movie")
            download.torrent = candidates[0]
            download.save(update_fields=["torrent", "updated_at"])

        directory = media.download_directory(download.pk)
        directory.mkdir(parents=True, exist_ok=True)
        info = self._load_torrent(download, directory)
        files = info.files()
        video = _select_video(files)

        offset, size, piece_length = files.file_offset(video), files.file_size(video), info.piece_length()
        download.local_path = f"{download.pk}/data/{files.file_path(video)}"
        try:
            media.local_video_path(download)
        except media.MediaError as error:
            raise TorrentError(f"unsafe file name in torrent: {error}") from error

        first_piece = offset // piece_length
        last_piece = (offset + max(size, 1) - 1) // piece_length
        # The video is selected piece by piece rather than with file priorities:
        # libtorrent web seeds skip the pieces touching a file of priority 0,
        # which are precisely the first and last pieces of the video.
        priorities = [0] * info.num_pieces()
        priorities[first_piece : last_piece + 1] = [4] * (last_piece - first_piece + 1)
        # Players read the end of the file first when the MP4 index is stored there.
        for piece in (first_piece, min(first_piece + 1, last_piece), max(last_piece - 1, first_piece), last_piece):
            priorities[piece] = TOP_PRIORITY

        params = lt.add_torrent_params()
        params.ti = info
        params.save_path = str(directory / "data")
        params.storage_mode = lt.storage_mode_t.storage_mode_sparse
        params.piece_priorities = priorities
        params.flags |= lt.torrent_flags.sequential_download
        handle = self.session.add_torrent(params)

        download.status = Download.Status.DOWNLOADING
        download.file_size = size
        download.file_offset = offset
        download.piece_length = piece_length
        download.needs_transcode = media.needs_transcode(files.file_path(video))
        download.error = ""
        download.save()

        job = _Job(download.pk, handle, first_piece, last_piece)
        self.jobs[download.pk] = job
        threading.Thread(
            target=_patch_boundaries,
            args=(job, info, video, media.local_video_path(download)),
            daemon=True,
        ).start()
        logger.info("download %s started: %s", download.pk, files.file_path(video))

    # --- following a job ---

    def _update(self, job, download):
        if job.finalizer is not None:
            # Conversion and upload are running; tick() drops the job once the row leaves the active statuses.
            return

        status = job.handle.status()
        if status.errc.value() != 0:
            raise TorrentError(status.errc.message())

        pieces = status.pieces
        current = bytes(
            1 if (piece < len(pieces) and pieces[piece]) or piece - job.first_piece in job.patched else 0
            for piece in range(job.first_piece, job.last_piece + 1)
        )
        finished = bool(current) and all(current)
        published = current if finished else (job.previous_pieces or bytes(len(current)))
        job.previous_pieces = current
        self._publish_pieces(job.download_id, published)

        contiguous = len(published) if all(published) else published.index(0)
        buffered = 0
        if contiguous:
            buffered = (job.first_piece + contiguous) * download.piece_length - download.file_offset
        download.buffered_bytes = max(0, min(download.file_size, buffered))
        download.progress = sum(published) / len(published) if published else 0
        download.download_rate = status.download_rate
        download.num_peers = status.num_peers

        if download.requested_offset is not None and download.requested_offset != job.applied_offset:
            self._prioritize(job, download)

        if finished:
            download.status = Download.Status.PROCESSING
            download.progress = 1
            download.download_rate = 0
            download.buffered_bytes = download.file_size
            download.save()
            job.handle.unset_flags(lt.torrent_flags.auto_managed)
            job.handle.pause()
            job.handle.flush_cache()
            job.finalizer = self.finalizers.submit(finalize, download.pk)
            return

        if status.total_wanted_done > job.last_done or status.state in _BUSY_STATES:
            job.last_done = status.total_wanted_done
            job.last_progress_at = time.monotonic()
        elif time.monotonic() - job.last_progress_at > STALL_TIMEOUT:
            raise TorrentError("the download stalled: no peer or web seed is serving this torrent")

        download.save(update_fields=["buffered_bytes", "progress", "download_rate", "num_peers", "updated_at"])

    def _publish_pieces(self, download_id, pieces):
        path = media.pieces_path(download_id)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(pieces)
        temporary.replace(path)  # atomic: readers never see a partial bitfield

    def _prioritize(self, job, download):
        piece = (download.file_offset + download.requested_offset) // download.piece_length
        piece = max(job.first_piece, min(piece, job.last_piece))
        for rank, index in enumerate(range(piece, min(piece + SEEK_WINDOW, job.last_piece + 1))):
            job.handle.set_piece_deadline(index, 1000 * (rank + 1))
        job.applied_offset = download.requested_offset

    # --- ending a job ---

    def _drop(self, job, delete_files):
        if job.handle.is_valid():
            self.session.remove_torrent(job.handle, lt.options_t.delete_files if delete_files else 0)
        if delete_files:
            shutil.rmtree(media.download_directory(job.download_id), ignore_errors=True)
        self.jobs.pop(job.download_id, None)

    def _fall_back(self, download, reason):
        """Give the next best torrent of the movie a chance before reporting a failure."""
        logger.warning("download %s: %s", download.pk, reason)
        job = self.jobs.get(download.pk)
        if job is not None:
            self._drop(job, delete_files=True)
        else:
            shutil.rmtree(media.download_directory(download.pk), ignore_errors=True)

        if download.torrent_id is not None:
            download.attempted_torrent_ids = [*download.attempted_torrent_ids, download.torrent_id]
        candidates = catalog.candidate_torrents(download.movie, exclude_ids=download.attempted_torrent_ids)
        download.torrent = candidates[0] if candidates else None
        download.status = Download.Status.QUEUED if candidates else Download.Status.FAILED
        download.error = "" if candidates else reason[:1000]
        download.progress = 0
        download.download_rate = 0
        download.num_peers = 0
        download.buffered_bytes = 0
        download.local_path = ""
        download.requested_offset = None
        download.save()


def _patch_boundaries(job, info, video, path):
    """
    The first and last pieces of the video usually overlap its neighbours in
    the torrent. archive.org rewrites some of those small files (thumbnails,
    metadata) after the torrent is made, so such a piece never passes its hash
    check again -- and players need the end of an MP4 before anything else.
    The video's own bytes of these two pieces are therefore read from the
    torrent's web seed (BEP 19); the piece then counts as available.
    """
    seeds = [seed["url"] for seed in info.web_seeds() if seed["url"].startswith(("https://", "http://"))]
    seeds.sort(key=lambda url: not url.startswith("https://"))
    if not seeds:
        return  # peer-only torrent: its pieces verify normally

    files, piece_length = info.files(), info.piece_length()
    offset, size = files.file_offset(video), files.file_size(video)
    base = seeds[0]
    url = base + quote(files.file_path(video)) if base.endswith("/") else base

    for piece in {job.first_piece, job.last_piece}:
        begin, end = piece * piece_length, (piece + 1) * piece_length
        if begin >= offset and end <= offset + size:
            continue  # entirely inside the video: nothing can corrupt its hash
        start = max(begin, offset) - offset
        stop = min(end, offset + size) - offset - 1
        try:
            data = http.get(url, headers={"Range": f"bytes={start}-{stop}"}, timeout=(5, 60)).content
        except requests.RequestException as error:
            logger.warning("download %s: boundary piece %s not patched: %s", job.download_id, piece, error)
            continue
        if len(data) != stop - start + 1:
            logger.warning("download %s: web seed ignored the range of piece %s", job.download_id, piece)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            os.pwrite(descriptor, data, start)
        finally:
            os.close(descriptor)
        job.patched.add(piece - job.first_piece)


def finalize(download_id):
    """Runs in a worker thread once the torrent is complete: convert if needed, then store."""
    try:
        download = Download.objects.get(pk=download_id)
        try:
            source = media.local_video_path(download)
            path, content_type = media.prepare_for_storage(source, media.download_directory(download_id))
            key = f"{download.movie_id}/video{path.suffix.lower()}"
            storage.upload_file(path, key, content_type)
        except (media.MediaError, OSError, *storage.StorageError) as error:
            logger.exception("download %s could not be stored", download_id)
            Download.objects.filter(pk=download_id).update(
                status=Download.Status.FAILED,
                error=str(error)[:1000],
                updated_at=timezone.now(),
            )
            return
        Download.objects.filter(pk=download_id).update(
            status=Download.Status.READY,
            storage_key=key,
            storage_size=path.stat().st_size,
            content_type=content_type,
            needs_transcode=False,
            completed_at=timezone.now(),
            updated_at=timezone.now(),
        )
        logger.info("download %s stored as %s", download_id, key)
    finally:
        connection.close()
