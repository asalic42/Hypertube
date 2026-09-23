from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from movies_app.models import Comment
from movies_app.pagination import PagePagination
from movies_app.permissions import IsAuthorOrReadOnly
from movies_app.serializers import CommentCreateSerializer, CommentSerializer
from movies_app.services import catalog

from .common import get_movie_or_404


def _save(serializer, request, movie):
    # The author always comes from the token, never from the payload.
    serializer.save(movie=movie, user_id=request.user.id, username=request.user.username)


@extend_schema_view(
    get=extend_schema(tags=["Comments"], operation_id="list_comments", description="Latest comments first."),
    post=extend_schema(
        tags=["Comments"],
        operation_id="create_comment",
        request=CommentCreateSerializer,
        responses={201: CommentSerializer},
    ),
)
class CommentListView(ListCreateAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    pagination_class = PagePagination

    def create(self, request, *args, **kwargs):
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movie = catalog.resolve_movie(serializer.validated_data.pop("movie_id"))
        if movie is None:
            raise ValidationError({"movie_id": ["Unknown movie."]})
        _save(serializer, request, movie)
        return Response(CommentSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=["Comments"], operation_id="list_movie_comments"),
    post=extend_schema(tags=["Comments"], operation_id="create_movie_comment"),
)
class MovieCommentListView(ListCreateAPIView):
    serializer_class = CommentSerializer
    pagination_class = PagePagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Comment.objects.none()
        return Comment.objects.filter(movie=get_movie_or_404(self.kwargs["movie_id"]))

    def perform_create(self, serializer):
        _save(serializer, self.request, get_movie_or_404(self.kwargs["movie_id"]))


@extend_schema_view(
    get=extend_schema(tags=["Comments"], operation_id="get_comment"),
    patch=extend_schema(tags=["Comments"], operation_id="update_comment"),
    delete=extend_schema(tags=["Comments"], operation_id="delete_comment"),
)
class CommentDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]
    lookup_url_kwarg = "comment_id"
    http_method_names = ["get", "patch", "delete", "head", "options"]
