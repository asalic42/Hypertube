from django.urls import path

from . import views

movies_urlpatterns = [
    path("", views.MovieListView.as_view(), name="movie-list"),
    path("genres/", views.GenreListView.as_view(), name="genre-list"),
    path("<int:movie_id>/", views.MovieDetailView.as_view(), name="movie-detail"),
    path("<int:movie_id>/comments/", views.MovieCommentListView.as_view(), name="movie-comment-list"),
    path("<int:movie_id>/download/", views.MovieDownloadView.as_view(), name="movie-download"),
    path("<int:movie_id>/stream/", views.MovieStreamView.as_view(), name="movie-stream"),
    path("<int:movie_id>/subtitles/", views.MovieSubtitleListView.as_view(), name="movie-subtitle-list"),
    path("<int:movie_id>/subtitles/<str:language>/", views.MovieSubtitleView.as_view(), name="movie-subtitle"),
]

comments_urlpatterns = [
    path("", views.CommentListView.as_view(), name="comment-list"),
    path("<int:comment_id>/", views.CommentDetailView.as_view(), name="comment-detail"),
]

urlpatterns = [
    path("health/", views.HealthView.as_view(), name="health"),
    *movies_urlpatterns,
]
