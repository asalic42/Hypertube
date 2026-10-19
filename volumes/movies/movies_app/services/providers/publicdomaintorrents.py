import html
import re

import requests

from movies_app.models import SourceItem
from movies_app.services import http

from .base import ProviderDetails, ProviderError, ProviderItem, ProviderTorrent

BASE_URL = "https://www.publicdomaintorrents.info"
CATALOG_URL = f"{BASE_URL}/nshowcat.html"
MOVIE_URL = f"{BASE_URL}/nshowmovie.html"

_CATALOG_ENTRY = re.compile(r"nshowmovie\.html\?movieid=(\d+)[^>]*>([^<]+)</a>", re.IGNORECASE)
_IMDB_ID = re.compile(r"imdb\.com/title/(tt\d+)", re.IGNORECASE)
_TORRENT_LINK = re.compile(r"href=[\"']?([^\"'\s>]+\.torrent)", re.IGNORECASE)
# The "PSP"/"iPod" encodes are low resolution duplicates of the main files.
_LOW_QUALITY = re.compile(r"(psp|ipod|palm|pda)", re.IGNORECASE)


def catalog():
    """
    The site has no search engine: its whole catalogue (about a thousand
    movies) is a single page, which is mirrored in database and searched there.
    """
    try:
        page = http.get(CATALOG_URL, params={"category": "ALL"}).text
    except requests.RequestException as error:
        raise ProviderError(f"publicdomaintorrents catalogue failed: {error}") from error

    items = {}
    for movie_id, title in _CATALOG_ENTRY.findall(page):
        title = html.unescape(title).strip()
        if title:
            items[movie_id] = ProviderItem(
                provider=SourceItem.Provider.PUBLIC_DOMAIN_TORRENTS,
                external_id=movie_id,
                title=title,
                item_url=f"{MOVIE_URL}?movieid={movie_id}",
            )
    if not items:
        raise ProviderError("publicdomaintorrents catalogue is empty or its layout changed")
    return list(items.values())


def _video_format(torrent_url):
    match = re.search(r"\.([A-Za-z0-9]{2,4})\.torrent$", torrent_url)
    return match.group(1).lower() if match else ""


def details(movie_id):
    try:
        page = http.get(MOVIE_URL, params={"movieid": movie_id}).text
    except requests.RequestException as error:
        raise ProviderError(f"publicdomaintorrents movie page failed: {error}") from error

    imdb = _IMDB_ID.search(page)
    links = dict.fromkeys(html.unescape(link) for link in _TORRENT_LINK.findall(page))
    torrents = [
        ProviderTorrent(torrent_url=link, video_format=_video_format(link))
        for link in links
        if link.startswith(("http://", "https://")) and not _LOW_QUALITY.search(link)
    ]
    return ProviderDetails(imdb_id=imdb.group(1) if imdb else "", torrents=torrents)
