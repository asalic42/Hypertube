import json
import logging
import re
import subprocess
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = (".mp4", ".m4v", ".webm", ".mkv", ".avi", ".mov", ".mpg", ".mpeg", ".ogv", ".wmv", ".flv", ".divx")
BROWSER_EXTENSIONS = (".mp4", ".m4v", ".webm")
BROWSER_VIDEO_CODECS = {"h264", "vp8", "vp9", "av1"}
BROWSER_AUDIO_CODECS = {"aac", "mp3", "opus", "vorbis"}

ENCODE = (
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-ac", "2", "-b:a", "160k",
)
LIVE_OUTPUT = (*ENCODE, "-movflags", "frag_keyframe+empty_moov+default_base_moof", "-f", "mp4", "pipe:1")


class MediaError(Exception):
    pass


def download_root():
    return Path(settings.MOVIES_DOWNLOAD_DIR).resolve()


def download_directory(download_id):
    return download_root() / str(download_id)


def pieces_path(download_id):
    return download_directory(download_id) / "pieces.bin"


RENDITIONS_DIR = "renditions"


def renditions_directory(download_id):
    return download_root() / RENDITIONS_DIR / str(download_id)


def storage_suffix(download):
    """Extension of the stored file, so that ffmpeg recognises the container of a local copy."""
    suffix = Path(download.storage_key).suffix.lower()
    return suffix if suffix in VIDEO_EXTENSIONS else ".mp4"


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


def _frame_rate(stream):
    """The average frame rate of a stream as a float; None when ffprobe does not know it."""
    try:
        numerator, denominator = (stream.get("avg_frame_rate") or "0/0").split("/")
        return round(int(numerator) / int(denominator), 3) or None
    except (ValueError, ZeroDivisionError):
        return None


def probe(path):
    """Codecs, frame size, frame rate and running time of a video, as ffprobe reports them. `path` may be a URL."""
    output = _run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type,codec_name,width,height,avg_frame_rate:format=duration",
            "-of", "json", str(path),
        ],  # fmt: skip
        timeout=120,
    ).stdout
    report = json.loads(output or b"{}")
    streams = report.get("streams", [])
    video = [stream for stream in streams if stream.get("codec_type") == "video"]
    sized = [stream for stream in video if stream.get("width") and stream.get("height")]
    main = max(sized, key=lambda stream: stream["width"] * stream["height"], default=None)
    try:
        duration = float(report.get("format", {}).get("duration")) or None
    except (TypeError, ValueError):
        duration = None
    return {
        "video_codecs": {stream["codec_name"] for stream in video},
        "audio_codecs": {stream["codec_name"] for stream in streams if stream.get("codec_type") == "audio"},
        "width": main["width"] if main else None,
        "height": main["height"] if main else None,
        "frame_rate": _frame_rate(main) if main else None,
        "duration": duration,
    }


HASH_CHUNK = 64 * 1024


def opensubtitles_hash(path):
    """
    The OpenSubtitles hash of a file: its size plus the first and last 64 KiB
    read as little-endian 64-bit words, summed modulo 2**64. It identifies a
    release exactly, so a subtitle found by it is in sync with this very file.
    """
    size = path.stat().st_size
    if size < HASH_CHUNK:
        raise MediaError("file too small to hash")
    total = size
    with path.open("rb") as handle:
        for offset in (0, size - HASH_CHUNK):
            handle.seek(offset)
            chunk = handle.read(HASH_CHUNK)
            total += sum(int.from_bytes(chunk[i : i + 8], "little") for i in range(0, len(chunk) - 7, 8))
    return f"{total & 0xFFFFFFFFFFFFFFFF:016x}"


def is_browser_ready(path):
    """True when both the container and the codecs are playable by Firefox and Chrome."""
    if needs_transcode(path.name):
        return False
    info = probe(path)
    return (
        bool(info["video_codecs"])
        and info["video_codecs"] <= BROWSER_VIDEO_CODECS
        and info["audio_codecs"] <= BROWSER_AUDIO_CODECS
    )


def rendition_heights(source_height):
    """The lower resolutions worth encoding for a source of this height: nothing is ever upscaled."""
    if not source_height:
        return []
    return sorted((height for height in settings.MOVIE_RENDITION_HEIGHTS if height < source_height), reverse=True)


def encode_rendition(source, target, height):
    """Scale a video down to `height` lines (even width, aspect ratio kept) as a browser-ready MP4."""
    _run(
        [
            "ffmpeg", "-v", "error", "-y", "-i", str(source),
            "-vf", f"scale=-2:{height}", *ENCODE,
            "-movflags", "+faststart", str(target),
        ],
        timeout=6 * 3600,
    )
    return target, "video/mp4"


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
        ["ffmpeg", "-v", "error", "-y", "-i", str(source), *ENCODE, "-movflags", "+faststart", str(target)],
        timeout=6 * 3600,
    )
    return target, "video/mp4"


def video_profile(path):
    """
    What subtitles are matched against: `duration`, `frame_rate` and the
    OpenSubtitles `file_hash` of the file. Whatever cannot be read is left
    empty rather than failing: the film is still worth storing.
    """
    profile = {"duration": None, "frame_rate": None, "file_hash": ""}
    try:
        info = probe(path)
        profile.update(duration=info["duration"], frame_rate=info["frame_rate"])
    except MediaError as error:
        logger.warning("%s: running time unknown: %s", path.name, error)
    try:
        profile["file_hash"] = opensubtitles_hash(path)
    except (MediaError, OSError) as error:
        logger.warning("%s: not hashed: %s", path.name, error)
    return profile


# Transfers of a film differ by seconds of leader, not minutes: a wider search only finds false matches.
ALIGN_MAX_OFFSET = 60
_ALIGN_SCORE = re.compile(r"score:\s*(-?[\d.]+)")
_ALIGN_OFFSET = re.compile(r"offset seconds:\s*(-?[\d.]+)")
_ALIGN_SCALE = re.compile(r"framerate scale factor:\s*([\d.]+)")


def align_subtitle(source, srt_in, srt_out):
    """
    Shift and stretch a SubRip file onto the speech of a video with ffsubsync,
    which detects voice in the sound track and finds the offset that best lines
    the cues up. `source` may be a URL; it must be the whole film, the cues of
    a partial one line up on noise. Returns (offset seconds, scale factor).
    """
    result = _run(
        [
            "ffsubsync", str(source), "-i", str(srt_in), "-o", str(srt_out),
            "--max-offset-seconds", str(ALIGN_MAX_OFFSET),
        ],  # fmt: skip
        timeout=1800,
    )
    report = result.stderr.decode(errors="replace")
    score, offset, scale = _ALIGN_SCORE.search(report), _ALIGN_OFFSET.search(report), _ALIGN_SCALE.search(report)
    if offset is None or not Path(srt_out).is_file():
        raise MediaError(f"ffsubsync reported no alignment: {report[-300:]}")
    # The score counts the frames where speech and cues agree minus those where they do not.
    if score is not None and float(score.group(1)) <= 0:
        raise MediaError(f"the cues do not line up with any speech (score {score.group(1)})")
    return float(offset.group(1)), float(scale.group(1)) if scale else 1.0

