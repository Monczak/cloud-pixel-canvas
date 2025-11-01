from fastapi import APIRouter, Depends, HTTPException

from adapters.db import DBAdapter, get_db_adapter
from models import PixelPlacement
from config import config

canvas_router = APIRouter(prefix="/canvas")

@canvas_router.get("/")
async def get_canvas(db: DBAdapter = Depends(get_db_adapter)):
    pixels = await db.get_canvas_state()
    return {
        "canvas_width": config.canvas_width,
        "canvas_height": config.canvas_height,
        "pixels": pixels,
    }

@canvas_router.post("/")
async def place_pixel(pixel: PixelPlacement, db: DBAdapter = Depends(get_db_adapter)):
    try:
        pixel.validate_bounds(config.canvas_width, config.canvas_height)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    pixel_data = await db.update_pixel(pixel.x, pixel.y, pixel.color)

    return pixel_data
