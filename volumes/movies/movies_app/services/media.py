import json
import logging
import subprocess
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = (".mp4", ".m4v", ".webm", ".mkv", ".avi", ".mov", ".mpg", ".mpeg", ".ogv", ".wmv", ".flv", ".divx")
# Containers a browser plays natively; everything else is converted.
BROWSER_EXTENSIONS = (".mp4", ".m4v", ".webm")
BROWSER_VIDEO_CODECS = {"h264", "vp8", "vp9", "av1"}
BROWSER_AUDIO_CODECS = {"aac", "mp3", "opus", "vorbis"}

# Fragmented MP4 can be written to a pipe and played while it is produced.
LIVE_OUTPUT = (
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-ac", "2", "-b:a", "160k",
    "-movflags", "frag_keyframe+empty_moov+default_base_moof",
    "-f", "mp4", "pipe:1",
)  # fmt: skip


class MediaError(Exception):
    pass


def download_root():
    return Path(settings.MOVIES_DOWNLOAD_DIR).resolve()


def download_directory(download_id):
    return download_root() / str(download_id)


def pieces_path(download_id):
    return download_directory(download_id) / "pieces.bin"


def local_video_path(download):
    """Resolve the on-disk video, refusing any torrent-provided path that escapes the download root."""
    root = download_root()
    path = (root / download.local_path).resolve()
    if not download.local_path or not path.is_relative_to(root):
        raise MediaError("invalid local path")
    return path


def needs_transcode(file_name):
    return not file_name.lower().endswith(BROWSER_EXTENSIONS)


def _run(command, timeout):
    try:
        return subprocess.run(command, capture_output=True, timeout=timeout, check=True)  # noqa: S603
    except (subprocess.SubprocessError, OSError) as error:
        stderr = getattr(error, "stderr", b"") or b""
        raise MediaError(f"{command[0]} failed: {stderr.decode(errors='replace')[-500:] or error}") from error


def is_browser_ready(path):
    """True when both the container and the codecs are playable by Firefox and Chrome."""
    if needs_transcode(path.name):
        return False
    output = _run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name", "-of", "json", str(path)],
        timeout=120,
    ).stdout
    streams = json.loads(output or b"{}").get("streams", [])
    video = [stream["codec_name"] for stream in streams if stream.get("codec_type") == "video"]
    audio = [stream["codec_name"] for stream in streams if stream.get("codec_type") == "audio"]
    return bool(video) and set(video) <= BROWSER_VIDEO_CODECS and set(audio) <= BROWSER_AUDIO_CODECS


def prepare_for_storage(source, workdir):
    """
    Return (path, content type) of the file to keep. MP4 gets its index moved
    up front so that playback from storage starts without reading the whole
    file; anything a browser cannot play is converted once and for all.
    """
    target = workdir / "final.mp4"
    if is_browser_ready(source):
        if source.suffix.lower() == ".webm":
            return source, "video/webm"
        try:
            _run(
                ["ffmpeg", "-v", "error", "-y", "-i", str(source), "-c", "copy", "-movflags", "+faststart", str(target)],
                timeout=3600,
            )
        except MediaError as error:
            logger.warning("faststart remux skipped: %s", error)
            return source, "video/mp4"
        return target, "video/mp4"

    _run(
        [
            "ffmpeg", "-v", "error", "-y", "-i", str(source),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ac", "2", "-b:a", "160k",
            "-movflags", "+faststart", str(target),
        ],  # fmt: skip
        timeout=6 * 3600,
    )
    return target, "video/mp4"
