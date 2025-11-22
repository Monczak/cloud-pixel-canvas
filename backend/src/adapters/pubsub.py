from abc import ABC, abstractmethod
import json
from typing import Awaitable, Callable, Dict

from valkey.asyncio import Valkey

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
    def __init__(self, host: str, port: int) -> None:
        self.valkey = Valkey(host=host, port=port, decode_responses=True)
        self.pubsub = None

        self._is_active = True

    async def publish(self, channel: str, message: Dict) -> None:
        await self.valkey.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str, callback: Callable[[Dict], Awaitable[None]]) -> None:
        self.pubsub = self.valkey.pubsub()
        await self.pubsub.subscribe(channel)

        try:
            async for message in self.pubsub.listen():
                if not self._is_active:
                    break

                if message["type"] == "message":
                    try:
                        payload = json.loads(message["data"])
                        await callback(payload)
                    except Exception as e:
                        print(f"Error processing pubsub message: {e}")
        except Exception as e:
            print(f"Valkey subscription loop ended: {e}")
    
    async def close(self) -> None:
        self._is_active = False
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        await self.valkey.aclose()

