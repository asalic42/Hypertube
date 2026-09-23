import logging
import re
import subprocess
import threading
import time

from django.conf import settings
from django.core import signing
from django.db import connection

from movies_app.models import Download
from movies_app.services import media, storage

logger = logging.getLogger(__name__)

CHUNK_SIZE = 256 * 1024
POLL_INTERVAL = 0.5
STATUS_REFRESH_INTERVAL = 5
# How long a viewer may wait for a piece before the response is cut short.
PIECE_TIMEOUT = 90
MIN_BUFFER_BYTES = 8 * 1024 * 1024
MIN_BUFFER_RATIO = 0.03
TOKEN_SALT = "movies.stream"

_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")


class RangeNotSatisfiable(Exception):
    pass


# --- Stream tokens ----------------------------------------------------------
# <video> and <track> cannot send an Authorization header, so authenticated
# users are handed a signed, expiring token bound to one movie.


def make_token(user_id, movie_id):
    return signing.dumps({"u": str(user_id), "m": movie_id}, salt=TOKEN_SALT)


def read_token(token, movie_id):
    """Return the user id the token was issued to, or None when it is not valid for this movie."""
    try:
        payload = signing.loads(token, salt=TOKEN_SALT, max_age=settings.STREAM_TOKEN_MAX_AGE)
    except signing.BadSignature:
        return None
    return payload.get("u") if payload.get("m") == movie_id else None


# --- Byte ranges ------------------------------------------------------------


def parse_range(header, size):
    """
    Return the inclusive (start, end) asked by a Range header, or None to send
    the whole file. Multi-range requests are answered with the whole file too.
    """
    match = _RANGE.match((header or "").strip())
    if not match:
        return None
    first, last = match.groups()
    if not first and not last:
        return None
    if not first:
        length = int(last)
        if length == 0:
            raise RangeNotSatisfiable
        return max(0, size - length), size - 1
    start = int(first)
    if start >= size:
        raise RangeNotSatisfiable
    end = min(int(last), size - 1) if last else size - 1
    if end < start:
        raise RangeNotSatisfiable
    return start, end


def is_playable(download):
    """Enough of the beginning is there for playback to start smoothly."""
    if download.status in (Download.Status.READY, Download.Status.PROCESSING):
        return True
    if download.status != Download.Status.DOWNLOADING or not download.file_size:
        return False
    needed = max(MIN_BUFFER_BYTES, int(download.file_size * MIN_BUFFER_RATIO))
    return download.buffered_bytes >= min(needed, download.file_size)


# --- Sources ----------------------------------------------------------------


def iter_storage(key, start, end):
    body = storage.open_range(key, start, end)
    try:
        yield from body.iter_chunks(CHUNK_SIZE)
    finally:
        body.close()


def _wait_for_piece(download, position):
    """Block until the piece holding `position` is on disk. False when it will not come."""
    first_piece = download.file_offset // download.piece_length
    index = (download.file_offset + position) // download.piece_length - first_piece
    deadline = time.monotonic() + PIECE_TIMEOUT
    next_refresh = 0.0
    asked = False

    while True:
        try:
            pieces = media.pieces_path(download.pk).read_bytes()
        except OSError:
            pieces = b""
        if index < len(pieces) and pieces[index]:
            return True

        now = time.monotonic()
        if now >= next_refresh:
            next_refresh = now + STATUS_REFRESH_INTERVAL
            status = Download.objects.filter(pk=download.pk).values_list("status", flat=True).first()
            if status in (Download.Status.PROCESSING, Download.Status.READY):
                return True  # the torrent completed: every piece is there
            if status != Download.Status.DOWNLOADING:
                return False
        if not asked:
            # Tell the worker where this viewer is, so it fetches these pieces first.
            Download.objects.filter(pk=download.pk).update(requested_offset=position)
            asked = True
        if now >= deadline:
            return False
        time.sleep(POLL_INTERVAL)


def iter_local(download, start, end):
    """
    Read [start, end] of a file that is still downloading, waiting for the
    pieces as needed. Raises media.MediaError right away on an invalid path.
    """
    return _iter_local(download, media.local_video_path(download), start, end)


def _iter_local(download, path, start, end):
    complete = download.status != Download.Status.DOWNLOADING
    position = start
    handle = None
    try:
        while position <= end:
            if not complete and not _wait_for_piece(download, position):
                return
            if handle is None:
                handle = path.open("rb")
            piece_end = download.piece_length - (download.file_offset + position) % download.piece_length
            handle.seek(position)
            data = handle.read(min(CHUNK_SIZE, piece_end, end - position + 1))
            if not data:
                return
            position += len(data)
            yield data
    finally:
        if handle is not None:
            handle.close()


def _feed(process, download):
    try:
        for chunk in iter_local(download, 0, download.file_size - 1):
            process.stdin.write(chunk)
    except (BrokenPipeError, OSError, ValueError):
        pass  # ffmpeg exited or the viewer left
    finally:
        try:
            process.stdin.close()
        except OSError:
            pass
        connection.close()


def iter_transcoded(download):
    """
    Convert to fragmented MP4 on the fly. A complete file is read by ffmpeg
    directly; a partial one is piped in as its pieces arrive. Raises
    media.MediaError right away on an invalid path.
    """
    return _iter_transcoded(download, media.local_video_path(download))


def _iter_transcoded(download, path):
    complete = download.status != Download.Status.DOWNLOADING
    source = str(path) if complete else "pipe:0"
    process = subprocess.Popen(  # noqa: S603
        ["ffmpeg", "-v", "error", "-i", source, *media.LIVE_OUTPUT],
        stdin=subprocess.DEVNULL if complete else subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if not complete:
        threading.Thread(target=_feed, args=(process, download), daemon=True).start()
    try:
        while data := process.stdout.read(CHUNK_SIZE):
            yield data
    finally:
        process.kill()
        process.wait()
        process.stdout.close()
