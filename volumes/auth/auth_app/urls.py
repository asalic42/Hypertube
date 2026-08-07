from django.urls import include, path

from .views import (
    HealthView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    RegisterView,
    VerifyView,
)


auth_urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    # path("login/", LoginView.as_view(), name="login"),
    path("delete/<int:user_id>/", views.DeleteUserView.as_view(), name="delete_user"),
]


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    *auth_urlpatterns
]
