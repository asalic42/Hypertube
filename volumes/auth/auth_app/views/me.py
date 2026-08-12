from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from django.conf import settings
from auth_app.serializers import UserSerializer
from auth_app.cookies import delete_refresh_cookie

class MeView(RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    @extend_schema(
        tags=["Authentication"],
        operation_id="auth_current_user",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Authentication"],
        operation_id="auth_delete_current_user",
    )
    def delete(self, request, *args, **kwargs):
        raw_refresh_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)

        if raw_refresh_token:
            try:
                refresh_token = RefreshToken(raw_refresh_token)
                token_user_id = refresh_token.get("sub")
                if str(token_user_id) == str(request.user.pk):
                    refresh_token.blacklist()
            except:
                pass

        request.user.delete()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        delete_refresh_cookie(response)
        return response