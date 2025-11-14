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
