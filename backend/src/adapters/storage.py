from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from os import PathLike
from pathlib import Path
import shutil
from typing import BinaryIO

from config import config

@dataclass
class StorageFile:
    key: str
    url: str
    size: int
    created_at: datetime

class StorageAdapter(ABC):
    @abstractmethod
    async def upload_file(self, key: str, file_data: BinaryIO) -> StorageFile:
        pass

    @abstractmethod
    async def download_file(self, key: str) -> bytes:
        pass

    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        pass

    @abstractmethod
    async def get_file_url(self, key: str) -> str:
        pass

    @abstractmethod
    async def file_exists(self, key: str) -> bool:
        pass

class LocalFileStorageAdapter(StorageAdapter):
    def __init__(self, base_path: PathLike | str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, key: str) -> Path:
        path = self.base_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    async def upload_file(self, key: str, file_data: BinaryIO) -> StorageFile:
        file_path = self._get_file_path(key)

        with open(file_path, "wb") as file:
            shutil.copyfileobj(file_data, file)
        
        stat = file_path.stat()

        return StorageFile(
            key=key,
            url=f"file://{file_path.absolute()}",
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime)
        )

    async def download_file(self, key: str) -> bytes:
        file_path = self._get_file_path(key)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        
        with open(file_path, "rb") as file:
            return file.read()

    async def delete_file(self, key: str) -> bool:
        file_path = self._get_file_path(key)

        if file_path.exists():
            file_path.unlink()
            return True
        
        return False
    
    async def get_file_url(self, key: str) -> str:
        file_path = self._get_file_path(key)
        return f"file://{file_path.absolute()}"
    
    async def file_exists(self, key: str) -> bool:
        return self._get_file_path(key).exists()
    
def get_storage_adapter() -> StorageAdapter:
    match config.environment:
        case "local":
            return LocalFileStorageAdapter(config.local_storage_path)
        
    raise ValueError(f"Unknown environment: {config.environment}")
    