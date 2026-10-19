from dataclasses import dataclass, field


class ProviderError(Exception):
    """An external source could not be reached or returned unusable data."""


@dataclass
class ProviderTorrent:
    torrent_url: str
    video_format: str = ""


@dataclass
class ProviderItem:
    provider: str
    external_id: str
    title: str
    item_url: str
    year: int | None = None
    downloads: int = 0
    cover_url: str = ""
    torrents: list[ProviderTorrent] = field(default_factory=list)


@dataclass
class ProviderDetails:
    imdb_id: str = ""
    overview: str = ""
    torrents: list[ProviderTorrent] = field(default_factory=list)
