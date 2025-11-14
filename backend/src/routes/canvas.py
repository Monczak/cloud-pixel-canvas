from fastapi import APIRouter, Depends, HTTPException

from adapters.auth import User
from services.canvas import CanvasService, get_canvas_service
from utils.auth import get_current_user
from models import PixelPlacement

canvas_router = APIRouter(prefix="/canvas")

@canvas_router.get("/")
async def get_canvas(canvas: CanvasService = Depends(get_canvas_service)):
    return await canvas.get_canvas_state()

@canvas_router.post("/")
async def place_pixel(pixel: PixelPlacement, user: User = Depends(get_current_user), canvas: CanvasService = Depends(get_canvas_service)):
    try:
        pixel_data = await canvas.place_pixel(pixel.x, pixel.y, pixel.color, user.user_id)
        return pixel_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
