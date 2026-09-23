from datetime import timedelta

from django.http import HttpResponse, StreamingHttpResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication

from movies_app.authentication import IgnoreClientContentNegotiation, StreamTokenAuthentication
from movies_app.models import Download, Movie, Subtitle, WatchRecord
from movies_app.serializers import DownloadRequestSerializer, DownloadSerializer, SubtitleSerializer
from movies_app.services import catalog, media, storage, streaming, users

from .common import get_movie_or_404

SUBTITLE_RETRY_DELAY = timedelta(days=1)
WATCH_UPDATE_INTERVAL = timedelta(minutes=1)
TOKEN_PARAMETER = OpenApiParameter("token", str, description="Stream token found in the download resource.")


def _serialize(download, request, status_code=status.HTTP_200_OK):
    context = {"token": streaming.make_token(request.user.id, download.movie_id)}
    return Response(DownloadSerializer(download, context=context).data, status=status_code)


def _request_subtitles(movie, language):
    """English whenever it exists, plus the viewer's language when the film is in another one."""
    wanted = {"en"}
    if language != movie.original_language:
        wanted.add(language)
    for code in wanted:
        subtitle, created = Subtitle.objects.get_or_create(movie=movie, language=code)
        retry = subtitle.status == Subtitle.Status.UNAVAILABLE and subtitle.updated_at < timezone.now() - SUBTITLE_RETRY_DELAY
        if not created and retry:
            subtitle.status = Subtitle.Status.PENDING
            subtitle.save(update_fields=["status", "updated_at"])


