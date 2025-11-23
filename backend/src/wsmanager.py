from typing import Dict, List, Optional
from fastapi import WebSocket
import asyncio
import json

from adapters.pubsub import PubSubAdapter
from config import config

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []
        self.pubsub: Optional[PubSubAdapter] = None
        self.channel_name = "canvas_updates"

        self._listener_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    def init_pubsub(self, pubsub_adapter: PubSubAdapter):
        self.pubsub = pubsub_adapter

    async def start_listening(self):
        if not self.pubsub:
            raise RuntimeError("PubSub adapter not initialized")
        
        self._listener_task = asyncio.create_task(self._subscribe_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _subscribe_loop(self):
        while True:
            try:
                if self.pubsub:
                    await self.pubsub.subscribe(self.channel_name, self._handle_broadcast)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Listener crashed. Restarting in 2s... Error: {e}")
                await asyncio.sleep(2)

    async def _heartbeat_loop(self):
        while True:
            try:
                await asyncio.sleep(config.heartbeat_interval)
                await self.broadcast({"intent": "heartbeat"})
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Heartbeat error: {e}")
                await asyncio.sleep(5)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def _handle_broadcast(self, message: Dict):
        data = json.dumps(message)
        to_remove = []
        for ws in self.active:
            try:
                await ws.send_text(data)
            except Exception:
                to_remove.append(ws)
        
        for ws in to_remove:
            self.disconnect(ws)

    async def broadcast(self, message: Dict):
        if self.pubsub:
            await self.pubsub.publish(self.channel_name, message)

    async def shutdown(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        if self.pubsub:
            await self.pubsub.close()

manager = ConnectionManager()
