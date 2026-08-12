from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.cookies import delete_refresh_cookie
from django.conf import settings

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses = {204: None,},
        tags=["Authentication"],
        operation_id="auth_logout"
    )
    def post(self, request):
        raw_refresh_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        
        if raw_refresh_token:
            try:
                refresh_token = RefreshToken(raw_refresh_token)
                token_uder_id = refresh_token.get("sub")
        
                if str(token_uder_id) == str(request.user.pk):
                    refresh_token.blacklist()
            except TokenError:
                pass
        
        response = Response(status=status.HTTP_204_NO_CONTENT)
        delete_refresh_cookie(response)
        return response
