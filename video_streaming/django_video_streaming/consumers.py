# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import logging


class TaskProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.task_id = self.scope["url_route"]["kwargs"]["task_id"]
        self.group_name = f"task_progress_{self.task_id}"
        print(self.scope["url_route"]["kwargs"]["task_id"])

        # Join room group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_progress(self, event):
        print("sending progressssss ")
        progress = event["progress"]
        print("Progress: ", progress)
        logging.info(f"Received progress: {progress}")
        await self.send(text_data=str(progress))
