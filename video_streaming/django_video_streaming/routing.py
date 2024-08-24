# routing.py
from django.urls import path
from .consumers import TaskProgressConsumer

websocket_urlpatterns = [
    path("ws/task_progress/<uuid:task_id>/", TaskProgressConsumer.as_asgi()),
]
