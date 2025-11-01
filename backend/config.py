import os
from typing import List

class Config:
    def __init__(self) -> None:
        self.environment: str = os.getenv("ENVIRONMENT", "local")
        self.cors_origins: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

config = Config()
