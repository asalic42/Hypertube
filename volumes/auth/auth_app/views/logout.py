from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.serializers import LogoutSerializer

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        reponse = {204: None,}
        tags="Authentication",
        operation_id="auth_logout"
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valide(raise_exception=True)
        raw_refresh_token = serializer.validated_data["refresh"]

        try:
            refresh_token = RefreshToken(raw_refresh_token)
        except TokenError:
            return Response(
                {
                    "detail":"The refresh token is invalid or revoked."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        token_user_id = refresh_token.get("sub")

        if str(token_user_id) != str(request.user.pk):
            return Reponse(
                {
                    "detail":"The refresh token does not belong to this user."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        
        refresh_token.blacklist()

        return Response(status=status.HTTP_204_NO_CONTENT)