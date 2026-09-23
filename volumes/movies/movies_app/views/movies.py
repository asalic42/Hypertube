from django.db.models import Count, Exists, F, OuterRef, Value
from django.db.models.functions import Lower
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from movies_app.models import Genre, Movie, WatchRecord
from movies_app.pagination import PagePagination
from movies_app.serializers import MovieDetailSerializer, MovieListQuerySerializer, MovieListSerializer
from movies_app.services import catalog

from .common import get_movie_or_404

# Metadata fetched while the user waits: (movies, seconds) per step.
SEARCH_ENRICHMENT = (20, 3.0)
PAGE_ENRICHMENT_TIMEOUT = 2.0

ORDERINGS = {
    "name": (Lower("title").asc(),),
    "-name": (Lower("title").desc(),),
    "year": (F("year").asc(nulls_last=True),),
    "-year": (F("year").desc(nulls_last=True),),
    "rating": (F("rating").asc(nulls_last=True),),
    "-rating": (F("rating").desc(nulls_last=True),),
    "popularity": ("popularity", "vote_count"),
    "-popularity": ("-popularity", "-vote_count"),
}


def with_watched(queryset, user):
    if not user.is_authenticated:
        return queryset.annotate(watched=Value(False))
    return queryset.annotate(watched=Exists(WatchRecord.objects.filter(user_id=user.id, movie=OuterRef("pk"))))


class MovieListView(GenericAPIView):
    """
    The library. Without a search it lists the most popular videos of the
    external sources; with one it queries them and sorts the results by name.
    """

    permission_classes = [AllowAny]
    serializer_class = MovieListSerializer
    pagination_class = PagePagination

    @extend_schema(
        tags=["Movies"],
        operation_id="list_movies",
        parameters=[
            MovieListQuerySerializer,
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        description=(
            "Anonymous requests only get the front page: the first page of the most popular movies. "
            "Searching, filtering and sorting need authentication."
        ),
    )
    def get(self, request):
        authenticated = request.user.is_authenticated
        query = MovieListQuerySerializer(data=request.query_params if authenticated else {})
        query.is_valid(raise_exception=True)
        params = query.validated_data

        movies = Movie.objects.all()
        words = catalog.search_words(params["search"])
        if words:
            catalog.refresh_search(words)
            movies = catalog.filter_by_words(movies, words)
            # Filters and sorting rely on metadata: fetch it for the best matches right away.
            catalog.enrich_listing(movies.order_by("-popularity"), *SEARCH_ENRICHMENT)
        else:
            catalog.refresh_popular()

        if params["genre"]:
            movies = movies.filter(genres__name__iexact=params["genre"])
        for field, lookup in (
            ("year_min", "year__gte"),
            ("year_max", "year__lte"),
            ("rating_min", "rating__gte"),
            ("rating_max", "rating__lte"),
        ):
            if field in params:
                movies = movies.filter(**{lookup: params[field]})

        ordering = ORDERINGS[params.get("sort") or ("name" if words else "-popularity")]
        movies = with_watched(movies, request.user).order_by(*ordering, "id").prefetch_related("genres")

        if not authenticated:
            # The public front page is a single, fixed page.
            page = list(movies[: PagePagination.page_size])
            if self.enrich_page(page):
                page = list(movies[: PagePagination.page_size])
            return Response(
                {
                    "count": len(page),
                    "page": 1,
                    "pages": 1,
                    "next_page": None,
                    "results": self.get_serializer(page, many=True).data,
                }
            )

        page = self.paginate_queryset(movies)
        if self.enrich_page(page):
            page = self.paginate_queryset(movies)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @staticmethod
    def enrich_page(page):
        shown = Movie.objects.filter(pk__in=[movie.pk for movie in page])
        return catalog.enrich_listing(shown, limit=len(page), timeout=PAGE_ENRICHMENT_TIMEOUT)


class MovieDetailView(GenericAPIView):
    serializer_class = MovieDetailSerializer

    @extend_schema(tags=["Movies"], operation_id="get_movie")
    def get(self, request, movie_id):
        movie = get_movie_or_404(movie_id)
        if catalog.enrich_pending(Movie.objects.filter(pk=movie.pk), limit=1, timeout=15):
            movie = get_movie_or_404(movie_id)  # it may just have been merged into its twin
        movie = (
            with_watched(Movie.objects.filter(pk=movie.pk), request.user)
            .annotate(comments_count=Count("comments"))
            .select_related("download")
            .prefetch_related("genres", "sources", "subtitles")
            .get()
        )
        return Response(self.get_serializer(movie).data)


class GenreListView(GenericAPIView):
    @extend_schema(
        tags=["Movies"],
        operation_id="list_genres",
        responses={200: {"type": "array", "items": {"type": "string"}}},
        description="Genres known to the library, to build the genre filter.",
    )
    def get(self, request):
        return Response(list(Genre.objects.filter(movies__isnull=False).distinct().values_list("name", flat=True)))
