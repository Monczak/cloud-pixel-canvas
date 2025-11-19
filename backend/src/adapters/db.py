from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

import aioboto3
from botocore.exceptions import ClientError
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

class DynamoDBAdapter(DBAdapter):
    def __init__(self):
        self.session = aioboto3.Session()
        self.canvas_table = config.dynamodb_canvas_table
        self.snapshots_table = config.dynamodb_snapshots_table

    async def get_canvas_state(self) -> Dict:
        async with self.session.resource("dynamodb", region_name=config.aws_region) as dynamodb:
            table = await dynamodb.Table(self.canvas_table)
            try:
                response = await table.get_item(Key={"canvas_id": "main"})
                if "Item" in response:
                    return response["Item"].get("pixels", {})
                return {}
            except ClientError as e:
                print(f"Error getting canvas state: {e}")
                return {}
    
    async def update_pixel(self, x: int, y: int, color: str, user_id: str | None = None) -> Dict:
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

        async with self.session.resource("dynamodb", region_name=config.aws_region) as dynamodb:
            table = await dynamodb.Table(self.canvas_table)
            try:
                await table.update_item(
                    Key={"canvas_id": "main"},
                    UpdateExpression="SET pixels.#pk = :pixel, lastModified = :ts",
                    ExpressionAttributeNames={"#pk": pixel_key},
                    ExpressionAttributeValues={
                        ":pixel": pixel_data,
                        ":ts": timestamp,
                    },
                )
            except ClientError as e:
                print(f"Error updating pixel: {e}")
                raise ValueError(f"Failed to update pixel: {e}")
        
        return pixel_data

    async def bulk_update_canvas(self, pixels: Dict) -> None:
        timestamp = int(datetime.now().timestamp())

        async with self.session.resource("dynamodb", region_name=config.aws_region) as dynamodb:
            table = await dynamodb.Table(self.canvas_table)
            try:
                update_parts = []
                attr_names = {}
                attr_values = {":ts": timestamp}

                for i, (pixel_key, pixel_data) in enumerate(pixels.items()):
                    name_key = f"#pk{i}"
                    value_key = f":pv{i}"
                    update_parts.append(f"pixels.{name_key} = {value_key}")
                    attr_names[name_key] = pixel_key
                    attr_values[value_key] = pixel_data

                update_expr = f"SET {",".join(update_parts)}, lastModified = :ts"

                await table.update_item(
                    Key={"canvas_id": "main"},
                    UpdateExpression=update_expr,
                    ExpressionAttributeNames=attr_names,
                    ExpressionAttributeValues=attr_values
                )
            except ClientError as e:
                print(f"Error bulk updating canvas: {e}")
                raise ValueError(f"Failed to bulk update canvas: {e}")
            
    async def bulk_overwrite_canvas(self, pixels: Dict) -> None:
        async with self.session.resource("dynamodb", region_name=config.aws_region) as dynamodb:
            table = await dynamodb.Table(self.canvas_table)
            try:
                await table.put_item(
                    Item={
                        "canvas_id": "main",
                        "pixels": pixels
                    }
                )
            except ClientError as e:
                print(f"Error overwriting canvas: {e}")
                raise ValueError(f"Failed to overwrite canvas: {e}")
            
    async def create_snapshot(self, snapshot_id: str, image_key: str, thumbnail_key: str) -> Dict:
        canvas_state = await self.get_canvas_state()

        snapshot_doc = {
            "snapshot_id": snapshot_id,
            "pixels": canvas_state,
            "image_key": image_key,
            "thumbnail_key": thumbnail_key,
            "canvas_width": config.canvas_width,
            "canvas_height": config.canvas_height,
            "created_at": datetime.now().isoformat(),
        }

        async with self.session.resource("dynamodb", region_name=config.aws_region) as dynamodb:
            table = await dynamodb.Table(self.snapshots_table)
            try:
                await table.put_item(Item=snapshot_doc)
            except ClientError as e:
                print(f"Error creating snapshot: {e}")
                raise ValueError(f"Failed to create snapshot: {e}")
            
        return {
            "snapshot_id": snapshot_id,
            "image_key": image_key,
            "thumbnail_key": thumbnail_key,
            "created_at": snapshot_doc["created_at"],
        }
    
    async def get_snapshots(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        async with self.session.resource("dynamodb", region_name=config.aws_region) as dynamodb:
            table = await dynamodb.Table(self.snapshots_table)
            try:
                response = await table.scan(
                    ProjectionExpression="snapshot_id, image_key, thumbnail_key, canvas_width, canvas_height, created_at"
                )
                items = response.get("Items", [])
                items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                paginated = items[offset:offset + limit]

                snapshots = []
                for item in paginated:
                    snapshots.append({
                        "snapshot_id": item["snapshot_id"],
                        "image_key": item["image_key"],
                        "thumbnail_key": item["thumbnail_key"],
                        "canvas_width": item.get("canvas_width", config.canvas_width),
                        "canvas_height": item.get("canvas_height", config.canvas_height),
                        "created_at": item["created_at"],
                    })
                
                return snapshots
            except ClientError as e:
                print(f"Error getting snapshots: {e}")
                return []
    
    async def get_snapshot_by_id(self, snapshot_id: str) -> Dict | None:
        async with self.session.resource("dynamodb", region_name=config.aws_region) as dynamodb:
            table = await dynamodb.Table(self.snapshots_table)
            try:
                response = await table.get_item(Key={"snapshot_id": snapshot_id})
                
                if "Item" not in response:
                    return None
                
                item = response["Item"]
                return {
                    "snapshot_id": item["snapshot_id"],
                    "pixels": item["pixels"],
                    "image_key": item["image_key"],
                    "thumbnail_key": item["thumbnail_key"],
                    "canvas_width": item.get("canvas_width", config.canvas_width),
                    "canvas_height": item.get("canvas_height", config.canvas_height),
                    "created_at": item["created_at"],
                }
            except ClientError as e:
                print(f"Error getting snapshot by id: {e}")
                return None
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        async with self.session.resource("dynamodb", region_name=config.aws_region) as dynamodb:
            table = await dynamodb.Table(self.snapshots_table)
            try:
                await table.delete_item(Key={"snapshot_id": snapshot_id})
                return True
            except ClientError as e:
                print(f"Error deleting snapshot: {e}")
                return False
            
    async def get_snapshot_count(self) -> int:
        async with self.session.resource("dynamodb", region_name=config.aws_region) as dynamodb:
            table = await dynamodb.Table(self.snapshots_table)
            try:
                response = await table.scan(Select="COUNT")
                return response.get("Count", 0)
            except ClientError as e:
                print(f"Error getting snapshot count: {e}")
                return 0

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
        case "aws":
            return DynamoDBAdapter()
        
    raise ValueError(f"Unknown environment: {config.environment}")
