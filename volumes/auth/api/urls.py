from django.urls import include, path

from .views import HealthView
from .views import RegisterView
from . import views


user_urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    # path("login/", LoginView.as_view(), name="login"),
    path("delete/<int:user_id>/", views.DeleteUserView.as_view(), name="delete_user"),
]


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/", include((user_urlpatterns, "api"))),
]
