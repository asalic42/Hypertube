import re
from urllib.parse import quote

import requests
from django.conf import settings
from django.utils.html import strip_tags

from movies_app.models import SourceItem
from movies_app.services import http
from movies_app.services.titles import parse_year

from .base import ProviderDetails, ProviderError, ProviderItem, ProviderTorrent

SEARCH_URL = "https://archive.org/advancedsearch.php"
METADATA_URL = "https://archive.org/metadata/{identifier}"
FIELDS = ("identifier", "title", "year", "date", "downloads")
SUBTITLE_EXTENSIONS = (".srt", ".vtt")


def _base_query():
    return f'mediatype:movies AND collection:({settings.ARCHIVE_COLLECTION}) AND format:"Archive BitTorrent"'


def _escape(term):
    # Lucene special characters would otherwise alter the query.
    return re.sub(r'([+\-&|!(){}\[\]^"~*?:\\/])', r"\\\1", term)


def _to_item(doc):
    identifier = doc["identifier"]
    title = doc.get("title") or identifier
    if isinstance(title, list):
        title = title[0]
    encoded = quote(identifier)
    return ProviderItem(
        provider=SourceItem.Provider.ARCHIVE,
        external_id=identifier,
        title=str(title),
        item_url=f"https://archive.org/details/{encoded}",
        year=parse_year(doc.get("year")) or parse_year(doc.get("date")),
        downloads=int(doc.get("downloads") or 0),
        cover_url=f"https://archive.org/services/img/{encoded}",
        torrents=[
            ProviderTorrent(torrent_url=f"https://archive.org/download/{encoded}/{encoded}_archive.torrent"),
        ],
    )


def _query(query, rows):
    try:
        response = http.get(
            SEARCH_URL,
            params={
                "q": query,
                "fl[]": FIELDS,
                "sort[]": "downloads desc",
                "rows": rows,
                "output": "json",
            },
            # Their search is sometimes very slow: give up and serve the cached catalogue instead.
            timeout=(5, 10),
        )
        docs = response.json()["response"]["docs"]
    except (requests.RequestException, ValueError, KeyError) as error:
        raise ProviderError(f"archive.org search failed: {error}") from error
    return [_to_item(doc) for doc in docs if doc.get("identifier")]


def search(words, rows=200):
    terms = " AND ".join(_escape(word) for word in words)
    return _query(f"{_base_query()} AND title:({terms})", rows)


def popular(rows=200):
    return _query(_base_query(), rows)


def _metadata(identifier):
    try:
        return http.get(METADATA_URL.format(identifier=quote(identifier))).json()
    except (requests.RequestException, ValueError) as error:
        raise ProviderError(f"archive.org metadata failed: {error}") from error


def details(identifier):
    description = _metadata(identifier).get("metadata", {}).get("description", "")
    if isinstance(description, list):
        description = " ".join(description)
    overview = re.sub(r"\s+", " ", strip_tags(str(description))).strip()
    return ProviderDetails(overview=overview)


def subtitle_files(identifier):
    """Return [(file name, download url)] for the subtitle files shipped with an item."""
    files = _metadata(identifier).get("files", [])
    encoded = quote(identifier)
    return [
        (entry["name"], f"https://archive.org/download/{encoded}/{quote(entry['name'])}")
        for entry in files
        if str(entry.get("name", "")).lower().endswith(SUBTITLE_EXTENSIONS)
    ]
