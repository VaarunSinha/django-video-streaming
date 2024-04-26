from datetime import timezone
import os
from celery import shared_task
from django.conf import settings
import logging
from django.core.files.base import ContentFile
import ffmpeg
from .models import Segment

SEGMENT_DURATION = 8
M3U8_FILE_NAME = "output.m3u8"
SEGMENT_FILE_PREFIX = "output"


@shared_task()
def generate_hls(self, segment_duration=SEGMENT_DURATION):
    """
    Generate HLS video segments and M3U8 file for the video.

    Args:
        segment_duration (int): Duration of each segment in seconds

    Returns:
        None
    """
    try:
        # Create the HLS videos directory if it doesn't exist
        self.generating_hls = True
        hls_videos_dir = os.path.abspath(
            os.path.join("hls_videos", timezone.now().strftime("%Y-%m-%d_%H-%M-%S"))
        )
        os.makedirs(hls_videos_dir, exist_ok=True)

        # Specify absolute path for the output M3U8 file
        output_path = os.path.abspath(os.path.join(hls_videos_dir, M3U8_FILE_NAME))

        # Run ffmpeg to split the video into segments
        ffmpeg.input(str(settings.MEDIA_ROOT) + "/" + self.video.name).output(
            output_path, format="hls", hls_time=segment_duration
        ).run()

        # Create segments and upload to the Segment model

        # Save M3U8 content to the hls_file field
        self.hls_file.save(
            M3U8_FILE_NAME,
            ContentFile(open(output_path, "rb").read()),
            save=True,
        )
        for segment_number in range(len(os.listdir(hls_videos_dir)) - 1):
            segment_file_path = os.path.join(
                hls_videos_dir, f"{SEGMENT_FILE_PREFIX}{segment_number}.ts"
            )
            segment_instance = Segment(stream_video=self)
            segment_instance.file.save(
                f"{SEGMENT_FILE_PREFIX}{segment_number}.ts",
                ContentFile(open(segment_file_path, "rb").read()),
                save=True,
            )
    except Exception as e:
        # Handle exceptions if needed
        self.generating_hls = False
        logging.error(f"Error: {e}")

    finally:
        # Clean up temporary directory after ffmpeg has finished
        self.generating_hls = False
        if os.path.exists(hls_videos_dir):
            for file_name in os.listdir(hls_videos_dir):
                file_path = os.path.join(hls_videos_dir, file_name)
                os.remove(file_path)
            os.rmdir(hls_videos_dir)
