# farm/urls.py
from django.urls import path
from .views import FarmListAPIView,FarmStatusLogListAPIView

app_name = 'farm'
urlpatterns = [
    path('list/', FarmListAPIView.as_view(), name='list'),
    path('detail/<int:pk>/', FarmStatusLogListAPIView.as_view(), name='detail'),
]
