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
    OAuthStartView,
    OAuthCallbackView,
    OAuthTokenView,
    ApiClientListView,
    ApiClientDetailView,
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
    path("oauth/token/", OAuthTokenView.as_view(), name="oauth-token"),
    path("oauth/clients/", ApiClientListView.as_view(), name="oauth-clients"),
    path("oauth/clients/<uuid:client_id>/", ApiClientDetailView.as_view(), name="oauth-client"),
    path(
        "oauth/42/start/",
        OAuthStartView.as_view(provider="42"),
        name="oauth-42-start",
    ),
    path(
        "oauth/42/callback/",
        OAuthCallbackView.as_view(provider="42"),
        name="oauth-42-callback",
    ),
    path(
        "oauth/github/start/",
        OAuthStartView.as_view(provider="github"),
        name="oauth-github-start",
    ),
    path(
        "oauth/github/callback/",
        OAuthCallbackView.as_view(provider="github"),
        name="oauth-github-callback",
    ),
    path(
        "oauth/google/start/",
        OAuthStartView.as_view(provider="google"),
        name="oauth-google-start",
    ),
    path(
        "oauth/google/callback/",
        OAuthCallbackView.as_view(provider="google"),
        name="oauth-google-callback",
    ),
    path(
        "oauth/discord/start/",
        OAuthStartView.as_view(provider="discord"),
        name="oauth-discord-start",
    ),
    path(
        "oauth/discord/callback/",
        OAuthCallbackView.as_view(provider="discord"),
        name="oauth-discord-callback",
    ),
]


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    *auth_urlpatterns
]
