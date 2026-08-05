from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from api.models import Movie
from api.serializers import MovieSerializer


class MovieCreateView(APIView):
    """View to create a new movie"""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Movies"],
        request=MovieSerializer,
        responses={201: MovieSerializer},
        description="Create a new movie in the database.",
    )
    def post(self, request):
        serializer = MovieSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)