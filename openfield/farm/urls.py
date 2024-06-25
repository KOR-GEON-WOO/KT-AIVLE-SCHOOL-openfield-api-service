# farm/urls.py
from django.urls import path
from .views import FarmStatusLogListView,FarmStatusLogDetailView

app_name = 'farm'
urlpatterns = [
    path('list/', FarmStatusLogListView.as_view(), name='list'),
    path('detail/<int:pk>/', FarmStatusLogDetailView.as_view(), name='detail'),
]