class MovieDownloadView(APIView):
    """The server-side copy of a movie: PUT asks for it, GET follows it until it is playable."""

    @extend_schema(
        tags=["Playback"],
        operation_id="get_movie_download",
        responses={200: DownloadSerializer, 404: OpenApiResponse(description="This movie was never requested.")},
    )
    def get(self, request, movie_id):
        movie = get_movie_or_404(movie_id)
        download = Download.objects.filter(movie=movie).select_related("movie").first()
        if download is None:
            raise NotFound("This movie has not been requested yet.")
        return _serialize(download, request)

    @extend_schema(
        tags=["Playback"],
        operation_id="request_movie_download",
        request=DownloadRequestSerializer,
        responses={
            200: DownloadSerializer,
            201: DownloadSerializer,
            409: OpenApiResponse(description="No torrent is available for this movie."),
        },
        description=(
            "Idempotent. Starts the torrent in the background when the movie is not on the server yet, "
            "and requests the subtitles for `language` (default: the preferred language of the user)."
        ),
    )
    def put(self, request, movie_id):
        movie = get_movie_or_404(movie_id)
        body = DownloadRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        language = (
            body.validated_data.get("language")
            or users.preferred_language(request.user.username, request.headers.get("Authorization", ""))
            or "en"
        )

        download = Download.objects.filter(movie=movie).first()
        created = False
        if download is None or download.status == Download.Status.FAILED:
            catalog.ensure_source_details(movie)
            candidates = catalog.candidate_torrents(movie)
            if not candidates:
                return Response({"detail": "No torrent is available for this movie."}, status=status.HTTP_409_CONFLICT)
            download, created = Download.objects.update_or_create(
                movie=movie,
                defaults={
                    "torrent": candidates[0],
                    "status": Download.Status.QUEUED,
                    "attempted_torrent_ids": [],
                    "error": "",
                    "progress": 0,
                    "buffered_bytes": 0,
                    "local_path": "",
                    "requested_offset": None,
                },
            )

        _request_subtitles(movie, language)
        download = Download.objects.select_related("movie").get(pk=download.pk)
        return _serialize(download, request, status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MediaView(APIView):
    authentication_classes = [StreamTokenAuthentication, JWTStatelessUserAuthentication]
    content_negotiation_class = IgnoreClientContentNegotiation


def _mark_watched(user_id, movie_id):
    now = timezone.now()
    record, created = WatchRecord.objects.get_or_create(user_id=user_id, movie_id=movie_id)
    if created or record.last_watched_at < now - WATCH_UPDATE_INTERVAL:
        WatchRecord.objects.filter(pk=record.pk).update(last_watched_at=now)
        Movie.objects.filter(pk=movie_id).update(last_watched_at=now)


class MovieStreamView(MediaView):
    @extend_schema(
        tags=["Playback"],
        operation_id="stream_movie",
        parameters=[TOKEN_PARAMETER],
        responses={
            (200, "video/mp4"): bytes,
            (206, "video/mp4"): bytes,
            409: OpenApiResponse(description="Not enough data has been downloaded yet."),
            416: OpenApiResponse(description="Range not satisfiable."),
        },
        description="The video, with HTTP range support. Non browser-ready formats are converted on the fly.",
    )
    def get(self, request, movie_id):
        movie = get_movie_or_404(movie_id)
        download = Download.objects.filter(movie=movie).first()
        if download is None:
            raise NotFound("This movie has not been requested yet.")
        if not streaming.is_playable(download):
            return Response({"detail": "Not enough data has been downloaded yet."}, status=status.HTTP_409_CONFLICT)
        _mark_watched(request.user.id, movie.pk)

        try:
            return self._respond(request, download)
        except media.MediaError:
            raise NotFound("The video file is missing.") from None
        except storage.StorageError:
            return Response({"detail": "The file storage is unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    def _respond(self, request, download):
        ready = download.status == Download.Status.READY
        if not ready and download.needs_transcode:
            # The length of a live conversion is unknown: no ranges, the player reads it front to back.
            body = () if request.method == "HEAD" else streaming.iter_transcoded(download)
            response = StreamingHttpResponse(body, content_type="video/mp4")
            response["Accept-Ranges"] = "none"
            response["Cache-Control"] = "no-store"
            return response

        if ready:
            size, content_type = download.storage_size, download.content_type
        else:
            size = download.file_size
            content_type = "video/webm" if download.local_path.lower().endswith(".webm") else "video/mp4"

        try:
            byte_range = streaming.parse_range(request.headers.get("Range"), size)
        except streaming.RangeNotSatisfiable:
            response = HttpResponse(status=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE)
            response["Content-Range"] = f"bytes */{size}"
            return response
        start, end = byte_range or (0, size - 1)

        if request.method == "HEAD":
            body = ()
        elif ready:
            chunks = streaming.iter_storage(download.storage_key, start, end)
            # Reading the first chunk now turns a storage outage into a 503 instead of a broken stream.
            body = _chain(next(chunks, b""), chunks)
        else:
            body = streaming.iter_local(download, start, end)

        response = StreamingHttpResponse(
            body,
            status=status.HTTP_206_PARTIAL_CONTENT if byte_range else status.HTTP_200_OK,
            content_type=content_type,
        )
        response["Accept-Ranges"] = "bytes"
        response["Content-Length"] = str(end - start + 1)
        response["Cache-Control"] = "no-store"
        if byte_range:
            response["Content-Range"] = f"bytes {start}-{end}/{size}"
        return response


def _chain(first, rest):
    try:
        yield first
        yield from rest
    finally:
        rest.close()


class MovieSubtitleListView(APIView):
    @extend_schema(tags=["Playback"], operation_id="list_movie_subtitles", responses=SubtitleSerializer(many=True))
    def get(self, request, movie_id):
        movie = get_movie_or_404(movie_id)
        context = {"token": streaming.make_token(request.user.id, movie.pk)}
        return Response(SubtitleSerializer(movie.subtitles.all(), many=True, context=context).data)


class MovieSubtitleView(MediaView):
    @extend_schema(
        tags=["Playback"],
        operation_id="get_movie_subtitle",
        parameters=[TOKEN_PARAMETER],
        responses={(200, "text/vtt"): str},
        description="A WebVTT track for the <track> element.",
    )
    def get(self, request, movie_id, language):
        movie = get_movie_or_404(movie_id)
        subtitle = Subtitle.objects.filter(movie=movie, language=language, status=Subtitle.Status.READY).first()
        if subtitle is None:
            raise NotFound("No subtitle in this language.")
        try:
            content = storage.read(subtitle.storage_key)
        except storage.StorageError:
            return Response({"detail": "The file storage is unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        response = HttpResponse(content, content_type="text/vtt; charset=utf-8")
        response["Cache-Control"] = "private, max-age=3600"
        return response
