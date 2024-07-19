# farm/urls.py
from django.urls import path
from .views import *

app_name = 'farm'
urlpatterns = [
    path('admin/list/', FarmAdminListAPIView.as_view(), name='adminList'),
    path('admin/detail/<int:pk>/', FarmAdminDetailView.as_view(), name='adminDetail'),
    path('user/list/', FarmUserListView.as_view(), name='userList'),
    path('user/detail/<int:pk>/', FarmUserDetailView.as_view(), name='userDetail'),
    path('iblist/', FarmIbDetectedListAPIView.as_view(), name='iblist'),
    path('ibdetail/<int:pk>/', FarmIbDetectedDetailView.as_view(), name='ibdetail'),
    path('user/mypage/', FarmUserMypageListView.as_view(), name='userMypage'),
    path('admin/mypage/', FarmAdminMypageListView.as_view(), name='adminMypage'),
    path('admin/mypage/detail/<int:pk>/', FarmAdminMypageDetailView.as_view(), name='adminMypageDetail'),
    path('cddetail/<int:pk>/', FarmChangeDetectionView.as_view(), name='cdDetail'),
]
