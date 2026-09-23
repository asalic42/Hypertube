import logging
import re

import requests
from django.conf import settings

from movies_app.models import SourceItem, Subtitle
from movies_app.services import http, storage
from movies_app.services.providers import ProviderError, archive

logger = logging.getLogger(__name__)

OPENSUBTITLES_URL = "https://api.opensubtitles.com/api/v1"
MAX_SUBTITLE_BYTES = 2 * 1024 * 1024

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
_TIMESTAMP = re.compile(r"(\d{1,2}:\d{2}:\d{2}),(\d{3})")

_opensubtitles_token = None


def decode(data):
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def to_vtt(text):
    """Convert SubRip to WebVTT, the only format <track> reads. WebVTT input is returned as is."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿").strip()
    if text.startswith("WEBVTT"):
        return text + "\n"
    return "WEBVTT\n\n" + _TIMESTAMP.sub(r"\1.\2", text) + "\n"


def guess_language(file_name):
    """Read the language tag of names such as "movie.eng.srt"; None when there is none."""
    stem = file_name.rsplit(".", 1)[0].lower()
    for token in reversed(re.split(r"[^a-z]+", stem)):
        if token in _ALIAS_TO_LANGUAGE:
            return _ALIAS_TO_LANGUAGE[token]
    return None


def _download(url, headers=None):
    response = http.get(url, headers=headers, timeout=(5, 30))
    if len(response.content) > MAX_SUBTITLE_BYTES:
        raise ValueError("subtitle file is too large")
    return to_vtt(decode(response.content))


def _from_archive(movie, language):
    for source in movie.sources.filter(provider=SourceItem.Provider.ARCHIVE):
        try:
            files = archive.subtitle_files(source.external_id)
        except ProviderError as error:
            logger.warning("%s", error)
            continue
        for name, url in files:
            # Untagged files are in the language of the film, English on these sources.
            if (guess_language(name) or movie.original_language or "en") == language:
                return _download(url)
    return None


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


def _from_opensubtitles(movie, language):
    if not settings.OPENSUBTITLES_API_KEY:
        return None
    if movie.imdb_id:
        params = {"imdb_id": int(movie.imdb_id.removeprefix("tt"))}
    elif movie.tmdb_id:
        params = {"tmdb_id": movie.tmdb_id}
    else:
        return None

    headers = _opensubtitles_headers()
    results = http.get(
        f"{OPENSUBTITLES_URL}/subtitles",
        params={**params, "languages": language, "order_by": "download_count"},
        headers=headers,
    ).json()
    for entry in results.get("data", []):
        files = entry.get("attributes", {}).get("files") or []
        if not files:
            continue
        link = http.post(
            f"{OPENSUBTITLES_URL}/download",
            json={"file_id": files[0]["file_id"]},
            headers=headers,
        ).json().get("link")
        if link:
            return _download(link)
    return None


def storage_key(movie_id, language):
    return f"{movie_id}/subtitles/{language}.vtt"


def process(subtitle):
    """Resolve a pending subtitle: files shipped with the archive.org item first, then OpenSubtitles."""
    movie = subtitle.movie
    vtt, origin = None, ""
    for origin, fetch in (("archive", _from_archive), ("opensubtitles", _from_opensubtitles)):
        try:
            vtt = fetch(movie, subtitle.language)
        except (requests.RequestException, ValueError, KeyError) as error:
            logger.warning("subtitle lookup on %s failed for movie %s: %s", origin, movie.pk, error)
            continue
        if vtt:
            break

    if not vtt:
        subtitle.status = Subtitle.Status.UNAVAILABLE
        subtitle.save(update_fields=["status", "updated_at"])
        return

    key = storage_key(movie.pk, subtitle.language)
    storage.upload_bytes(vtt.encode("utf-8"), key, "text/vtt; charset=utf-8")
    subtitle.status = Subtitle.Status.READY
    subtitle.origin = origin
    subtitle.storage_key = key
    subtitle.save(update_fields=["status", "origin", "storage_key", "updated_at"])
