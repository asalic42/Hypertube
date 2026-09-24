import re
import unicodedata

from django.db import models
from django.utils import timezone


def normalize_title(value):
    """Lowercase, accent-free, alphanumeric-only form used to search and compare titles."""
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


class Genre(models.Model):
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Movie(models.Model):
    class MetadataStatus(models.TextChoices):
        PENDING = "pending"
        MATCHED = "matched"
        UNMATCHED = "unmatched"

    title = models.CharField(max_length=512)
    normalized_title = models.CharField(max_length=512, db_index=True, editable=False)
    year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    overview = models.TextField(blank=True)
    cover_url = models.URLField(max_length=512, blank=True)
    backdrop_url = models.URLField(max_length=512, blank=True)
    rating = models.FloatField(null=True, blank=True, db_index=True)
    vote_count = models.PositiveIntegerField(default=0)
    runtime = models.PositiveIntegerField(null=True, blank=True, help_text="Length in minutes.")
    genres = models.ManyToManyField(Genre, related_name="movies", blank=True)
    directors = models.JSONField(default=list, blank=True)
    producers = models.JSONField(default=list, blank=True)
    cast = models.JSONField(default=list, blank=True)
    original_language = models.CharField(max_length=8, blank=True)
    imdb_id = models.CharField(max_length=16, blank=True, db_index=True)
    tmdb_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    # Sum of the download counters reported by the external sources.
    popularity = models.BigIntegerField(default=0, db_index=True)
    metadata_status = models.CharField(
        max_length=16,
        choices=MetadataStatus.choices,
        default=MetadataStatus.PENDING,
        db_index=True,
    )
    metadata_fetched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Drives the "erase a movie unwatched for a month" rule.
    last_watched_at = models.DateTimeField(null=True, blank=True, db_index=True)

    def save(self, *args, **kwargs):
        self.normalized_title = normalize_title(self.title)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "title" in update_fields:
            kwargs["update_fields"] = {*update_fields, "normalized_title"}
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.year})" if self.year else self.title


class MergedMovie(models.Model):
    """
    Several source items often turn out to be the same film and are merged.
    The ids handed out before the merge keep resolving through this table.
    """

    old_id = models.BigIntegerField(primary_key=True)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="merged_ids")

    def __str__(self):
        return f"{self.old_id} -> {self.movie_id}"


class SourceItem(models.Model):
    """A movie as listed by one external torrent source."""

    class Provider(models.TextChoices):
        ARCHIVE = "archive", "Internet Archive"
        PUBLIC_DOMAIN_TORRENTS = "pdt", "Public Domain Torrents"

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="sources")
    provider = models.CharField(max_length=16, choices=Provider.choices)
    external_id = models.CharField(max_length=255)
    title = models.CharField(max_length=512)
    item_url = models.URLField(max_length=512)
    downloads = models.BigIntegerField(default=0)
    details_fetched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("provider", "external_id"), name="unique_source_item"),
        ]

    def __str__(self):
        return f"{self.provider}:{self.external_id}"


class Torrent(models.Model):
    source = models.ForeignKey(SourceItem, on_delete=models.CASCADE, related_name="torrents")
    torrent_url = models.URLField(max_length=1024)
    # Container announced by the source ("mp4", "avi", ...), empty when unknown.
    video_format = models.CharField(max_length=16, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("source", "torrent_url"), name="unique_source_torrent"),
        ]

    def __str__(self):
        return self.torrent_url


class SearchCache(models.Model):
    """Remembers when the external sources were last queried for a given key."""

    key = models.CharField(max_length=255, unique=True)
    fetched_at = models.DateTimeField()

    def __str__(self):
        return self.key


class Download(models.Model):
    """The server-side copy of a movie, from the torrent job to the stored file."""

    class Status(models.TextChoices):
        QUEUED = "queued"
        DOWNLOADING = "downloading"
        PROCESSING = "processing"
        READY = "ready"
        FAILED = "failed"

    ACTIVE_STATUSES = (Status.QUEUED, Status.DOWNLOADING, Status.PROCESSING)

    movie = models.OneToOneField(Movie, on_delete=models.CASCADE, related_name="download")
    torrent = models.ForeignKey(Torrent, on_delete=models.SET_NULL, null=True, related_name="+")
    # Torrents that already stalled or failed, so the worker falls back to another source.
    attempted_torrent_ids = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    progress = models.FloatField(default=0)
    download_rate = models.PositiveIntegerField(default=0, help_text="Bytes per second.")
    num_peers = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)

    # Location of the video inside the torrent, filled by the worker. The web
    # process uses it to map byte ranges to pieces while the download runs.
    local_path = models.CharField(max_length=1024, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    file_offset = models.BigIntegerField(null=True, blank=True)
    piece_length = models.PositiveIntegerField(null=True, blank=True)
    buffered_bytes = models.BigIntegerField(default=0, help_text="Contiguous bytes available from the start.")
    needs_transcode = models.BooleanField(default=False)
    # Byte offset a viewer is waiting for; the worker prioritises its pieces.
    requested_offset = models.BigIntegerField(null=True, blank=True)

    storage_key = models.CharField(max_length=512, blank=True)
    storage_size = models.BigIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=64, blank=True)
    # Frame size of the stored video, read once the file is complete.
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    # Set once the lower resolutions to encode were decided (possibly none).
    renditions_planned = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.movie_id}:{self.status}"


class Rendition(models.Model):
    """A lower resolution copy of a stored movie, encoded by the worker once the download is complete."""

    class Status(models.TextChoices):
        PENDING = "pending"
        READY = "ready"
        FAILED = "failed"

    download = models.ForeignKey(Download, on_delete=models.CASCADE, related_name="renditions")
    height = models.PositiveIntegerField()
    width = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    storage_key = models.CharField(max_length=512, blank=True)
    storage_size = models.BigIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=64, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("download", "height"), name="unique_download_rendition"),
        ]
        ordering = ("-height",)

    def __str__(self):
        return f"{self.download_id}:{self.height}p"


class Subtitle(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        READY = "ready"
        UNAVAILABLE = "unavailable"

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="subtitles")
    language = models.CharField(max_length=8)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    origin = models.CharField(max_length=32, blank=True)
    storage_key = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("movie", "language"), name="unique_movie_subtitle"),
        ]
        ordering = ("language",)

    def __str__(self):
        return f"{self.movie_id}:{self.language}"


class Comment(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="comments")
    # Users live in the auth service: only their id and username are kept here.
    user_id = models.UUIDField(db_index=True)
    username = models.CharField(max_length=150)
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"{self.username} on {self.movie_id}"


class WatchRecord(models.Model):
    user_id = models.UUIDField()
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="watch_records")
    first_watched_at = models.DateTimeField(auto_now_add=True)
    last_watched_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user_id", "movie"), name="unique_user_movie_watch"),
        ]

    def __str__(self):
        return f"{self.user_id} watched {self.movie_id}"
