import logging
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from movies_app.models import (
    Comment,
    Genre,
    MergedMovie,
    Movie,
    SearchCache,
    SourceItem,
    Subtitle,
    Torrent,
    WatchRecord,
    normalize_title,
)
from movies_app.services import storage, tmdb
from movies_app.services.providers import ProviderError, archive, publicdomaintorrents
from movies_app.services.titles import clean_title

logger = logging.getLogger(__name__)

SEARCH_TTL = timedelta(hours=1)
POPULAR_TTL = timedelta(days=1)
PDT_CATALOG_TTL = timedelta(days=7)
ENRICHMENT_RETRY_DELAY = timedelta(hours=1)
ENRICHMENT_WORKERS = 16


# --- External sources -------------------------------------------------------


def _is_fresh(key, ttl):
    return SearchCache.objects.filter(key=key, fetched_at__gte=timezone.now() - ttl).exists()


def _mark_fetched(key):
    SearchCache.objects.update_or_create(key=key, defaults={"fetched_at": timezone.now()})


def _refresh_popularity(movie_id):
    total = SourceItem.objects.filter(movie_id=movie_id).aggregate(total=Sum("downloads"))["total"]
    Movie.objects.filter(pk=movie_id).update(popularity=total or 0)


def upsert_items(items):
    """Mirror source listings in database. Known items only get their counters updated."""
    if not items:
        return
    provider = items[0].provider
    known = {
        source.external_id: source
        for source in SourceItem.objects.filter(
            provider=provider,
            external_id__in=[item.external_id for item in items],
        )
    }
    for item in items:
        source = known.get(item.external_id)
        if source is not None:
            if item.downloads and item.downloads != source.downloads:
                SourceItem.objects.filter(pk=source.pk).update(downloads=item.downloads)
                _refresh_popularity(source.movie_id)
            continue

        title, year = clean_title(item.title, item.year)
        with transaction.atomic():
            movie = Movie.objects.create(
                title=title,
                year=year,
                cover_url=item.cover_url,
                popularity=item.downloads,
            )
            # get_or_create absorbs the race with a concurrent request listing the same item.
            source, created = SourceItem.objects.get_or_create(
                provider=item.provider,
                external_id=item.external_id,
                defaults={
                    "movie": movie,
                    "title": item.title[:512],
                    "item_url": item.item_url,
                    "downloads": item.downloads,
                },
            )
            if not created:
                movie.delete()
                continue
            Torrent.objects.bulk_create(
                Torrent(source=source, torrent_url=torrent.torrent_url, video_format=torrent.video_format)
                for torrent in item.torrents
            )


def _refresh(key, ttl, fetch):
    if _is_fresh(key, ttl):
        return
    try:
        upsert_items(fetch())
    except ProviderError as error:
        # A source being down must not take the library down: serve what is cached.
        logger.warning("%s", error)
        return
    _mark_fetched(key)


def refresh_pdt_catalog():
    _refresh("pdt:catalog", PDT_CATALOG_TTL, publicdomaintorrents.catalog)


def refresh_popular():
    _refresh("archive:popular", POPULAR_TTL, archive.popular)
    refresh_pdt_catalog()


def refresh_search(words):
    _refresh(f"archive:search:{' '.join(words)}"[:255], SEARCH_TTL, lambda: archive.search(words))
    refresh_pdt_catalog()


def resolve_movie(movie_id):
    """Find a movie by id, following the merges. None when it does not exist."""
    movie = Movie.objects.filter(pk=movie_id).first()
    if movie is None:
        alias = MergedMovie.objects.filter(old_id=movie_id).select_related("movie").first()
        movie = alias.movie if alias else None
    return movie


def search_words(query):
    return normalize_title(query).split()


def filter_by_words(queryset, words):
    for word in words:
        queryset = queryset.filter(normalized_title__contains=word)
    return queryset


# --- Metadata enrichment ----------------------------------------------------


def pending_enrichment():
    retry_before = timezone.now() - ENRICHMENT_RETRY_DELAY
    return Q(metadata_status=Movie.MetadataStatus.PENDING) & (
        Q(metadata_fetched_at__isnull=True) | Q(metadata_fetched_at__lt=retry_before)
    )


