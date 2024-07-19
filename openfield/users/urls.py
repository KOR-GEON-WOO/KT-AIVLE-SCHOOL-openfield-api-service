from django.urls import path
from .views import *

urlpatterns = [
    path('signup/', UserCreateAPIView.as_view(), name='signup'),
    path('login/', UserLoginAPIView.as_view(), name='login'),
    path('logout/', UserLogoutAPIView.as_view(), name='logout'),
    path('authorization/', UserAuthorizationView.as_view(), name='authorization'),
    path('check-dup/', UserisExistView.as_view(), name='checkdup')
]

