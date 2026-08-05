from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView


class DeleteUserView(APIView):
    authentication_classes = []
    permission_classes = []

    def delete(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        user.delete()

        return Response({"message": "User deleted successfully"})