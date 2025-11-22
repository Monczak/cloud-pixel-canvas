import os
from typing import List

class Config:
    def __init__(self) -> None:
        self.environment: str = os.getenv("ENVIRONMENT", "local")
        self.cors_origins: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
        self.system_key: str = os.getenv("SYSTEM_KEY", "very-secret-key")

        self.tile_size: int = int(os.getenv("TILE_SIZE", 32))
        self.chunk_size: int = int(os.getenv("CHUNK_SIZE", 100))
        self.chunk_write_concurrency: int = int(os.getenv("CHUNK_WRITE_CONCURRENCY", 4))

        self.mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.mongo_db: str = os.getenv("MONGO_DB", "pixel_canvas")

        self.canvas_width: int = int(os.getenv("CANVAS_WIDTH", 100))
        self.canvas_height: int = int(os.getenv("CANVAS_HEIGHT", 100))

        self.max_snapshots: int = int(os.getenv("MAX_SNAPSHOTS", 50))

        self.local_storage_path: str = os.getenv("LOCAL_STORAGE_PATH", ".storage")

        # Valkey / ElastiCache
        self.valkey_host: str = os.getenv("VALKEY_HOST", "localhost")
        self.valkey_port: int = int(os.getenv("VALKEY_PORT", 6379))
        self.valkey_ssl: bool = os.getenv("VALKEY_SSL", "false").lower() == "true"
        self.valkey_password: str = os.getenv("VALKEY_PASSWORD", "")

        # AWS
        self.aws_region: str = os.getenv("AWS_REGION", "us-east-1")

        self.dynamodb_canvas_table: str = os.getenv("DYNAMODB_CANVAS_TABLE", "canvas")
        self.dynamodb_snapshots_table: str = os.getenv("DYNAMODB_SNAPSHOTS_TABLE", "snapshots")
        self.dynamodb_snapshot_tiles_table: str = os.getenv("DYNAMODB_SNAPSHOT_TILES_TABLE", "snapshot-tiles")

        self.cognito_user_pool_id: str = os.getenv("COGNITO_USER_POOL_ID", "")
        self.cognito_client_id: str = os.getenv("COGNITO_CLIENT_ID", "")
        self.cognito_client_secret: str = os.getenv("COGNITO_CLIENT_SECRET", "")

        self.s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "")

    def is_local(self) -> bool:
        return self.environment == "local"

config = Config()
