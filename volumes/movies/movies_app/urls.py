from django.urls import include, path

from .views import ArchiveCatalogView, ArchiveDownloadProgressView, ArchiveDownloadView, HealthView, ArchiveRetrieveDownloadsView


movies_urlpatterns = [
    path("catalog/", ArchiveCatalogView.as_view(), name="archive-catalog"),
    path("download/", ArchiveDownloadView.as_view(), name="archive-download"),
    path("retrieve-downloads/", ArchiveRetrieveDownloadsView.as_view(), name="retrieve-archive-downloads"),
    path("download/<str:job_id>/progress/", ArchiveDownloadProgressView.as_view(), name="archive-download-progress"),
    path("create/", views.MovieCreateView.as_view(), name="movie-create"),
]


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    *movies_urlpatterns,
]