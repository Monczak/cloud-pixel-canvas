from abc import ABC, abstractmethod
import asyncio
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from boto3.dynamodb.conditions import Attr, Key
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
    def __init__(self, dynamodb_client):
        self.dynamodb = dynamodb_client
        self.canvas_table = config.dynamodb_canvas_table
        self.snapshots_table = config.dynamodb_snapshots_table
        self.snapshot_tiles_table = config.dynamodb_snapshot_tiles_table

        self.tile_size = config.tile_size
        self.chunk_size = config.chunk_size
        self.chunk_write_concurrency = config.chunk_write_concurrency

    async def get_canvas_state(self) -> Dict:
        # Aggregate pixels across tile items (canvas_id startswith "main#")
        pixels: Dict = {}
        table = await self.dynamodb.Table(self.canvas_table)
        try:
            response = await table.scan(
                FilterExpression=Attr("canvas_id").begins_with("main")
            )
            items = response.get("Items", [])
            for item in items:
                item_pixels = item.get("pixels", {}) or {}
                pixels.update(item_pixels)
            return pixels
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

        # determine tile
        tx = x // self.tile_size
        ty = y // self.tile_size
        tile_canvas_id = f"main#{tx}_{ty}"

        table = await self.dynamodb.Table(self.canvas_table)
        try:
            # Try nested update to tile item
            await table.update_item(
                Key={"canvas_id": tile_canvas_id},
                UpdateExpression="SET #pixels.#pk = :pixel, #lm = :ts",
                ExpressionAttributeNames={
                    "#pixels": "pixels",
                    "#pk": pixel_key,
                    "#lm": "lastModified",
                },
                ExpressionAttributeValues={
                    ":pixel": pixel_data,
                    ":ts": timestamp,
                },
            )
        except ClientError as e:
            err_code = e.response.get("Error", {}).get("Code", "")
            err_msg = e.response.get("Error", {}).get("Message", "") or ""
            # If tile item or parent map missing, create it then retry
            if err_code == "ValidationException" and ("overlap" in err_msg.lower() or "invalid" in err_msg.lower()):
                try:
                    await table.update_item(
                        Key={"canvas_id": tile_canvas_id},
                        UpdateExpression="SET #pixels = :empty_map",
                        ConditionExpression="attribute_not_exists(#pixels)",
                        ExpressionAttributeNames={"#pixels": "pixels"},
                        ExpressionAttributeValues={":empty_map": {}},
                    )
                except ClientError:
                    # ignore conditional failure - someone else created it
                    pass

                try:
                    await table.update_item(
                        Key={"canvas_id": tile_canvas_id},
                        UpdateExpression="SET #pixels.#pk = :pixel, #lm = :ts",
                        ExpressionAttributeNames={
                            "#pixels": "pixels",
                            "#pk": pixel_key,
                            "#lm": "lastModified",
                        },
                        ExpressionAttributeValues={
                            ":pixel": pixel_data,
                            ":ts": timestamp,
                        },
                    )
                except ClientError as e2:
                    print(f"Error updating pixel after ensuring tile: {e2}")
                    raise ValueError(f"Failed to update pixel: {e2}")
            else:
                print(f"Error updating pixel: {e}")
                raise ValueError(f"Failed to update pixel: {e}")

        return pixel_data

    async def bulk_update_canvas(self, pixels: Dict) -> None:
        timestamp = int(datetime.now().timestamp())

        # group pixels by tile id
        tiles: Dict[str, Dict] = defaultdict(dict)
        for pixel_key, pixel_data in pixels.items():
            try:
                x_str, y_str = pixel_key.split("_", 1)
                x = int(x_str); y = int(y_str)
            except Exception:
                # fallback: put in tile 0_0
                x = 0; y = 0
            tx = x // self.tile_size
            ty = y // self.tile_size
            tile_id = f"{tx}_{ty}"
            tiles[tile_id][pixel_key] = pixel_data

        table = await self.dynamodb.Table(self.canvas_table)
        sem = asyncio.Semaphore(self.chunk_write_concurrency)

        async def _write_chunk_for_tile(tile_id: str, chunk_items: List[Tuple[str, Dict]]):
            async with sem:
                key = {"canvas_id": f"main#{tile_id}"}

                # ensure parent map exists
                try:
                    await table.update_item(
                        Key=key,
                        UpdateExpression="SET #pixels = :empty_map",
                        ConditionExpression="attribute_not_exists(#pixels)",
                        ExpressionAttributeNames={"#pixels": "pixels"},
                        ExpressionAttributeValues={":empty_map": {}},
                    )
                except ClientError:
                    pass

                attr_names = {"#pixels": "pixels", "#lm": "lastModified"}
                attr_values: Dict[str, Any] = {":ts": timestamp}
                parts = []

                for idx, (pkey, pdata) in enumerate(chunk_items):
                    name_key = f"#pk{idx}"
                    value_key = f":pv{idx}"
                    parts.append(f"#pixels.{name_key} = {value_key}")
                    attr_names[name_key] = pkey
                    attr_values[value_key] = pdata

                update_expr = f"SET {', '.join(parts)}, #lm = :ts"

                try:
                    await table.update_item(
                        Key=key,
                        UpdateExpression=update_expr,
                        ExpressionAttributeNames=attr_names,
                        ExpressionAttributeValues=attr_values,
                    )
                except ClientError as e:
                    print(f"Error bulk updating tile {tile_id} chunk: {e}")
                    raise ValueError(f"Failed to bulk update canvas tile {tile_id}: {e}")

        # build tasks per tile/chunk
        tasks = []
        for tile_id, tile_pixels in tiles.items():
            items = list(tile_pixels.items())
            for i in range(0, len(items), self.chunk_size):
                chunk = items[i:i + self.chunk_size]
                tasks.append(asyncio.create_task(_write_chunk_for_tile(tile_id, chunk)))

        if tasks:
            await asyncio.gather(*tasks)
        
    async def bulk_overwrite_canvas(self, pixels: Dict) -> None:
        tiles: Dict[str, Dict] = defaultdict(dict)
        for pixel_key, pixel_data in pixels.items():
            try:
                x_str, y_str = pixel_key.split("_", 1)
                x = int(x_str); y = int(y_str)
            except Exception:
                x = 0
                y = 0
            
            tx = x // self.tile_size
            ty = y // self.tile_size
            tile_id = f"{tx}_{ty}"
            tiles[tile_id][pixel_key] = pixel_data

        table = await self.dynamodb.Table(self.canvas_table)
        try:
            # write/replace each tile item
            for tile_id, tile_pixels in tiles.items():
                await table.put_item(
                    Item={
                        "canvas_id": f"main#{tile_id}",
                        "pixels": tile_pixels,
                        "lastModified": int(datetime.now().timestamp())
                    }
                )

            # scan existing tile items and delete tiles not in the new set
            resp = await table.scan(FilterExpression=Attr("canvas_id").begins_with("main#"))
            items = resp.get("Items", [])
            keep_ids = set(f"main#{tid}" for tid in tiles.keys())
            for it in items:
                cid = it.get("canvas_id")
                if cid not in keep_ids:
                    try:
                        await table.delete_item(Key={"canvas_id": cid})
                    except ClientError:
                        pass
        except ClientError as e:
            print(f"Error overwriting canvas: {e}")
            raise ValueError(f"Failed to overwrite canvas: {e}")
            
    async def create_snapshot(self, snapshot_id: str, image_key: str, thumbnail_key: str) -> Dict:
        canvas_table = await self.dynamodb.Table(self.canvas_table)
        snapshots_table = await self.dynamodb.Table(self.snapshots_table)
        tiles_table = await self.dynamodb.Table(self.snapshot_tiles_table)

        try:
            # Read current tiles from canvas (items whose canvas_id starts with "main#")
            resp = await canvas_table.scan(FilterExpression=Attr("canvas_id").begins_with("main#"))
            items = resp.get("Items", [])

            # Write snapshot metadata (small item)
            metadata = {
                "snapshot_id": snapshot_id,
                "image_key": image_key,
                "thumbnail_key": thumbnail_key,
                "canvas_width": config.canvas_width,
                "canvas_height": config.canvas_height,
                "created_at": datetime.now().isoformat(),
            }
            await snapshots_table.put_item(Item=metadata)

            # Write each tile as a separate item under the snapshot_tiles table
            # key: (snapshot_id, tile_id), attribute: pixels
            # chunking: do a small batch of put_item calls concurrently to avoid bursts
            sem = asyncio.Semaphore(8)
            async def _put_tile(tile_item):
                async with sem:
                    cid = tile_item.get("canvas_id", "")
                    if "#" in cid:
                        tile_id = cid.split("#", 1)[1]
                    else:
                        tile_id = "0_0"
                    tile_pixels = tile_item.get("pixels", {}) or {}
                    await tiles_table.put_item(Item={
                        "snapshot_id": snapshot_id,
                        "tile_id": tile_id,
                        "pixels": tile_pixels
                    })

            tasks = [asyncio.create_task(_put_tile(it)) for it in items]
            if tasks:
                await asyncio.gather(*tasks)

        except ClientError as e:
            print(f"Error creating snapshot: {e}")
            raise ValueError(f"Failed to create snapshot: {e}")

        return {
            "snapshot_id": snapshot_id,
            "image_key": image_key,
            "thumbnail_key": thumbnail_key,
            "created_at": metadata["created_at"],
        }
    
    async def get_snapshots(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        table = await self.dynamodb.Table(self.snapshots_table)
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
        snapshots_table = await self.dynamodb.Table(self.snapshots_table)
        tiles_table = await self.dynamodb.Table(self.snapshot_tiles_table)
        try:
            meta_resp = await snapshots_table.get_item(Key={"snapshot_id": snapshot_id})
            if "Item" not in meta_resp:
                return None
            meta = meta_resp["Item"]

            # query for tiles belonging to this snapshot
            tiles_resp = await tiles_table.query(KeyConditionExpression=Key("snapshot_id").eq(snapshot_id))
            tile_items = tiles_resp.get("Items", [])

            # normalize Decimal -> int for numeric fields so result is JSON serializable
            pixels: Dict = {}
            for t in tile_items:
                t_pixels = t.get("pixels", {}) or {}
                for pkey, pdata in t_pixels.items():
                    # copy to avoid mutating original
                    norm = dict(pdata)
                    # convert Decimal numbers to ints where applicable
                    for num_field in ("x", "y", "timestamp"):
                        if num_field in norm and isinstance(norm[num_field], Decimal):
                            norm[num_field] = int(norm[num_field])
                    # also convert any nested numeric fields if present
                    if "timestamp" in norm and isinstance(norm["timestamp"], Decimal):
                        norm["timestamp"] = int(norm["timestamp"])
                    pixels[pkey] = norm

            return {
                "snapshot_id": meta["snapshot_id"],
                "pixels": pixels,
                "image_key": meta["image_key"],
                "thumbnail_key": meta["thumbnail_key"],
                "canvas_width": meta.get("canvas_width", config.canvas_width),
                "canvas_height": meta.get("canvas_height", config.canvas_height),
                "created_at": meta["created_at"],
            }
        except ClientError as e:
            print(f"Error getting snapshot by id: {e}")
            return None
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        snapshots_table = await self.dynamodb.Table(self.snapshots_table)
        tiles_table = await self.dynamodb.Table(self.snapshot_tiles_table)
        try:
            # delete metadata
            await snapshots_table.delete_item(Key={"snapshot_id": snapshot_id})

            # delete per-tile items for this snapshot (query then delete)
            # Query for tile ids and delete each one (handles potentially many tiles)
            resp = await tiles_table.query(
                KeyConditionExpression=Key("snapshot_id").eq(snapshot_id),
                ProjectionExpression="tile_id"
            )
            items = resp.get("Items", []) or []
            for it in items:
                tid = it.get("tile_id")
                if not tid:
                    continue
                try:
                    await tiles_table.delete_item(Key={"snapshot_id": snapshot_id, "tile_id": tid})
                except ClientError:
                    # swallow individual delete errors and continue
                    pass

            return True
        except ClientError as e:
            print(f"Error deleting snapshot: {e}")
            return False
            
    async def get_snapshot_count(self) -> int:
        table = await self.dynamodb.Table(self.snapshots_table)
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
        self.snapshot_tiles_collection = self.db.snapshot_tiles

        self.tile_size = config.tile_size
        self.chunk_size = config.chunk_size
        self.chunk_write_concurrency = config.chunk_write_concurrency
    
    async def get_canvas_state(self) -> Dict:
        pixels: Dict = {}
        cursor = self.canvas_collection.find({"canvas_id": {"$regex": r"^main(#.*)?$"}})
        async for doc in cursor:
            item_pixels = doc.get("pixels", {}) or {}
            pixels.update(item_pixels)
        return pixels
    
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

        tx = x // self.tile_size
        ty = y // self.tile_size
        tile_id = f"{tx}_{ty}"
        await self.canvas_collection.update_one(
            {"canvas_id": f"main#{tile_id}"},
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
        tiles: Dict[str, Dict] = defaultdict(dict)

        for pixel_key, pixel_data in pixels.items():
            try:
                x_str, y_str = pixel_key.split("_", 1)
                x = int(x_str); y = int(y_str)
            except Exception:
                x = 0; y = 0
            tx = x // self.tile_size
            ty = y // self.tile_size
            tile_id = f"{tx}_{ty}"
            tiles[tile_id][pixel_key] = pixel_data

        # For each tile, chunk updates into $set map and upsert
        for tile_id, tile_pixels in tiles.items():
            items = list(tile_pixels.items())
            for i in range(0, len(items), self.chunk_size):
                chunk = items[i:i + self.chunk_size]
                update_dict = {}
                for pkey, pdata in chunk:
                    update_dict[f"pixels.{pkey}"] = pdata
                update_dict["lastModified"] = timestamp
                await self.canvas_collection.update_one(
                    {"canvas_id": f"main#{tile_id}"},
                    {"$set": update_dict},
                    upsert=True
                )

    async def bulk_overwrite_canvas(self, pixels: Dict) -> None:
        # group by tile and replace tile documents; remove legacy 'main' and stale tiles
        tiles: Dict[str, Dict] = defaultdict(dict)
        for pixel_key, pixel_data in pixels.items():
            try:
                x_str, y_str = pixel_key.split("_", 1)
                x = int(x_str); y = int(y_str)
            except Exception:
                x = 0; y = 0
            tx = x // self.tile_size
            ty = y // self.tile_size
            tile_id = f"{tx}_{ty}"
            tiles[tile_id][pixel_key] = pixel_data

        # delete all existing tile docs for this canvas
        await self.canvas_collection.delete_many({"canvas_id": {"$regex": r"^main(#.*)?$"}})

        # insert tile docs
        docs = []
        now_ts = int(datetime.now().timestamp())
        for tile_id, tile_pixels in tiles.items():
            docs.append({
                "canvas_id": f"main#{tile_id}",
                "pixels": tile_pixels,
                "lastModified": now_ts
            })
        if docs:
            await self.canvas_collection.insert_many(docs)

    async def create_snapshot(self, snapshot_id: str, image_key: str, thumbnail_key: str) -> Dict:
        # read tile docs from canvas collection (only items with canvas_id like "main#tx_ty")
        cursor = self.canvas_collection.find({"canvas_id": {"$regex": r"^main#"}})
        tiles = []
        async for doc in cursor:
            tiles.append(doc)

        metadata = {
            "snapshot_id": snapshot_id,
            "image_key": image_key,
            "thumbnail_key": thumbnail_key,
            "canvas_width": config.canvas_width,
            "canvas_height": config.canvas_height,
            "created_at": datetime.now(),
        }

        # insert small metadata doc
        await self.snapshots_collection.insert_one(metadata)

        # prepare per-tile snapshot docs
        docs = []
        for tile in tiles:
            cid = tile.get("canvas_id", "")
            tile_id = cid.split("#", 1)[1] if "#" in cid else "0_0"
            tile_pixels = tile.get("pixels", {}) or {}
            docs.append({
                "snapshot_id": snapshot_id,
                "tile_id": tile_id,
                "pixels": tile_pixels
            })

        # insert tile docs in chunks to avoid huge single operations
        for i in range(0, len(docs), self.chunk_size):
            chunk = docs[i:i + self.chunk_size]
            if chunk:
                # unordered insert to be resilient to duplicates/errors
                await self.snapshot_tiles_collection.insert_many(chunk, ordered=False)

        return {
            "snapshot_id": snapshot_id,
            "image_key": image_key,
            "thumbnail_key": thumbnail_key,
            "created_at": metadata["created_at"]
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
        # read metadata
        meta = await self.snapshots_collection.find_one({"snapshot_id": snapshot_id})
        if not meta:
            return None

        # aggregate per-tile pixels for this snapshot
        pixels: Dict = {}
        cursor = self.snapshot_tiles_collection.find({"snapshot_id": snapshot_id})
        async for tdoc in cursor:
            t_pixels = tdoc.get("pixels", {}) or {}
            pixels.update(t_pixels)

        return {
            "snapshot_id": meta["snapshot_id"],
            "pixels": pixels,
            "image_key": meta["image_key"],
            "thumbnail_key": meta["thumbnail_key"],
            "canvas_width": meta.get("canvas_width", config.canvas_width),
            "canvas_height": meta.get("canvas_height", config.canvas_height),
            "created_at": meta["created_at"],
        }

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        # remove metadata and any per-tile docs
        meta_res = await self.snapshots_collection.delete_one({"snapshot_id": snapshot_id})
        await self.snapshot_tiles_collection.delete_many({"snapshot_id": snapshot_id})
        return meta_res.deleted_count > 0

    async def get_snapshot_count(self) -> int:
        return await self.snapshots_collection.count_documents({})
    
def get_db_adapter() -> DBAdapter:
    from deps import manager

    if not manager.db:
        raise RuntimeError("Database adapter not initialized")
    return manager.db
