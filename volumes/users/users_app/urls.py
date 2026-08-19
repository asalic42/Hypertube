from django.urls import include, path

from .views import HealthView
from . import views 


user_urlpatterns = [
        path('', views.PublicUserListCreate.as_view(), name='user-list'),
        path('<str:username>/', views.PublicUserView.as_view(), name='user'),
        path('<str:username>/avatar/', views.PublicUserAvatarView.as_view(), name='user-avatar'),
]


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    *user_urlpatterns,
]