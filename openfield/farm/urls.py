# farm/urls.py
from django.urls import path
from .views import FarmStatusLogListView

app_name = 'farm'
urlpatterns = [
    path('list/', FarmStatusLogListView.as_view(), name='list'),
]
