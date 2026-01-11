from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import json
from os import PathLike
from pathlib import Path
import shutil
from typing import BinaryIO

from botocore.exceptions import ClientError

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
    def get_file_url(self, key: str) -> str:
        pass

    @abstractmethod
    async def file_exists(self, key: str) -> bool:
        pass

class S3StorageAdapter(StorageAdapter):
    def __init__(self, s3_client, bucket_name: str | None = None, public_domain: str | None = None):
        self.s3 = s3_client
        self.bucket_name = bucket_name or config.s3_bucket_name
        self.region = config.aws_region
        self.public_domain = public_domain or config.s3_public_domain

    async def ensure_bucket_exists(self, make_public: bool = False) -> None:
        try:
            await self.s3.head_bucket(Bucket=self.bucket_name)
        except Exception:
            await self.s3.create_bucket(Bucket=self.bucket_name)
            if make_public:
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                        }
                    ]
                }
                try:
                    await self.s3.put_bucket_policy(
                        Bucket=self.bucket_name,
                        Policy=json.dumps(policy)
                    )
                except Exception as e:
                    print(f"Error setting bucket policy: {e}")
    
    async def upload_file(self, key: str, file_data: BinaryIO) -> StorageFile:
        try:
            file_content = file_data.read()
            file_size = len(file_content)

            await self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType="image/png"
            )
            
            return StorageFile(
                key=key,
                url=self.get_file_url(key),
                size=file_size,
                created_at=datetime.now()
            )
        except ClientError as e:
            print(f"Error uploading file to S3: {e}")
            raise ValueError(f"Failed to upload file: {e}")

    async def download_file(self, key: str) -> bytes:
        try:
            response = await self.s3.get_object(Bucket=self.bucket_name, Key=key)
            async with response["Body"] as stream:
                return await stream.read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {key}")
            print(f"Error downloading file from S3: {e}")
            raise ValueError(f"Failed to download file: {e}")

    async def delete_file(self, key: str) -> bool:
        try:
            await self.s3.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            print(f"Error deleting file from S3: {e}")
            return False
    
    def get_file_url(self, key: str) -> str:
        if self.public_domain:
            return f"{self.public_domain}/{self.bucket_name}/{key}"
        
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
    
    async def file_exists(self, key: str) -> bool:
        try:
            await self.s3.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

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
            url=self.get_file_url(key),
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
    
    def get_file_url(self, key: str) -> str:
        return f"/static/{key}"
    
    async def file_exists(self, key: str) -> bool:
        return self._get_file_path(key).exists()
    
def get_storage_adapter() -> StorageAdapter:
    from deps import manager

    if not manager.storage:
        raise RuntimeError("Storage adapter not initialized")
    return manager.storage
