from collections import defaultdict
from datetime import datetime
from io import BytesIO
from typing import Dict
import uuid

from fastapi import Depends
from PIL import Image

from adapters.db import DBAdapter, get_db_adapter
from adapters.storage import StorageAdapter, get_storage_adapter
from metrics import PIXELS_PLACED, SNAPSHOTS_TAKEN
from models import PixelData
from config import config
from wsmanager import manager as websocket


class CanvasService:
    def __init__(self, db: DBAdapter, storage: StorageAdapter):
        self.db = db
        self.storage = storage

    def _validate_bounds(self, x: int, y: int):
        if not 0 <= x < config.canvas_width or not 0 <= y < config.canvas_height:
            raise ValueError(f"Pixel coords out of bounds: ({x}, {y})")
        
    def _create_canvas_image(self, pixels: Dict[str, PixelData], width: int, height: int) -> Image.Image:
        img = Image.new("RGB", (width, height), color="#ffffff")
        for pixel in pixels.values():
            color_rgb = tuple(int(pixel.color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
            img.putpixel((pixel.x, pixel.y), color_rgb)
        return img

    def _create_thumbnail(self, img: Image.Image, max_size: int = 200) -> Image.Image:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        return img

    async def place_pixel(self, x: int, y: int, color: str, user_id: str) -> PixelData:
        self._validate_bounds(x, y)
        
        pixel = PixelData(
            x=x, 
            y=y, 
            color=color, 
            userId=user_id, 
            timestamp=int(datetime.now().timestamp())
        )
        
        result = await self.db.update_pixel(pixel)
        try:
            await websocket.broadcast({
                "intent": "pixel",
                "payload": result.model_dump()
            })
        except Exception as e:
            print(f"WebSocket broadcast failed: {e}")

        PIXELS_PLACED.labels(color=color).inc()
        
        return result
    
    async def bulk_place_pixels(self, pixels_map: Dict[str, Dict], user_id: str) -> Dict:
        timestamp = int(datetime.now().timestamp())
        
        pixel_objects = []
        for p_data in pixels_map.values():
            p_data["userId"] = user_id
            p_data["timestamp"] = timestamp

            p = PixelData(**p_data)
            pixel_objects.append(p)
            PIXELS_PLACED.labels(color=p.color).inc()

        await self.db.bulk_update_canvas(pixel_objects)

        try:
            broadcast_payload = {
                f"{p.x}_{p.y}": p.model_dump() for p in pixel_objects
            }
            await websocket.broadcast({
                "intent": "bulk_update",
                "payload": {
                    "pixels": broadcast_payload,
                    "user_id": user_id
                }
            })
        except Exception as e:
            print(f"WebSocket broadcast failed: {e}")
        
        return {
            "pixels_updated": len(pixel_objects),
            "timestamp": timestamp
        }

    async def bulk_overwrite(self, pixels_dict: Dict[str, Dict]) -> None:
        pixel_objects = [PixelData(**p) for p in pixels_dict.values()]
        
        await self.db.bulk_overwrite_canvas(pixel_objects)

        try:
            await websocket.broadcast({
                "intent": "bulk_overwrite",
                "payload": {
                    "pixels": pixels_dict,
                }
            })
        except Exception as e:
            print(f"WebSocket broadcast failed: {e}")

    async def get_canvas_state(self) -> Dict:
        pixels_data = await self.db.get_canvas_state()
        pixels_serializable = {k: v.model_dump() for k, v in pixels_data.items()}

        state = {
            "canvas_width": config.canvas_width,
            "canvas_height": config.canvas_height,
            "pixels": pixels_serializable,
        }
        return state
    
    async def create_snapshot(self) -> Dict:
        pixels_map = await self.db.get_canvas_state()

        snapshot_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        img = self._create_canvas_image(pixels_map, config.canvas_width, config.canvas_height)
        
        img_buffer = BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        image_key = f"snapshots/{snapshot_id}_{timestamp}.png"
        await self.storage.upload_file(image_key, img_buffer)

        thumb_buffer = BytesIO()
        self._create_thumbnail(img).save(thumb_buffer, format="PNG")
        thumb_buffer.seek(0)
        thumbnail_key = f"snapshots/{snapshot_id}_{timestamp}_thumb.png"
        await self.storage.upload_file(thumbnail_key, thumb_buffer)

        meta = await self.db.create_snapshot_metadata(snapshot_id, image_key, thumbnail_key)
        
        tiles_payload = []
        grouped = defaultdict(dict)
        for p in pixels_map.values():
            tx = p.x // config.tile_size
            ty = p.y // config.tile_size
            grouped[f"{tx}_{ty}"][f"{p.x}_{p.y}"] = p.model_dump()
            
        for tile_id, p_dict in grouped.items():
            tiles_payload.append({
                "canvas_id": f"main#{tile_id}",
                "pixels": p_dict
            })
            
        await self.db.create_snapshot_tiles(snapshot_id, tiles_payload)

        image_url = self.storage.get_file_url(image_key)
        thumbnail_url = self.storage.get_file_url(thumbnail_key)

        SNAPSHOTS_TAKEN.inc()

        return {
            "snapshot_id": snapshot_id,
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "created_at": meta["created_at"]
        }
    
def get_canvas_service(db: DBAdapter = Depends(get_db_adapter), storage: StorageAdapter = Depends(get_storage_adapter)) -> CanvasService:
    return CanvasService(db, storage)
