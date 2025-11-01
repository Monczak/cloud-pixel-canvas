from pydantic import BaseModel, Field

class PixelPlacement(BaseModel):
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")

    def validate_bounds(self, width: int, height: int):
        if not 0 <= self.x < width or not 0 <= self.y < height:
            raise ValueError(f"Pixel coords out of bounds: ({self.x}, {self.y})")

class PixelData(BaseModel):
    x: int
    y: int
    color: str
    userId: str
    timestamp: int
