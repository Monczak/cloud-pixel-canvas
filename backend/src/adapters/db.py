from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from pymongo import AsyncMongoClient

from config import config

class DBAdapter(ABC):
    @abstractmethod
    async def get_canvas_state(self) -> Dict:
        pass

    @abstractmethod
    async def update_pixel(self, x: int, y: int, color: str, user_id: Optional[str] = None) -> Dict:
        pass

    @abstractmethod
    async def bulk_update_canvas(self, pixels: Dict) -> None:
        pass

    @abstractmethod
    async def bulk_overwrite_canvas(self, pixels: Dict) -> None:
        pass

    @abstractmethod
    async def create_snapshot(self, snapshot_id: str, image_key: str, thumbnail_key: str) -> Dict:
        pass

    @abstractmethod
    async def get_snapshots(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        pass

    @abstractmethod
    async def get_snapshot_by_id(self, snapshot_id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        pass

    @abstractmethod
    async def get_snapshot_count(self) -> int:
        pass

class MongoDBAdapter(DBAdapter):
    def __init__(self) -> None:
        self.client = AsyncMongoClient(config.mongo_uri)
        self.db = self.client[config.mongo_db]
        self.canvas_collection = self.db.canvas_state
        self.snapshots_collection = self.db.snapshots
    
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
    
    async def bulk_update_canvas(self, pixels: Dict) -> None:
        timestamp = int(datetime.now().timestamp())

        update_dict = {}
        for pixel_key, pixel_data in pixels.items():
            update_dict[f"pixels.{pixel_key}"] = pixel_data

        await self.canvas_collection.update_one(
            {"canvas_id": "main"},
            {
                "$set": {
                    **update_dict,
                    "lastModified": timestamp
                }
            },
            upsert=True
        )

    async def bulk_overwrite_canvas(self, pixels: Dict) -> None:
        await self.canvas_collection.update_one(
            {"canvas_id": "main"},
            {
                "$set": {
                    "pixels": pixels
                }
            },
            upsert=True
        )

    async def create_snapshot(self, snapshot_id: str, image_key: str, thumbnail_key: str) -> Dict:
        canvas_doc = await self.canvas_collection.find_one({"canvas_id": "main"})
        pixels = canvas_doc.get("pixels", {}) if canvas_doc else {}

        snapshot_doc = {
            "snapshot_id": snapshot_id,
            "pixels": pixels,
            "image_key": image_key,
            "thumbnail_key": thumbnail_key,
            "canvas_width": config.canvas_width,
            "canvas_height": config.canvas_height,
            "created_at": datetime.now(),
        }

        await self.snapshots_collection.insert_one(snapshot_doc)

        return {
            "snapshot_id": snapshot_id,
            "image_key": image_key,
            "thumbnail_key": thumbnail_key,
            "created_at": snapshot_doc["created_at"]
        }
    
    async def get_snapshots(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        cursor = self.snapshots_collection.find(
            {},
            {"pixels": 0} # Exclude pixel data from result
        ).sort("created_at", -1).skip(offset).limit(limit)

        snapshots = []
        async for doc in cursor:
            snapshots.append({
                "snapshot_id": doc["snapshot_id"],
                "image_key": doc["image_key"],
                "thumbnail_key": doc["thumbnail_key"],
                "canvas_width": doc.get("canvas_width", config.canvas_width),
                "canvas_height": doc.get("canvas_height", config.canvas_height),
                "created_at": doc["created_at"],
            })

        return snapshots
    
    async def get_snapshot_by_id(self, snapshot_id: str) -> Optional[Dict]:
        doc = await self.snapshots_collection.find_one({"snapshot_id": snapshot_id})
        
        if not doc:
            return None
        
        return {
            "snapshot_id": doc["snapshot_id"],
            "pixels": doc["pixels"],
            "image_key": doc["image_key"],
            "thumbnail_key": doc["thumbnail_key"],
            "canvas_width": doc.get("canvas_width", config.canvas_width),
            "canvas_height": doc.get("canvas_height", config.canvas_height),
            "created_at": doc["created_at"],
        }

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        result = await self.snapshots_collection.delete_one({"snapshot_id": snapshot_id})
        return result.deleted_count > 0

    async def get_snapshot_count(self) -> int:
        return await self.snapshots_collection.count_documents({})
    
def get_db_adapter() -> DBAdapter:
    match config.environment:
        case "local":
            return MongoDBAdapter()
        
    raise ValueError(f"Unknown environment: {config.environment}")
