"""
Subtitles for the stored movies, in sync with the file the viewer actually gets.

A film in the public domain exists in many transfers, of different cuts and
frame rates, so a subtitle made for one of them drifts on another. Every
candidate is therefore matched against the video: the files shipped with an
archive.org item are used only for a video taken from that very item,
OpenSubtitles is asked by the hash of the file and ranked by frame rate, cue
times are rescaled when the frame rate implies another running speed, and
whatever outlasts the video or covers little of it is rejected. The chosen
subtitle is served right away, then lined up on the speech of the sound track
once the whole film is stored, which absorbs the few seconds of leader that
differ from one transfer to the next. (The first minutes alone are not enough:
lined up on a partial film, the cues land on noise, minutes away.)
"""

import logging
import re
import tempfile
from pathlib import Path

import requests
from django.conf import settings
from django.utils import timezone

from movies_app.models import Download, SourceItem, Subtitle
from movies_app.services import http, media, storage
from movies_app.services.providers import ProviderError, archive

logger = logging.getLogger(__name__)

OPENSUBTITLES_URL = "https://api.opensubtitles.com/api/v1"
MAX_SUBTITLE_BYTES = 2 * 1024 * 1024
# OpenSubtitles downloads are quota-limited: a subtitle is not worth more tries than this.
MAX_CANDIDATES = 3
# A subtitle may end this many seconds after the video (credits differ between transfers)...
END_MARGIN = 90
# ...and must cover at least this share of it (a shorter cut, or another film altogether).
MIN_COVERAGE = 0.6
# A video runs either at film speed or, when it has 25 frames per second, 4% faster (PAL).
FILM_SPEED = 23.976
PAL_SPEED = 25.0
# A file still downloading is probed once this much of its beginning is there, then again
# every PROBE_STEP bytes: the index of an MP4 may sit at the end, which arrives early too.
PROBE_MIN_BYTES = 4 * 1024 * 1024
PROBE_STEP = 64 * 1024 * 1024

LANGUAGE_ALIASES = {
    "en": ("en", "eng", "english"),
    "fr": ("fr", "fre", "fra", "french", "francais"),
    "es": ("es", "spa", "esp", "spanish", "espanol"),
    "de": ("de", "ger", "deu", "german", "deutsch"),
    "it": ("it", "ita", "italian", "italiano"),
    "pt": ("pt", "por", "portuguese"),
    "ru": ("ru", "rus", "russian"),
    "zh": ("zh", "chi", "zho", "chinese"),
    "ja": ("ja", "jpn", "japanese"),
    "ko": ("ko", "kor", "korean"),
}
_ALIAS_TO_LANGUAGE = {alias: code for code, aliases in LANGUAGE_ALIASES.items() for alias in aliases}
# A cue time as SubRip files write it in the wild: hours optional, a comma or a
# dot, one to three fractional digits. WebVTT accepts only HH:MM:SS.mmm.
_TIMESTAMP = re.compile(r"(?<!\d)(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[,.](\d{1,3})(?!\d)")
_VTT_TIME = re.compile(r"(\d{2,}):(\d{2}):(\d{2})\.(\d{3})")
# SubRip positioning after the times ("X1:100 X2:200 Y1:..."), which WebVTT does not read.
_SRT_COORDINATES = re.compile(r"\s+[XY][12]:\d+.*$")

_opensubtitles_token = None
# Download id -> bytes buffered when its partial file was last probed in vain.
_partial_probes = {}


# --- Cue times ----------------------------------------------------------------


