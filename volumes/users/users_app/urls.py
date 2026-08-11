from django.urls import include, path

from .views import HealthView
from . import views 


user_urlpatterns = [
        path('', views.PublicUserList.as_view(), name='user-list'),
        path('create/', views.PublicUserCreate.as_view(), name='user-create'),
        path('<str:username>/', views.PublicUserGetDetail.as_view(), name='user-detail'),
        path('<str:username>/avatar', views.PublicUserGetAvatar.as_view(), name='user-avatar'),
        path('<str:username>/update', views.PublicUserUpdate.as_view(), name='user-update'),
        path('<str:username>/avatar/update', views.PublicUserUpdateAvatar.as_view(), name='user-update-avatar'),
        path('<str:username>/avatar/delete', views.PublicUserDeleteAvatar.as_view(), name='user-delete-avatar'),
        path('delete/<str:username>/', views.PublicUserDelete.as_view(), name='user-delete'),
]


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    *user_urlpatterns,
]