# blog/urls.py
from django.urls import path
from .views import ChatAPIView, SessionClearAPIView

app_name = 'chatbot'
urlpatterns = [

    path('chat/', ChatAPIView.as_view(), name='chat'),
    path('clear-session/', SessionClearAPIView.as_view(), name='clear-session'),


]
