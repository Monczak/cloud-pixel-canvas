from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional

from pymongo import AsyncMongoClient

from config import config

class DBAdapter(ABC):
    @abstractmethod
    async def get_canvas_state(self) -> Dict:
        pass

    @abstractmethod
    async def update_pixel(self, x: int, y: int, color: str, user_id: Optional[str] = None) -> Dict:
        pass

class MongoDBAdapter(DBAdapter):
    def __init__(self) -> None:
        self.client = AsyncMongoClient(config.mongo_uri)
        self.db = self.client[config.mongo_db]
        self.canvas_collection = self.db.canvas_state
    
    async def get_canvas_state(self) -> Dict:
        doc = await self.canvas_collection.find_one({"canvas_id": "main"})
        if doc:
            return doc.get("pixels", {})
        return {}
    
    async def update_pixel(self, x: int, y: int, color: str, user_id: Optional[str] = None) -> Dict:
        pixel_key = f"{x}_{y}"
        timestamp = int(datetime.now().timestamp())
        
        pixel_data = {
            "x": x,
            "y": y,
            "color": color,
            "timestamp": timestamp,
        }

        if user_id:
            pixel_data["userId"] = user_id
        
        await self.canvas_collection.update_one(
            {"canvas_id": "main"},
            {
                "$set": {
                    f"pixels.{pixel_key}": pixel_data,
                    "lastModified": timestamp
                }
            },
            upsert=True
        )

        return pixel_data
    
def get_db_adapter() -> DBAdapter:
    match config.environment:
        case "local":
            return MongoDBAdapter()
        
    raise ValueError(f"Unknown environment: {config.environment}")
