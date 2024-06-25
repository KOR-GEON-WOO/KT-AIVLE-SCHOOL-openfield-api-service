# farm/urls.py
from django.urls import path
from .views import *

app_name = 'farm'
urlpatterns = [
    path('list/', FarmListAPIView.as_view(), name='list'),
    path('detail/<int:pk>/', FarmDetailView.as_view(), name='detail'),
]