@dataclass
class _Plan:
    movie_id: int
    title: str
    year: int | None
    imdb_id: str
    has_overview: bool
    # (source pk, provider, external id) of the sources whose detail page was never read.
    sources: list[tuple[int, str, str]] = field(default_factory=list)


@dataclass
class _Result:
    movie_id: int
    imdb_id: str = ""
    overview: str = ""
    source_details: dict = field(default_factory=dict)
    metadata: tmdb.TMDbMovie | None = None
    complete: bool = True


def _fetch(plan):
    """Network only: runs in a thread pool and must not touch the database."""
    result = _Result(movie_id=plan.movie_id, imdb_id=plan.imdb_id)
    archive_sources = []
    for source_pk, provider, external_id in plan.sources:
        if provider == SourceItem.Provider.ARCHIVE:
            archive_sources.append((source_pk, external_id))
            continue
        try:
            details = publicdomaintorrents.details(external_id)
        except ProviderError as error:
            logger.warning("%s", error)
            result.complete = False
            continue
        result.source_details[source_pk] = details
        result.imdb_id = result.imdb_id or details.imdb_id

    if tmdb.is_configured():
        try:
            tmdb_id = tmdb.find_id(plan.title, plan.year, result.imdb_id)
            if tmdb_id:
                result.metadata = tmdb.movie(tmdb_id)
        except tmdb.TMDbError as error:
            logger.warning("%s", error)
            result.complete = False
    else:
        result.complete = False

    if result.metadata is None and not plan.has_overview:
        # Fall back on the description written by the uploader.
        for source_pk, external_id in archive_sources:
            try:
                details = archive.details(external_id)
            except ProviderError as error:
                logger.warning("%s", error)
                continue
            result.source_details[source_pk] = details
            result.overview = result.overview or details.overview
    return result


def merge_movies(keep, duplicate):
    """Several source items can be the same film: fold `duplicate` into `keep`."""
    SourceItem.objects.filter(movie=duplicate).update(movie=keep)
    Comment.objects.filter(movie=duplicate).update(movie=keep)

    for record in WatchRecord.objects.filter(movie=duplicate):
        kept, created = WatchRecord.objects.get_or_create(
            user_id=record.user_id,
            movie=keep,
            defaults={"last_watched_at": record.last_watched_at},
        )
        if not created and record.last_watched_at > kept.last_watched_at:
            kept.last_watched_at = record.last_watched_at
            kept.save(update_fields=["last_watched_at"])

    known_languages = set(keep.subtitles.values_list("language", flat=True))
    for subtitle in Subtitle.objects.filter(movie=duplicate):
        if subtitle.language in known_languages:
            storage.delete(subtitle.storage_key)
        else:
            Subtitle.objects.filter(pk=subtitle.pk).update(movie=keep)

    duplicate_download = getattr(duplicate, "download", None)
    if duplicate_download is not None:
        if hasattr(keep, "download"):
            storage.delete(duplicate_download.storage_key)
        else:
            duplicate_download.movie = keep
            duplicate_download.save(update_fields=["movie"])

    watched = [date for date in (keep.last_watched_at, duplicate.last_watched_at) if date]
    if watched:
        keep.last_watched_at = max(watched)
        keep.save(update_fields=["last_watched_at"])
    MergedMovie.objects.filter(movie=duplicate).update(movie=keep)
    MergedMovie.objects.update_or_create(old_id=duplicate.pk, defaults={"movie": keep})
    # The instance still caches the relations that were just moved: delete by
    # queryset so the cascade only removes what is really left on the duplicate.
    Movie.objects.filter(pk=duplicate.pk).delete()
    _refresh_popularity(keep.pk)


def _apply_metadata(movie, metadata):
    movie.title = metadata.title or movie.title
    movie.year = metadata.year or movie.year
    movie.overview = metadata.overview or movie.overview
    movie.cover_url = metadata.cover_url or movie.cover_url
    movie.backdrop_url = metadata.backdrop_url
    movie.rating = metadata.rating
    movie.vote_count = metadata.vote_count
    movie.runtime = metadata.runtime
    movie.original_language = metadata.original_language
    movie.imdb_id = metadata.imdb_id or movie.imdb_id
    movie.tmdb_id = metadata.tmdb_id
    movie.directors = metadata.directors
    movie.producers = metadata.producers
    movie.cast = metadata.cast
    movie.metadata_status = Movie.MetadataStatus.MATCHED
    movie.save()
    movie.genres.set(Genre.objects.get_or_create(name=name)[0] for name in metadata.genres)


