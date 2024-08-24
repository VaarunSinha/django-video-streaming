from django.http import JsonResponse
from .tasks import generate_hls
from .models import DjangoStreamVideo


def create_celery_task(request, **kwargs):
    video_id = request.GET.get("video_id")
    segment_duration = request.GET.get("segment_duration")

    # Ensure both video_id and segment_duration are provided
    if video_id is None or segment_duration is None:
        return JsonResponse(
            {"error": "Both video_id and segment_duration are required."}, status=400
        )

    try:
        video = DjangoStreamVideo.objects.get(pk=video_id)
    except DjangoStreamVideo.DoesNotExist:
        return JsonResponse({"error": "Video not found."}, status=404)

    # Optionally, you can validate the segment duration here

    task = generate_hls.delay(
        video_id=video_id, segment_duration=segment_duration
    )  # Pass video object and segment duration to the task
    return JsonResponse({"task_id": task.id})  # Return the task ID


from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.http import JsonResponse


def send_fake_progress(request, task_id):
    # Trigger a fake progress event
    channel_layer = get_channel_layer()
    group_name = f"task_progress_{task_id}"

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "send_progress",
            "progress": "50%",  # Sample progress update
        },
    )
    return JsonResponse({"status": "ok"})
