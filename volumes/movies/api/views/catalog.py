from pathlib import Path

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import (
    ArchiveCatalogQuerySerializer,
    ArchiveCatalogResponseSerializer,
    ArchiveDownloadCreateSerializer,
    ArchiveDownloadProgressResponseSerializer,
    ArchiveDownloadStartResponseSerializer,
)
from api.services.archive import (
    get_archive_download_progress,
    search_archive_catalog,
    start_archive_video_download,
)


class ArchiveCatalogView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        serializer = ArchiveCatalogQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data["q"]
        limit_value = serializer.validated_data["limit"]

        results = search_archive_catalog(query=query, limit=limit_value)
        response_serializer = ArchiveCatalogResponseSerializer(
            {"query": query, "limit": limit_value, "results": results}
        )
        return Response(response_serializer.data)


class ArchiveDownloadView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = ArchiveDownloadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"]

        destination_dir = serializer.validated_data.get("destination_dir") or str(
            Path(settings.BASE_DIR) / "downloads"
        )

        try:
            payload = start_archive_video_download(identifier, destination_dir)
        except ValueError as error:
            return Response({"detail": str(error)}, status=404)

        payload["progress_url"] = request.build_absolute_uri(
            f"/api/movies/download/{payload['job_id']}/progress/"
        )
        response_serializer = ArchiveDownloadStartResponseSerializer(payload)
        return Response(response_serializer.data, status=202)


class ArchiveDownloadProgressView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, job_id: str):
        try:
            payload = get_archive_download_progress(job_id)
        except KeyError:
            return Response({"detail": "Téléchargement introuvable."}, status=404)

        response_serializer = ArchiveDownloadProgressResponseSerializer(payload)
        return Response(response_serializer.data)

class ArchiveRetrieveDownloadsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        from api.services.archive import _get_jobs

        jobs = _get_jobs()
        response_serializer = ArchiveDownloadProgressResponseSerializer(jobs, many=True)
        return Response(response_serializer.data)