@transaction.atomic
def _apply(result):
    movie = Movie.objects.select_for_update().filter(pk=result.movie_id).first()
    if movie is None:
        return  # merged into another movie meanwhile

    now = timezone.now()
    for source_pk, details in result.source_details.items():
        for torrent in details.torrents:
            Torrent.objects.get_or_create(
                source_id=source_pk,
                torrent_url=torrent.torrent_url,
                defaults={"video_format": torrent.video_format},
            )
        SourceItem.objects.filter(pk=source_pk).update(details_fetched_at=now)

    movie.imdb_id = movie.imdb_id or result.imdb_id
    movie.overview = movie.overview or result.overview
    movie.metadata_fetched_at = now

    if result.metadata is not None:
        twin = Movie.objects.select_for_update().filter(tmdb_id=result.metadata.tmdb_id).exclude(pk=movie.pk).first()
        if twin is not None:
            merge_movies(keep=twin, duplicate=movie)
            return
        _apply_metadata(movie, result.metadata)
        return

    if result.complete:
        movie.metadata_status = Movie.MetadataStatus.UNMATCHED
    movie.save()


def enrich(movies, timeout=8.0):
    """
    Fetch the missing metadata of `movies` in parallel. The time budget keeps
    the calling request responsive: what is late is retried on a later call.
    """
    plans = []
    for movie in movies:
        plans.append(
            _Plan(
                movie_id=movie.pk,
                title=movie.title,
                year=movie.year,
                imdb_id=movie.imdb_id,
                has_overview=bool(movie.overview),
                sources=[
                    (source.pk, source.provider, source.external_id)
                    for source in movie.sources.all()
                    if source.details_fetched_at is None
                ],
            )
        )
    if not plans:
        return

    executor = ThreadPoolExecutor(max_workers=ENRICHMENT_WORKERS)
    try:
        done, _ = wait([executor.submit(_fetch, plan) for plan in plans], timeout=timeout)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    for future in done:
        try:
            result = future.result()
        except Exception:  # noqa: BLE001 - one bad movie must not break the listing
            logger.exception("metadata fetch failed")
            continue
        try:
            _apply(result)
        except IntegrityError:
            # Two requests matched the same TMDb movie at once: the retry merges into the winner.
            _apply(result)


def enrich_pending(queryset, limit, timeout=8.0):
    movies = list(queryset.filter(pending_enrichment()).prefetch_related("sources")[:limit])
    enrich(movies, timeout=timeout)
    return len(movies)


def enrich_listing(queryset, limit, timeout):
    """
    Enrichment on the path of a listing request: only worth its latency when
    TMDb can answer. The worker covers the rest of the catalogue in background.
    """
    if not tmdb.is_configured():
        return 0
    return enrich_pending(queryset, limit, timeout)


# --- Torrent selection ------------------------------------------------------


def ensure_source_details(movie):
    """publicdomaintorrents only reveals its torrents on the movie page."""
    missing = [source for source in movie.sources.all() if source.details_fetched_at is None]
    if any(source.provider == SourceItem.Provider.PUBLIC_DOMAIN_TORRENTS for source in missing):
        enrich([movie])


def candidate_torrents(movie, exclude_ids=()):
    """
    Best torrents first. archive.org torrents are web seeded, so they finish
    even without peers; then browser-ready containers avoid a transcode.
    """
    torrents = Torrent.objects.filter(source__movie=movie).exclude(pk__in=exclude_ids).select_related("source")

    def rank(torrent):
        return (
            torrent.source.provider != SourceItem.Provider.ARCHIVE,
            torrent.video_format not in ("", "mp4", "webm"),
            -torrent.source.downloads,
            torrent.pk,
        )

    return sorted(torrents, key=rank)
