from abc import ABC, abstractmethod
import asyncio
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError
from pymongo import AsyncMongoClient

from models import PixelData
from config import config

class DBAdapter(ABC):
    @abstractmethod
    async def get_canvas_state(self) -> Dict:
        pass

    @abstractmethod
    async def update_pixel(self, pixel: PixelData) -> PixelData:
        pass

    @abstractmethod
    async def bulk_update_canvas(self, pixels: List[PixelData]) -> int:
        pass

    @abstractmethod
    async def bulk_overwrite_canvas(self, pixels: List[PixelData]) -> None:
        pass

    @abstractmethod
    async def create_snapshot_metadata(self, snapshot_id: str, image_key: str, thumbnail_key: str) -> Dict:
        pass

    @abstractmethod
    async def create_snapshot_tiles(self, snapshot_id: str, tiles_data: List[Dict]) -> None:
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
    def __init__(self, dynamo_resource):
        self.dynamodb = dynamo_resource
        
        self.canvas_table_name = config.dynamodb_canvas_table
        self.snapshots_table_name = config.dynamodb_snapshots_table
        self.snapshot_tiles_table_name = config.dynamodb_snapshot_tiles_table

        self.tile_size = config.tile_size
        self.chunk_size = config.chunk_size
        self.chunk_write_concurrency = config.chunk_write_concurrency

    async def _execute_atomic_update(self, key: Dict, update_expr: str, attr_names: Dict, attr_values: Dict):
        table = await self.dynamodb.Table(self.canvas_table_name)
        
        try:
            await table.update_item(
                Key=key,
                UpdateExpression=update_expr,
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_values,
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ValidationException":
                # Atomic initialization of the parent map 'pixels'
                try:
                    await table.update_item(
                        Key=key,
                        UpdateExpression="SET #pixels = :empty_map",
                        ConditionExpression="attribute_not_exists(#pixels)",
                        ExpressionAttributeNames={"#pixels": "pixels"},
                        ExpressionAttributeValues={":empty_map": {}},
                    )
                except ClientError as init_error:
                    if init_error.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                        raise init_error

                # Retry the original operation
                await table.update_item(
                    Key=key,
                    UpdateExpression=update_expr,
                    ExpressionAttributeNames=attr_names,
                    ExpressionAttributeValues=attr_values,
                )
            else:
                raise e

    async def get_canvas_state(self) -> Dict[str, PixelData]:
        pixels_map: Dict[str, PixelData] = {}
        try:
            table = await self.dynamodb.Table(self.canvas_table_name)
            response = await table.scan(
                FilterExpression=Attr("canvas_id").begins_with("main")
            )
            for item in response.get("Items", []):
                raw_pixels = item.get("pixels", {}) or {}
                for key, val in raw_pixels.items():
                    val_fixed = {
                        k: int(v) if isinstance(v, Decimal) else v 
                        for k, v in val.items()
                    }
                    pixels_map[key] = PixelData(**val_fixed) # type: ignore
            return pixels_map
        except ClientError as e:
            print(f"Error getting canvas state: {e}")
            return {}
    
    async def update_pixel(self, pixel: PixelData) -> PixelData:
        pixel_key = f"{pixel.x}_{pixel.y}"
        tx = pixel.x // self.tile_size
        ty = pixel.y // self.tile_size
        tile_canvas_id = f"main#{tx}_{ty}"

        await self._execute_atomic_update(
            key={"canvas_id": tile_canvas_id},
            update_expr="SET #pixels.#pk = :pixel, #lm = :ts",
            attr_names={
                "#pixels": "pixels",
                "#pk": pixel_key,
                "#lm": "lastModified",
            },
            attr_values={
                ":pixel": pixel.model_dump(),
                ":ts": pixel.timestamp,
            }
        )
        return pixel

    async def bulk_update_canvas(self, pixels: List[PixelData]) -> int:
        timestamp = int(datetime.now().timestamp())
        tiles = defaultdict(list)
        for p in pixels:
            tx = p.x // self.tile_size
            ty = p.y // self.tile_size
            tiles[f"{tx}_{ty}"].append(p)

        sem = asyncio.Semaphore(self.chunk_write_concurrency)

        async def _process_tile_chunk(tile_id: str, chunk: List[PixelData]):
            async with sem:
                key = {"canvas_id": f"main#{tile_id}"}
                update_parts = []
                attr_names = {"#pixels": "pixels", "#lm": "lastModified"}
                attr_values: Dict[str, Any] = {":ts": timestamp}

                for idx, p in enumerate(chunk):
                    p_key = f"{p.x}_{p.y}"
                    name_ph = f"#pk{idx}"
                    val_ph = f":pv{idx}"
                    update_parts.append(f"#pixels.{name_ph} = {val_ph}")
                    attr_names[name_ph] = p_key
                    attr_values[val_ph] = p.model_dump()

                update_expr = f"SET {', '.join(update_parts)}, #lm = :ts"

                await self._execute_atomic_update(
                    key=key,
                    update_expr=update_expr,
                    attr_names=attr_names,
                    attr_values=attr_values
                )

        tasks = []
        for tile_id, tile_pixels in tiles.items():
            for i in range(0, len(tile_pixels), self.chunk_size):
                chunk = tile_pixels[i : i + self.chunk_size]
                tasks.append(_process_tile_chunk(tile_id, chunk))

        if tasks:
            await asyncio.gather(*tasks)
        return len(pixels)

    async def bulk_overwrite_canvas(self, pixels: List[PixelData]) -> None:
        table = await self.dynamodb.Table(self.canvas_table_name)
        
        tiles = defaultdict(dict)
        for p in pixels:
            tx = p.x // self.tile_size
            ty = p.y // self.tile_size
            tiles[f"{tx}_{ty}"][f"{p.x}_{p.y}"] = p.model_dump()

        for tile_id, tile_data in tiles.items():
            await table.put_item(
                Item={
                    "canvas_id": f"main#{tile_id}",
                    "pixels": tile_data,
                    "lastModified": int(datetime.now().timestamp())
                }
            )

        try:
            resp = await table.scan(
                FilterExpression=Attr("canvas_id").begins_with("main#"),
                ProjectionExpression="canvas_id"
            )
            active_keys = {f"main#{tid}" for tid in tiles.keys()}
            delete_futures = []
            for item in resp.get("Items", []):
                cid = item.get("canvas_id")
                if cid and cid not in active_keys:
                    delete_futures.append(table.delete_item(Key={"canvas_id": cid}))
            if delete_futures:
                await asyncio.gather(*delete_futures)
        except Exception as e:
            print(f"Error cleaning up old tiles: {e}")

    async def create_snapshot_metadata(self, snapshot_id: str, image_key: str, thumbnail_key: str) -> Dict:
        table = await self.dynamodb.Table(self.snapshots_table_name)
        meta = {
            "snapshot_id": snapshot_id,
            "image_key": image_key,
            "thumbnail_key": thumbnail_key,
            "canvas_width": config.canvas_width,
            "canvas_height": config.canvas_height,
            "created_at": datetime.now().isoformat(),
        }
        await table.put_item(Item=meta)
        return meta

    async def create_snapshot_tiles(self, snapshot_id: str, tiles_data: List[Dict]) -> None:
        table = await self.dynamodb.Table(self.snapshot_tiles_table_name)
        sem = asyncio.Semaphore(10)
        
        async def _write(tile):
            async with sem:
                cid = tile.get("canvas_id", "")
                tile_id = cid.split("#", 1)[1] if "#" in cid else "0_0"
                await table.put_item(Item={
                    "snapshot_id": snapshot_id,
                    "tile_id": tile_id,
                    "pixels": tile.get("pixels", {})
                })

        await asyncio.gather(*[_write(t) for t in tiles_data])

    async def get_snapshots(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        try:
            table = await self.dynamodb.Table(self.snapshots_table_name)
            resp = await table.scan()
            items = resp.get("Items", [])
            items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return items[offset : offset + limit]
        except ClientError:
            return []

    async def get_snapshot_by_id(self, snapshot_id: str) -> Optional[Dict]:
        try:
            snapshots_table = await self.dynamodb.Table(self.snapshots_table_name)
            resp = await snapshots_table.get_item(Key={"snapshot_id": snapshot_id})
            if "Item" not in resp:
                return None
            
            meta = resp["Item"]
            
            tiles_table = await self.dynamodb.Table(self.snapshot_tiles_table_name)
            tiles_resp = await tiles_table.query(
                KeyConditionExpression=Key("snapshot_id").eq(snapshot_id)
            )
            
            pixels = {}
            for t in tiles_resp.get("Items", []):
                for p_key, p_val in t.get("pixels", {}).items():
                    val_fixed = {
                        k: int(v) if isinstance(v, Decimal) else v 
                        for k, v in p_val.items()
                    }
                    pixels[p_key] = val_fixed
            
            meta["pixels"] = pixels
            return meta
        except ClientError:
            return None

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        try:
            snapshots_table = await self.dynamodb.Table(self.snapshots_table_name)
            await snapshots_table.delete_item(Key={"snapshot_id": snapshot_id})
            
            tiles_table = await self.dynamodb.Table(self.snapshot_tiles_table_name)
            tiles = await tiles_table.query(
                KeyConditionExpression=Key("snapshot_id").eq(snapshot_id),
                ProjectionExpression="tile_id"
            )
            
            fs = []
            for t in tiles.get("Items", []):
                fs.append(tiles_table.delete_item(
                    Key={"snapshot_id": snapshot_id, "tile_id": t["tile_id"]}
                ))
            if fs:
                await asyncio.gather(*fs)
            return True
        except ClientError:
            return False

    async def get_snapshot_count(self) -> int:
        try:
            table = await self.dynamodb.Table(self.snapshots_table_name)
            resp = await table.scan(Select="COUNT")
            return resp.get("Count", 0)
        except ClientError:
            return 0

class MongoDBAdapter(DBAdapter):
    def __init__(self):
        self.client = AsyncMongoClient(config.mongo_uri)
        self.db = self.client[config.mongo_db]
        self.canvas_collection = self.db.canvas_state
        self.snapshots_collection = self.db.snapshots
        self.snapshot_tiles_collection = self.db.snapshot_tiles
        self.tile_size = config.tile_size

    async def get_canvas_state(self) -> Dict[str, PixelData]:
        pixels = {}
        async for doc in self.canvas_collection.find({"canvas_id": {"$regex": r"^main"}}):
            raw_pixels = doc.get("pixels", {})
            for k, v in raw_pixels.items():
                pixels[k] = PixelData(**v)
        return pixels

    async def update_pixel(self, pixel: PixelData) -> PixelData:
        pixel_key = f"{pixel.x}_{pixel.y}"
        tx = pixel.x // self.tile_size
        ty = pixel.y // self.tile_size
        
        await self.canvas_collection.update_one(
            {"canvas_id": f"main#{tx}_{ty}"},
            {
                "$set": {
                    f"pixels.{pixel_key}": pixel.model_dump(),
                    "lastModified": pixel.timestamp
                }
            },
            upsert=True
        )
        return pixel

    async def bulk_update_canvas(self, pixels: List[PixelData]) -> int:
        tiles = defaultdict(dict)
        for p in pixels:
            tx = p.x // self.tile_size
            ty = p.y // self.tile_size
            tiles[f"{tx}_{ty}"][f"{p.x}_{p.y}"] = p.model_dump()

        for tile_id, tile_pixels in tiles.items():
            await self.canvas_collection.update_one(
                {"canvas_id": f"main#{tile_id}"},
                {"$set": {f"pixels.{k}": v for k, v in tile_pixels.items()}},
                upsert=True
            )
        return len(pixels)

    async def bulk_overwrite_canvas(self, pixels: List[PixelData]) -> None:
        tiles = defaultdict(dict)
        ts = int(datetime.now().timestamp())
        for p in pixels:
            tx = p.x // self.tile_size
            ty = p.y // self.tile_size
            tiles[f"{tx}_{ty}"][f"{p.x}_{p.y}"] = p.model_dump()

        await self.canvas_collection.delete_many({"canvas_id": {"$regex": r"^main"}})
        
        docs = []
        for tile_id, tile_pixels in tiles.items():
            docs.append({
                "canvas_id": f"main#{tile_id}",
                "pixels": tile_pixels,
                "lastModified": ts
            })
        if docs:
            await self.canvas_collection.insert_many(docs)

    async def create_snapshot_metadata(self, snapshot_id: str, image_key: str, thumbnail_key: str) -> Dict:
        meta = {
            "snapshot_id": snapshot_id,
            "image_key": image_key,
            "thumbnail_key": thumbnail_key,
            "canvas_width": config.canvas_width,
            "canvas_height": config.canvas_height,
            "created_at": datetime.now(),
        }
        await self.snapshots_collection.insert_one(meta)
        return meta

    async def create_snapshot_tiles(self, snapshot_id: str, tiles_data: List[Dict]) -> None:
        docs = []
        for tile in tiles_data:
            cid = tile.get("canvas_id", "")
            tile_id = cid.split("#", 1)[1] if "#" in cid else "0_0"
            docs.append({
                "snapshot_id": snapshot_id,
                "tile_id": tile_id,
                "pixels": tile.get("pixels", {})
            })
        if docs:
            await self.snapshot_tiles_collection.insert_many(docs)

    async def get_snapshots(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        cursor = self.snapshots_collection.find({}, {"pixels": 0}).sort("created_at", -1).skip(offset).limit(limit)
        return [doc async for doc in cursor]

    async def get_snapshot_by_id(self, snapshot_id: str) -> Optional[Dict]:
        meta = await self.snapshots_collection.find_one({"snapshot_id": snapshot_id})
        if not meta:
            return None
        
        pixels = {}
        async for doc in self.snapshot_tiles_collection.find({"snapshot_id": snapshot_id}):
            pixels.update(doc.get("pixels", {}))
        
        meta["pixels"] = pixels
        return meta

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        res = await self.snapshots_collection.delete_one({"snapshot_id": snapshot_id})
        await self.snapshot_tiles_collection.delete_many({"snapshot_id": snapshot_id})
        return res.deleted_count > 0

    async def get_snapshot_count(self) -> int:
        return await self.snapshots_collection.count_documents({})
    
def get_db_adapter() -> DBAdapter:
    from deps import manager

    if not manager.db:
        raise RuntimeError("Database adapter not initialized")
    return manager.db
