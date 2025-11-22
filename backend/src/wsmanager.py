from typing import Dict, List, Optional
from fastapi import WebSocket
import asyncio
import json

from adapters.pubsub import PubSubAdapter

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []
        self.pubsub: Optional[PubSubAdapter] = None
        self.channel_name = "canvas_updates"
        self._listener_task: Optional[asyncio.Task] = None

    def init_pubsub(self, pubsub_adapter: PubSubAdapter):
        self.pubsub = pubsub_adapter

    async def start_listening(self):
        if not self.pubsub:
            raise RuntimeError("PubSub adapter not initialized")
        
        self._listener_task = asyncio.create_task(self._subscribe_loop())

    async def _subscribe_loop(self):
        while True:
            try:
                if self.pubsub:
                    await self.pubsub.subscribe(self.channel_name, self._handle_broadcast)
            except asyncio.CancelledError:
                # Task cancelled during shutdown
                break
            except Exception as e:
                print(f"PubSub subscription error: {e}. Retrying in 3s...")
                await asyncio.sleep(3)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active.remove(websocket)
        except ValueError:
            pass

    async def _handle_broadcast(self, message: Dict):
        data = json.dumps(message)
        to_remove = []
        for ws in list(self.active):
            try:
                await ws.send_text(data)
            except Exception:
                to_remove.append(ws)
        for ws in to_remove:
            self.disconnect(ws)

    async def broadcast(self, message: Dict):
        if self.pubsub:
            try:
                await self.pubsub.publish(self.channel_name, message)
            except Exception as e:
                print(f"Failed to publish message: {e}")
        else:
            print("PubSub not configured - update dropped")

    async def shutdown(self):
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            await self.pubsub.close()

manager = ConnectionManager()
