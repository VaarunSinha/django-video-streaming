from django.urls import path
from .views import create_celery_task, send_fake_progress

urlpatterns = [
    path("api/create_task/", create_celery_task, name="create_celery_task"),
    path("api/fake-event/<str:task_id>/", send_fake_progress, name="fake-prog"),
]
