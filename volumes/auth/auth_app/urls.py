from django.urls import include, path

from .views import (
    HealthView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    RegisterView,
    VerifyView,
    CsrfTokenView,
    ForgotPasswordView,
    ResetPasswordView,
    FortyTwoStartView,
    FortyTwoCallbackView,
)


auth_urlpatterns = [
    path("csrf/", CsrfTokenView.as_view(), name="csrf"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_pass"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset_pass"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("verify/", VerifyView.as_view(), name="verify"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path(
        "oauth/42/start/",
        FortyTwoStartView.as_view(),
        name="oauth-42-start",
    ),
    path(
        "oauth/42/callback/",
        FortyTwoCallbackView.as_view(),
        name="oauth-42-callback",
    ),
]


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    *auth_urlpatterns
]
