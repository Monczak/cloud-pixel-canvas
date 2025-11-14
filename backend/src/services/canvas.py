from datetime import datetime
from io import BytesIO
from typing import Dict
import uuid

from fastapi import Depends
from PIL import Image

from adapters.db import DBAdapter, get_db_adapter
from adapters.storage import StorageAdapter, get_storage_adapter
from config import config
from wsmanager import manager as websocket



class CanvasService:
    def __init__(self, db: DBAdapter, storage: StorageAdapter):
        self.db = db
        self.storage = storage

    def _validate_bounds(self, x, y):
        if not 0 <= x < config.canvas_width or not 0 <= y < config.canvas_height:
            raise ValueError(f"Pixel coords out of bounds: ({x}, {y})")
        
    def _create_canvas_image(self, pixels: Dict, width: int, height: int) -> Image.Image:
        img = Image.new("RGB", (width, height), color="#ffffff")

        for pixel in pixels.values():
            x = pixel["x"]
            y = pixel["y"]
            color = pixel["color"]

            color_rgb = tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
            img.putpixel((x, y), color_rgb)
        
        return img

    def _create_thumbnail(self, img: Image.Image, max_size: int = 200) -> Image.Image:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        return img

    async def place_pixel(self, x: int, y: int, color: str, user_id: str) -> Dict:
        self._validate_bounds(x, y)
        pixel_data = await self.db.update_pixel(x, y, color, user_id)

        try:
            await websocket.broadcast({
                "intent": "pixel",
                "payload": pixel_data
            })
        except Exception as e:
            print(f"WebSocket broadcast failed: {e}")
        
        return pixel_data
    
    async def bulk_place_pixels(self, pixels: Dict, user_id: str) -> Dict:
        timestamp = int(datetime.now().timestamp())
        for pixel_key, pixel_data in pixels.items():
            pixel_data["userId"] = user_id
            pixel_data["timestamp"] = timestamp

        await self.db.bulk_update_canvas(pixels)

        try:
            await websocket.broadcast({
                "intent": "bulk_update",
                "payload": {
                    "pixels": pixels,
                    "user_id": user_id
                }
            })
        except Exception as e:
            print(f"WebSocket broadcast failed: {e}")
        
        return {
            "pixels_updated": len(pixels),
            "timestamp": timestamp
        }

    async def bulk_overwrite(self, pixels: Dict) -> None:
        await self.db.bulk_overwrite_canvas(pixels)

        try:
            await websocket.broadcast({
                "intent": "bulk_overwrite",
                "payload": {
                    "pixels": pixels,
                }
            })
        except Exception as e:
            print(f"WebSocket broadcast failed: {e}")

    async def get_canvas_state(self) -> Dict:
        state = {
            "canvas_width": config.canvas_width,
            "canvas_height": config.canvas_height,
            "pixels": await self.db.get_canvas_state(),
        }
        return state
    
    async def create_snapshot(self) -> Dict:
        count = await self.db.get_snapshot_count()
        if count >= config.max_snapshots:
            snapshots = await self.db.get_snapshots(limit=count - config.max_snapshots + 1, offset=config.max_snapshots - 1)
            for snapshot in snapshots:
                try:
                    await self.storage.delete_file(snapshot["image_key"])
                    await self.storage.delete_file(snapshot["thumbnail_key"])
                    await self.db.delete_snapshot(snapshot["snapshot_id"])
                except Exception as e:
                    print(f"Failed to delete old snapshot: {e}")

        state = await self.get_canvas_state()
        pixels = state["pixels"]

        snapshot_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        img = self._create_canvas_image(pixels, config.canvas_width, config.canvas_height)
        img_buffer = BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        image_key = f"snapshots/{snapshot_id}_{timestamp}.png"
        await self.storage.upload_file(image_key, img_buffer)

        thumbnail = self._create_thumbnail(img.copy())
        thumb_buffer = BytesIO()
        thumbnail.save(thumb_buffer, format="PNG")
        thumb_buffer.seek(0)

        thumbnail_key = f"snapshots/{snapshot_id}_{timestamp}_thumb.png"
        await self.storage.upload_file(thumbnail_key, thumb_buffer)

        snapshot_doc = await self.db.create_snapshot(snapshot_id, image_key, thumbnail_key)

        image_url = await self.storage.get_file_url(image_key)
        thumbnail_url = await self.storage.get_file_url(thumbnail_key)

        return {
            "snapshot_id": snapshot_id,
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "created_at": snapshot_doc["created_at"]
        }
    
def get_canvas_service(db: DBAdapter = Depends(get_db_adapter), storage: StorageAdapter = Depends(get_storage_adapter)) -> CanvasService:
    return CanvasService(db, storage)
