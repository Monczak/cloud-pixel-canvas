from datetime import datetime
from typing import List
from pydantic import BaseModel, Field

class PixelPlacement(BaseModel):
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")

class PixelData(BaseModel):
    x: int
    y: int
    color: str
    userId: str
    timestamp: int

class SnapshotResponse(BaseModel):
    snapshot_id: str
    image_url: str
    thumbnail_url: str
    canvas_width: int
    canvas_height: int
    created_at: datetime

class SnapshotListResponse(BaseModel):
    snapshots: List[SnapshotResponse]
    total: int
    limit: int
    offset: int
