import os
import logging
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import Segment
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from ffmpeg_progress_yield import FfmpegProgress
from .models import DjangoStreamVideo

M3U8_FILE_NAME = "output.m3u8"
SEGMENT_FILE_PREFIX = "output"


@shared_task(bind=True)
def generate_hls(self, video_id, segment_duration):
    """
    Generate HLS video segments and M3U8 file for the video.

    Args:
        segment_duration (int): Duration of each segment in seconds

    Returns:
        None
    """

    channel_layer = get_channel_layer()

    task_id = self.request.id
    group_name = f"task_progress_{task_id}"

    video = DjangoStreamVideo.objects.get(id=video_id)
    hls_videos_dir = None
    print(group_name)
    try:
        # Create the HLS videos directory if it doesn't exist
        video.generating_hls = True
        hls_videos_dir = os.path.abspath(
            os.path.join("hls_videos", timezone.now().strftime("%Y-%m-%d_%H-%M-%S"))
        )
        os.makedirs(hls_videos_dir, exist_ok=True)

        # Specify absolute path for the output M3U8 file
        output_path = os.path.abspath(os.path.join(hls_videos_dir, M3U8_FILE_NAME))

        # Run ffmpeg to split the video into segments using FfmpegProgress
        cmd = [
            "ffmpeg",
            "-i",
            str(settings.MEDIA_ROOT) + "/" + video.video.name,
            "-c:v",
            "libx264",
            "-hls_time",
            str(segment_duration),
            "-hls_list_size",
            "0",
            "-f",
            "hls",
            output_path,
        ]
        ff = FfmpegProgress(cmd)
        async_to_sync(channel_layer.group_send)(
            group_name, {"type": "send_progress", "progress": 0}
        )

        print("Progress: 0%")
        for progress in ff.run_command_with_progress():
            print(f"Progress: {progress}%")
            async_to_sync(channel_layer.group_send)(
                group_name, {"type": "send_progress", "progress": progress}
            )

        # Create segments and upload to the Segment model
        for segment_number in range(len(os.listdir(hls_videos_dir)) - 1):
            segment_file_path = os.path.join(
                hls_videos_dir, f"{SEGMENT_FILE_PREFIX}{segment_number}.ts"
            )
            segment_instance = Segment(stream_video=video)
            segment_instance.file.save(
                f"{SEGMENT_FILE_PREFIX}{segment_number}.ts",
                ContentFile(open(segment_file_path, "rb").read()),
                save=True,
            )

        # Save M3U8 content to the hls_file field
        video.hls_file.save(
            M3U8_FILE_NAME,
            ContentFile(open(output_path, "rb").read()),
            save=True,
        )

    except Exception as e:
        # Handle exceptions if needed
        video.generating_hls = False
        logging.error(f"Error: {e}")

    finally:
        # Clean up temporary directory after ffmpeg has finished
        video.generating_hls = False
        if os.path.exists(hls_videos_dir):
            for file_name in os.listdir(hls_videos_dir):
                file_path = os.path.join(hls_videos_dir, file_name)
                os.remove(file_path)
            os.rmdir(hls_videos_dir)
