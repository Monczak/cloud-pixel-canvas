import os
from typing import List

class Config:
    def __init__(self) -> None:
        self.environment: str = os.getenv("ENVIRONMENT", "local")
        self.cors_origins: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
        self.system_key: str = os.getenv("SYSTEM_KEY", "very-secret-key")

        self.mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.mongo_db: str = os.getenv("MONGO_DB", "pixel_canvas")

        self.canvas_width: int = int(os.getenv("CANVAS_WIDTH", 100))
        self.canvas_height: int = int(os.getenv("CANVAS_HEIGHT", 100))

        self.max_snapshots: int = int(os.getenv("MAX_SNAPSHOTS", 50))

        self.local_storage_path: str = os.getenv("LOCAL_STORAGE_PATH", ".storage")

    def is_local(self) -> bool:
        return self.environment == "local"

config = Config()
