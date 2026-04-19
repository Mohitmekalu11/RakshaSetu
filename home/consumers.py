from channels.generic.websocket import AsyncWebsocketConsumer
import json

class CrimeReportConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("crime_alerts", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("crime_alerts", self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message')

        await self.channel_layer.group_send(
            "crime_alerts",
            {
                'type': 'crime_message',
                'message': message
            }
        )

    async def crime_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({'message': message}))