def decode(data):
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _vtt_time(match, scale):
    hours, minutes, seconds, fraction = match.groups()
    total = ((int(hours or 0) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + int(fraction.ljust(3, "0"))
    total = round(total * scale)
    hours, rest = divmod(total, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    seconds, milliseconds = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def _timing_line(line, scale):
    """A cue timing line in the one form browsers parse; a malformed cue is otherwise dropped silently."""
    line = _SRT_COORDINATES.sub("", line)
    return _TIMESTAMP.sub(lambda match: _vtt_time(match, scale), line)


def to_vtt(text, scale=1.0):
    """
    Convert SubRip to WebVTT, the only format <track> reads. The cue times are
    rewritten whatever their spelling (comma, two decimals, no hours), in
    WebVTT input too: a file that calls itself WEBVTT may still carry them.
    `scale` multiplies every time, for a subtitle made at another running speed.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿").strip()
    lines = [_timing_line(line, scale) if "-->" in line else line for line in text.split("\n")]
    body = "\n".join(lines)
    if body.startswith("WEBVTT"):
        return body + "\n"
    return "WEBVTT\n\n" + body + "\n"


def last_cue_end(vtt):
    """When the last cue of a WebVTT file ends, in seconds; None when it has no cue."""
    ends = [
        int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
        for line in vtt.split("\n")
        if "-->" in line
        for hours, minutes, seconds, milliseconds in _VTT_TIME.findall(line)
    ]
    return max(ends, default=None)


def to_srt(vtt):
    """The cues of a WebVTT file as SubRip, numbered, without header, notes or cue settings."""
    blocks = []
    for block in re.split(r"\n{2,}", vtt.replace("\r\n", "\n").strip()):
        lines = block.split("\n")
        timing = next((index for index, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            continue
        times = _VTT_TIME.findall(lines[timing])
        if len(times) < 2:
            continue
        start, end = ("{}:{}:{},{}".format(*time) for time in times[:2])
        text = "\n".join(lines[timing + 1 :]).strip()
        if text:
            blocks.append(f"{len(blocks) + 1}\n{start} --> {end}\n{text}")
    return "\n\n".join(blocks) + "\n"


def fits(vtt, duration):
    """Whether a subtitle can belong to a video of this running time: it must not outlast it, and must cover most of it."""
    if not duration:
        return True
    end = last_cue_end(vtt)
    return end is not None and duration * MIN_COVERAGE <= end <= duration + END_MARGIN


def speed(frame_rate):
    """The running speed a frame rate implies; None when the frame rate is unknown."""
    if not frame_rate:
        return None
    return PAL_SPEED if round(frame_rate) in (25, 50) else FILM_SPEED


def guess_language(file_name):
    """Read the language tag of names such as "movie.eng.srt"; None when there is none."""
    stem = file_name.rsplit(".", 1)[0].lower()
    for token in reversed(re.split(r"[^a-z]+", stem)):
        if token in _ALIAS_TO_LANGUAGE:
            return _ALIAS_TO_LANGUAGE[token]
    return None


# --- The video to match ---------------------------------------------------------


def video_profile(download):
    """
    Duration, frame rate and hash of the file the viewer gets, or None while
    not enough of it has arrived to tell. A film stored before these were
    recorded is probed from storage; when even that fails, the profile is
    empty and the subtitle is matched on the film alone rather than never.
    """
    if download.duration:
        return {"duration": download.duration, "frame_rate": download.frame_rate, "file_hash": download.file_hash}
    if download.status == Download.Status.READY and download.storage_key:
        source = storage.presigned_url(download.storage_key)
    elif download.status == Download.Status.DOWNLOADING and download.buffered_bytes >= PROBE_MIN_BYTES:
        if download.buffered_bytes < _partial_probes.get(download.pk, -PROBE_STEP) + PROBE_STEP:
            return None
        _partial_probes[download.pk] = download.buffered_bytes
        try:
            source = media.local_video_path(download)
        except media.MediaError:
            return None
    else:
        return None

    try:
        info = media.probe(source)
    except media.MediaError as error:
        logger.info("download %s: running time not readable: %s", download.pk, error)
        info = {"duration": None, "frame_rate": None}
    if not info["duration"]:
        if download.status == Download.Status.READY:
            return {"duration": None, "frame_rate": None, "file_hash": download.file_hash}
        return None
    if download.status == Download.Status.READY:
        Download.objects.filter(pk=download.pk).update(duration=info["duration"], frame_rate=info["frame_rate"], updated_at=timezone.now())
    _partial_probes.pop(download.pk, None)
    return {"duration": info["duration"], "frame_rate": info["frame_rate"], "file_hash": download.file_hash}


def align(subtitle, download, vtt=None):
    """
    Line the stored cues of a subtitle up on the speech of its video, once the
    whole film is stored. True once done. A failed alignment leaves the
    subtitle as it came, better a few seconds off than nothing.
    """
    if download.status != Download.Status.READY:
        return False
    with tempfile.TemporaryDirectory() as workdir:
        try:
            reference = storage.presigned_url(download.storage_key)
            if vtt is None:
                vtt = storage.read(subtitle.storage_key).decode("utf-8", "replace")
            srt_in, srt_out = Path(workdir, "in.srt"), Path(workdir, "out.srt")
            srt_in.write_text(to_srt(vtt), encoding="utf-8")
            offset, scale = media.align_subtitle(reference, srt_in, srt_out)
            aligned = to_vtt(decode(srt_out.read_bytes()))
        except (media.MediaError, OSError) as error:
            logger.warning("subtitle %s: not aligned on the sound track: %s", subtitle, error)
            aligned, offset, scale = vtt, None, 1.0
    if aligned is not None and aligned != vtt:
        storage.upload_bytes(aligned.encode("utf-8"), subtitle.storage_key, "text/vtt; charset=utf-8")
    subtitle.aligned = True
    subtitle.save(update_fields=["aligned", "updated_at"])
    logger.info(
        "subtitle %s: aligned on the sound track, offset %s%s",
        subtitle, "unknown" if offset is None else f"{offset:+.2f}s", f", stretched by {scale}" if scale != 1.0 else "",
    )
    return True


# --- Candidates ------------------------------------------------------------------
# Each source yields (label, fetch, scale): `fetch` returns the subtitle text,
# `scale` the factor its times need to run at the speed of the video.


def _fetch(url, headers=None):
    response = http.get(url, headers=headers, timeout=(5, 30))
    if len(response.content) > MAX_SUBTITLE_BYTES:
        raise ValueError("subtitle file is too large")
    return decode(response.content)


def _from_archive(download, movie, language, profile):
    """The subtitle files shipped with the archive.org item the video comes from, and that one only."""
    source = download.torrent.source if download.torrent_id else None
    if source is None or source.provider != SourceItem.Provider.ARCHIVE:
        return
    try:
        files = archive.subtitle_files(source.external_id)
    except ProviderError as error:
        logger.warning("%s", error)
        return
    candidates = [
        (name, url)
        for name, url in files
        # ".asr.srt" is archive.org's automatic transcription: wrong words, and timed on whichever derivative it ran on.
        if ".asr." not in name.lower()
        # Untagged files are in the language of the film, English on these sources.
        and (guess_language(name) or movie.original_language or "en") == language
    ]
    # An item may ship subtitles for several of its files: the one named after the video first.
    stem = Path(download.local_path).stem.lower()

    def order(candidate):
        name = Path(candidate[0]).stem.lower()
        return 0 if name == stem else 1 if name.startswith(stem) else 2

    candidates.sort(key=order)
    for name, url in candidates:
        yield f"archive.org {name}", (lambda url=url: _fetch(url)), 1.0


def _opensubtitles_headers():
    global _opensubtitles_token
    headers = {"Api-Key": settings.OPENSUBTITLES_API_KEY, "Accept": "application/json"}
    if settings.OPENSUBTITLES_USERNAME and _opensubtitles_token is None:
        # Logging in is optional but raises the daily download quota.
        response = http.post(
            f"{OPENSUBTITLES_URL}/login",
            json={"username": settings.OPENSUBTITLES_USERNAME, "password": settings.OPENSUBTITLES_PASSWORD},
            headers=headers,
        )
        _opensubtitles_token = response.json().get("token") or ""
    if _opensubtitles_token:
        headers["Authorization"] = f"Bearer {_opensubtitles_token}"
    return headers


def _from_opensubtitles(download, movie, language, profile):
    """
    OpenSubtitles entries for the film, best match first: one made for this
    very file (hash), then those at the running speed of the video, then
    those whose speed is unknown, and last the ones to rescale.
    """
    if not settings.OPENSUBTITLES_API_KEY:
        return
    if movie.imdb_id:
        params = {"imdb_id": int(movie.imdb_id.removeprefix("tt"))}
    elif movie.tmdb_id:
        params = {"tmdb_id": movie.tmdb_id}
    else:
        return
    if profile["file_hash"]:
        params["moviehash"] = profile["file_hash"]

    headers = _opensubtitles_headers()
    results = http.get(
        f"{OPENSUBTITLES_URL}/subtitles",
        params={**params, "languages": language, "order_by": "download_count"},
        headers=headers,
    ).json()
    video_speed = speed(profile["frame_rate"])

    def rank(entry):
        attributes = entry.get("attributes", {})
        subtitle_speed = speed(attributes.get("fps"))
        rescaled = bool(video_speed and subtitle_speed and subtitle_speed != video_speed)
        return (not attributes.get("moviehash_match"), rescaled, subtitle_speed is None, -(attributes.get("download_count") or 0))

    for entry in sorted(results.get("data", []), key=rank):
        attributes = entry.get("attributes", {})
        files = attributes.get("files") or []
        if not files:
            continue
        subtitle_speed = speed(attributes.get("fps"))
        scale = 1.0
        if video_speed and subtitle_speed and not attributes.get("moviehash_match"):
            scale = subtitle_speed / video_speed

        def fetch(file_id=files[0]["file_id"]):
            link = http.post(f"{OPENSUBTITLES_URL}/download", json={"file_id": file_id}, headers=headers).json().get("link")
            if not link:
                raise ValueError("no download link")
            return _fetch(link)

        yield f"opensubtitles {attributes.get('release') or files[0].get('file_name') or files[0]['file_id']}", fetch, scale


SOURCES = (("archive", _from_archive), ("opensubtitles", _from_opensubtitles))


# --- Storage -----------------------------------------------------------------------


def storage_key(movie_id, language):
    return f"{movie_id}/subtitles/{language}.vtt"


def remove_stored(movie):
    """Forget the subtitles of a movie and erase their files from storage. Best effort.

    Every row goes, not only the stored ones: a later download asks for the
    languages it needs again, from scratch.
    """
    for key in movie.subtitles.exclude(storage_key="").values_list("storage_key", flat=True):
        storage.delete(key)
    movie.subtitles.all().delete()


def reset(movie):
    """Start the subtitles of a movie over, keeping the languages asked for: its video is another file now."""
    for key in movie.subtitles.exclude(storage_key="").values_list("storage_key", flat=True):
        storage.delete(key)
    movie.subtitles.update(status=Subtitle.Status.PENDING, origin="", storage_key="", aligned=False, updated_at=timezone.now())


def _settle(subtitle, status, origin="", key=""):
    subtitle.status = status
    subtitle.origin = origin
    subtitle.storage_key = key
    subtitle.aligned = False
    subtitle.save(update_fields=["status", "origin", "storage_key", "aligned", "updated_at"])


def process(subtitle):
    """
    Resolve a pending subtitle against the video of its movie. Nothing is done
    until enough of the video is there to know its running time and frame
    rate: the subtitle stays pending and is looked at again later. The chosen
    file is served at once and lined up on the sound track when possible, or
    later by align_pending().
    """
    movie = subtitle.movie
    download = Download.objects.filter(movie=movie).select_related("torrent__source").first()
    if download is None or download.status == Download.Status.FAILED:
        _settle(subtitle, Subtitle.Status.UNAVAILABLE)
        return
    profile = video_profile(download)
    if profile is None:
        return

    attempts = 0
    for origin, candidates in SOURCES:
        try:
            for label, fetch, scale in candidates(download, movie, subtitle.language, profile):
                if attempts >= MAX_CANDIDATES:
                    break
                attempts += 1
                try:
                    vtt = to_vtt(fetch(), scale)
                except (requests.RequestException, ValueError, KeyError) as error:
                    logger.warning("subtitle %s: %s could not be fetched: %s", subtitle, label, error)
                    continue
                if not fits(vtt, profile["duration"]):
                    logger.info("subtitle %s: %s ends at %ss, the video at %ss: rejected", subtitle, label, last_cue_end(vtt), round(profile["duration"]))
                    continue
                key = storage_key(movie.pk, subtitle.language)
                storage.upload_bytes(vtt.encode("utf-8"), key, "text/vtt; charset=utf-8")
                _settle(subtitle, Subtitle.Status.READY, origin, key)
                logger.info("subtitle %s: %s%s", subtitle, label, f", times x{scale:.4f}" if scale != 1.0 else "")
                align(subtitle, download, vtt)
                return
        except (requests.RequestException, ValueError, KeyError) as error:
            logger.warning("subtitle lookup on %s failed for movie %s: %s", origin, movie.pk, error)
    _settle(subtitle, Subtitle.Status.UNAVAILABLE)


def align_pending():
    """Line up the subtitles served as they came, once their film is stored."""
    pending = Subtitle.objects.filter(status=Subtitle.Status.READY, aligned=False, movie__download__status=Download.Status.READY)
    for subtitle in pending.select_related("movie").order_by("updated_at")[:10]:
        download = Download.objects.get(movie=subtitle.movie)
        try:
            align(subtitle, download)
        except storage.StorageError as error:
            logger.warning("subtitle %s could not be re-stored: %s", subtitle, error)
