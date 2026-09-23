import re

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from movies_app.models import Comment, Download, Movie, Subtitle
from movies_app.services import streaming

SORT_CHOICES = ("name", "-name", "year", "-year", "rating", "-rating", "popularity", "-popularity")
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()


class MovieListQuerySerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, max_length=100, default="")
    genre = serializers.CharField(required=False, allow_blank=True, max_length=64, default="")
    year_min = serializers.IntegerField(required=False, min_value=1880, max_value=2100)
    year_max = serializers.IntegerField(required=False, min_value=1880, max_value=2100)
    rating_min = serializers.FloatField(required=False, min_value=0, max_value=10)
    rating_max = serializers.FloatField(required=False, min_value=0, max_value=10)
    sort = serializers.ChoiceField(required=False, choices=SORT_CHOICES)

    def validate(self, attrs):
        for low, high in (("year_min", "year_max"), ("rating_min", "rating_max")):
            if low in attrs and high in attrs and attrs[low] > attrs[high]:
                raise serializers.ValidationError({low: f"Must not be greater than {high}."})
        return attrs


@extend_schema_field({"type": "array", "items": {"type": "string"}})
class GenreNamesField(serializers.Field):
    def to_representation(self, value):
        return [genre.name for genre in value.all()]


class MovieListSerializer(serializers.ModelSerializer):
    genres = GenreNamesField(read_only=True)
    watched = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = Movie
        fields = ("id", "title", "year", "rating", "cover_url", "genres", "watched")


class SourceSerializer(serializers.Serializer):
    provider = serializers.CharField(source="get_provider_display")
    url = serializers.URLField(source="item_url")


class MovieDetailSerializer(MovieListSerializer):
    sources = SourceSerializer(many=True, read_only=True)
    subtitles = serializers.SerializerMethodField()
    comments_count = serializers.IntegerField(read_only=True)
    download_status = serializers.SerializerMethodField()

    class Meta(MovieListSerializer.Meta):
        fields = (
            *MovieListSerializer.Meta.fields,
            "overview",
            "backdrop_url",
            "runtime",
            "vote_count",
            "original_language",
            "imdb_id",
            "directors",
            "producers",
            "cast",
            "sources",
            "subtitles",
            "comments_count",
            "download_status",
        )

    def get_subtitles(self, movie) -> list[str]:
        return [subtitle.language for subtitle in movie.subtitles.all() if subtitle.status == Subtitle.Status.READY]

    def get_download_status(self, movie) -> str | None:
        download = getattr(movie, "download", None)
        return download.status if download else None


class CommentSerializer(serializers.ModelSerializer):
    comment = serializers.CharField(source="content", max_length=2000, trim_whitespace=True)
    movie_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "movie_id", "username", "comment", "created_at", "updated_at")
        read_only_fields = ("id", "username", "created_at", "updated_at")

    def validate_comment(self, value):
        value = _CONTROL_CHARACTERS.sub("", value).strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value


class CommentCreateSerializer(CommentSerializer):
    movie_id = serializers.IntegerField(min_value=1)


class DownloadRequestSerializer(serializers.Serializer):
    language = serializers.RegexField(r"^[a-z]{2}$", required=False)


class SubtitleSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Subtitle
        fields = ("language", "status", "url")

    def get_url(self, subtitle) -> str | None:
        if subtitle.status != Subtitle.Status.READY:
            return None
        return f"/api/movies/{subtitle.movie_id}/subtitles/{subtitle.language}/?token={self.context['token']}"


class DownloadSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    playable = serializers.SerializerMethodField()
    stream_url = serializers.SerializerMethodField()
    subtitles = serializers.SerializerMethodField()

    class Meta:
        model = Download
        fields = (
            "movie_id",
            "status",
            "progress",
            "download_rate",
            "num_peers",
            "playable",
            "error",
            "stream_url",
            "subtitles",
        )

    def get_progress(self, download) -> float:
        return round(download.progress * 100, 1)

    def get_playable(self, download) -> bool:
        return streaming.is_playable(download)

    def get_stream_url(self, download) -> str | None:
        if not streaming.is_playable(download):
            return None
        return f"/api/movies/{download.movie_id}/stream/?token={self.context['token']}"

    def get_subtitles(self, download) -> list:
        return SubtitleSerializer(download.movie.subtitles.all(), many=True, context=self.context).data
