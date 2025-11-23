from abc import ABC, abstractmethod
import asyncio
import json
import socket
from typing import Awaitable, Callable, Dict

from valkey.asyncio import Valkey
from valkey.exceptions import ValkeyError, TimeoutError

class PubSubAdapter(ABC):
    @abstractmethod
    async def publish(self, channel: str, message: Dict) -> None:
        pass

    @abstractmethod
    async def subscribe(self, channel: str, callback: Callable[[Dict], Awaitable[None]]) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

class ValkeyPubSubAdapter(PubSubAdapter):
    def __init__(self, host: str, port: int, ssl: bool = False) -> None:
        self.pub_client = Valkey(
            host=host, 
            port=port, 
            ssl=ssl,
            decode_responses=True,
        )

        self.sub_client = Valkey(
            host=host, 
            port=port, 
            ssl=ssl,
            decode_responses=True,
            health_check_interval=0,
            
            socket_timeout=None,
            
            socket_keepalive=True,
            socket_keepalive_options={
                socket.TCP_KEEPIDLE: 15,
                socket.TCP_KEEPINTVL: 5,
                socket.TCP_KEEPCNT: 3,
            }
        )

        self.pubsub = None
        self._is_active = True

    async def publish(self, channel: str, message: Dict) -> None:
        await self.pub_client.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str, callback: Callable[[Dict], Awaitable[None]]) -> None:
        self.pubsub = self.sub_client.pubsub()
        await self.pubsub.subscribe(channel)

        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        payload = json.loads(message["data"])
                        if payload.get("intent") != "heartbeat":
                            await callback(payload)
                    except Exception as e:
                        print(f"Error processing message: {e}")
                        
        except Exception as e:
            print(f"Subscription connection lost: {e}")
            raise e
        finally:
            if self.pubsub:
                await self.pubsub.close()

    async def close(self) -> None:
        if self.pubsub:
            await self.pubsub.close()
        await self.pub_client.aclose()
        await self.sub_client.aclose()
