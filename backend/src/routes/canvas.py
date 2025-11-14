from io import BytesIO
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from PIL import Image

from adapters.auth import User
from adapters.db import DBAdapter, get_db_adapter
from adapters.storage import StorageAdapter, get_storage_adapter
from config import config
from services.canvas import CanvasService, get_canvas_service
from utils.auth import get_current_user, verify_system_key
from models import PixelPlacement, SnapshotListResponse, SnapshotResponse

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

@canvas_router.post("/snapshot")
async def create_snapshot(
    system_key: str = Depends(verify_system_key),
    canvas: CanvasService = Depends(get_canvas_service),
):
    result = await canvas.create_snapshot()

    return SnapshotResponse(
        snapshot_id=result["snapshot_id"],
        image_url=result["image_url"],
        thumbnail_url=result["thumbnail_url"],
        canvas_width=config.canvas_width,
        canvas_height=config.canvas_height,
        created_at=result["created_at"]
    )

@canvas_router.get("/snapshot")
async def list_snapshots(
    limit: int = 20,
    offset: int = 0,
    db: DBAdapter = Depends(get_db_adapter),
    storage: StorageAdapter = Depends(get_storage_adapter)
):
    snapshots = await db.get_snapshots(limit, offset)
    total = await db.get_snapshot_count()

    snapshot_responses = []
    for snapshot in snapshots:
        image_url = await storage.get_file_url(snapshot["image_key"])
        thumbnail_url = await storage.get_file_url(snapshot["thumbnail_key"])

        snapshot_responses.append(SnapshotResponse(
            snapshot_id=snapshot["snapshot_id"],
            image_url=image_url,
            thumbnail_url=thumbnail_url,
            canvas_width=snapshot["canvas_width"],
            canvas_height=snapshot["canvas_height"],
            created_at=snapshot["created_at"]
        ))
    
    return SnapshotListResponse(
        snapshots=snapshot_responses,
        total=total,
        limit=limit,
        offset=offset
    )

@canvas_router.get("/snapshot/{snapshot_id}/download")
async def download_snapshot(snapshot_id: str, storage: StorageAdapter = Depends(get_storage_adapter), db: DBAdapter = Depends(get_db_adapter)):
    snapshot = await db.get_snapshot_by_id(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    image_url = await storage.get_file_url(snapshot["image_key"])
    return {"download_url": image_url}

@canvas_router.post("/snapshot/{snapshot_id}/restore")
async def restore_snapshot(
    snapshot_id: str,
    system_key: str = Depends(verify_system_key),
    canvas: CanvasService = Depends(get_canvas_service), 
    db: DBAdapter = Depends(get_db_adapter)
):
    snapshot = await db.get_snapshot_by_id(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    pixels = snapshot["pixels"]
    await canvas.bulk_overwrite(pixels)

    return Response(status_code=200)

@canvas_router.post("/overwrite")
async def overwrite_with_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    canvas: CanvasService = Depends(get_canvas_service)
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    contents = await file.read()
    img = Image.open(BytesIO(contents))

    if img.mode != "RGB":
        img = img.convert("RGB")

    img = img.resize((config.canvas_width, config.canvas_height), Image.Resampling.LANCZOS)
    pixels = {}

    for y in range(config.canvas_height):
        for x in range(config.canvas_width):
            r, g, b = img.getpixel((x, y)) # type: ignore
            color = f"#{r:02x}{g:02x}{b:02x}"
            pixel_key = f"{x}_{y}"

            pixels[pixel_key] = {
                "x": x,
                "y": y,
                "color": color,
            }

    result = await canvas.bulk_place_pixels(pixels, user.user_id)

    return {"pixels_updated": result["pixels_updated"]}
