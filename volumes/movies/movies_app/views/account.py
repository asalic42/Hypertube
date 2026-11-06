from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from movies_app.models import Comment, WatchRecord


class MyDataView(APIView):
    """Everything this service holds about the caller, erased when their account goes."""

    @extend_schema(
        tags=["Account"],
        operation_id="delete_my_data",
        request=None,
        responses={204: None},
        description="Erase the caller's comments and watch history. Called by the auth service when an account is deleted.",
    )
    def delete(self, request):
        Comment.objects.filter(user_id=request.user.id).delete()
        WatchRecord.objects.filter(user_id=request.user.id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
