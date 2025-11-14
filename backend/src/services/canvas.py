from typing import Dict

from fastapi import Depends

from adapters.db import DBAdapter, get_db_adapter
from config import config
from wsmanager import manager as websocket


class CanvasService:
    def __init__(self, db: DBAdapter):
        self.db = db

    def _validate_bounds(self, x, y):
        if not 0 <= x < config.canvas_width or not 0 <= y < config.canvas_height:
            raise ValueError(f"Pixel coords out of bounds: ({x}, {y})")

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
    
    async def get_canvas_state(self) -> Dict:
        state = {
            "canvas_width": config.canvas_width,
            "canvas_height": config.canvas_height,
            "pixels": await self.db.get_canvas_state(),
        }
        return state
    
def get_canvas_service(db: DBAdapter = Depends(get_db_adapter)) -> CanvasService:
    return CanvasService(db)
