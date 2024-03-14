from django.urls import path
from .views import serve_m3u8

urlpatterns = [
    # ... other URL patterns
    path("<int:video_id>/", serve_m3u8, name="serve_m3u8"),
]
