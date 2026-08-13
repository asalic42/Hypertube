from django.urls import include, path

from .views import HealthView
from . import views 


user_urlpatterns = [
        path('', views.PublicUserListCreate.as_view(), name='user-list'),
        path('<uuid:user_id>/', views.PublicUserView.as_view(), name='user'),
        path('<uuid:user_id>/avatar/', views.PublicUserAvatarView.as_view(), name='user-avatar'),
]


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    *user_urlpatterns,
]