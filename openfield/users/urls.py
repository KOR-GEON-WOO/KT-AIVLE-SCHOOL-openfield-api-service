from django.urls import path
from .views import UserCreateAPIView, UserLoginAPIView, UserLogoutAPIView, UserAuthorizationView

urlpatterns = [
    path('signup/', UserCreateAPIView.as_view(), name='signup'),
    path('login/', UserLoginAPIView.as_view(), name='login'),
    path('logout/', UserLogoutAPIView.as_view(), name='logout'),
    path('authorization/', UserAuthorizationView.as_view(), name='authorization'),
]

