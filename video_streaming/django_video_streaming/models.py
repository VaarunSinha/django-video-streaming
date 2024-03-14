import ffmpeg  # Import ffmpeg library for video processing
import os  # Import os library for operating system functionalities
from django.db import models
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.db import transaction
import asyncio
from asgiref.sync import async_to_sync
from django.conf import settings
import logging

SEGMENT_DURATION = 8
M3U8_FILE_NAME = "output.m3u8"
SEGMENT_FILE_PREFIX = "output"


class Segment(models.Model):
    stream_video = models.ForeignKey(
        "DjangoStreamVideo", on_delete=models.CASCADE, related_name="segments"
    )

    def upload_to_path(instance, filename):
        return os.path.join(
            "django-video-streaming/hls_videos",
            instance.stream_video.video.name.split("/")[-1],
            filename,
        )

    file = models.FileField(upload_to=upload_to_path)


class DjangoStreamVideo(models.Model):
    video = models.FileField(
        upload_to="django-video-streaming/videos/",
        validators=[FileExtensionValidator(allowed_extensions=["mp4"])],
    )

    def upload_to_path(instance, filename):
        return os.path.join(
            "django-video-streaming/hls_videos",
            instance.video.name.split("/")[-1],
            filename,
        )

    hls_file = models.FileField(upload_to=upload_to_path, blank=True, null=True)
    generating_hls = False

    def save(self, *args, **kwargs):
        """
        Save method to trigger HLS generation if enabled in settings.

        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments

        Returns:
            None
        """
        # Your existing save logic here
        if getattr(settings, "HLS_GENERATION_ENABLED_ON_SAVE", False):
            if self.generating_hls == False:
                self.generate_hls()
        super().save(*args, **kwargs)

    @transaction.atomic
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
