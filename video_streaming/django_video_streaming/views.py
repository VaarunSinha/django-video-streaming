from django.shortcuts import render, get_object_or_404
from django.conf import settings
from .models import DjangoStreamVideo
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist


def serve_m3u8(request, video_id):
    """
    Retrieves the corresponding DjangoStreamVideo object and checks if the hls_file exists.
    If valid, serves the m3u8 file with correct mimetype and caching headers.
    """

    try:
        video = get_object_or_404(DjangoStreamVideo, pk=video_id)

        # Check if hls_file exists and is not empty
        if not video.hls_file or not video.hls_file.size:
            video.generate_hls()

        # Serve the m3u8 file with correct mimetype and caching headers
        response = HttpResponse(
            video.hls_file.read(), content_type="application/vnd.apple.mpegurl"
        )
        response["Cache-Control"] = "max-age=3600"
        return response

    except ObjectDoesNotExist as e:
        return render(request, "error.html", {"error_message": str(e)})
