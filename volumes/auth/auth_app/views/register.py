from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from auth_app.cookies import set_refresh_cookie
from auth_app.models import User
from auth_app.serializers import CustomTokenObtainPairSerializer, RegisterSerializer, UserSerializer


@method_decorator(csrf_protect, name="dispatch")
@extend_schema_view(
    post=extend_schema(
        tags=["Authentication"],
        operation_id="auth_register",
        responses={201: CustomTokenObtainPairSerializer},
        description=(
            "Creates the account and logs it in: the answer carries the access token "
            "and sets the refresh cookie, like a login, so the profile can be created right away."
        ),
    )
)
class RegisterView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "register"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = CustomTokenObtainPairSerializer.get_token(user)
        response = Response(
            {"user": UserSerializer(user).data, "access": str(refresh.access_token)},
            status=status.HTTP_201_CREATED,
        )
        set_refresh_cookie(response, str(refresh))
        return response
