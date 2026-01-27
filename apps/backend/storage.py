import os
import shutil
import secrets
import json
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Protocol
import aioboto3
from botocore.client import Config

class IStorageProvider(ABC):
    @abstractmethod
    async def save_file(self, file_content: bytes, filename: string, subfolder: str = "bugs") -> str:
        pass

    @abstractmethod
    async def delete_file(self, file_path: str):
        pass

class DiskStorageProvider(IStorageProvider):
    def __init__(self, storage_path: str):
        self.storage_root = Path(storage_path)
        self.storage_root.mkdir(parents=True, exist_ok=True)
        # Ensure bugs subfolder exists
        (self.storage_root / "bugs").mkdir(parents=True, exist_ok=True)

    async def save_file(self, file_content: bytes, filename: str, subfolder: str = "bugs") -> str:
        safe_name = os.path.basename(filename).replace(" ", "_")
        timestamp = int(datetime.utcnow().timestamp())
        unique_name = f"{timestamp}_{secrets.token_hex(4)}_{safe_name}"
        
        target_dir = self.storage_root / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = target_dir / unique_name
        
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
            
        return f"/uploads/{subfolder}/{unique_name}"

    async def delete_file(self, file_path: str):
        # file_path is like /uploads/bugs/filename
        if file_path.startswith("/uploads/"):
            relative_path = file_path.replace("/uploads/", "")
            full_path = self.storage_root / relative_path
            if full_path.exists():
                full_path.unlink()

class BucketStorageProvider(IStorageProvider):
    def __init__(self):
        self.endpoint_url = os.getenv("BUCKET_ENDPOINT_URL")
        self.region_name = os.getenv("BUCKET_REGION", "auto")
        self.bucket_name = os.getenv("BUCKET_NAME")
        self.access_key = os.getenv("BUCKET_ACCESS_KEY_ID")
        self.secret_key = os.getenv("BUCKET_SECRET_ACCESS_KEY")
        
        if not all([self.endpoint_url, self.bucket_name, self.access_key, self.secret_key]):
            raise ValueError("Missing bucket configuration environment variables")

        self.session = aioboto3.Session()

    async def save_file(self, file_content: bytes, filename: str, subfolder: str = "bugs") -> str:
        safe_name = os.path.basename(filename).replace(" ", "_")
        timestamp = int(datetime.utcnow().timestamp())
        unique_name = f"{timestamp}_{secrets.token_hex(4)}_{safe_name}"
        object_key = f"{subfolder}/{unique_name}"

        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region_name,
            config=Config(signature_version="s3v4")
        ) as s3:
            await s3.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_content
            )
            
            # Construct the public URL
            # For Railway buckets, the URL structure is usually endpoint/bucket/key 
            # or a custom domain. We'll use the endpoint/bucket/key pattern or check if endpoint has the bucket.
            if self.endpoint_url.endswith("/"):
                url = f"{self.endpoint_url}{self.bucket_name}/{object_key}"
            else:
                url = f"{self.endpoint_url}/{self.bucket_name}/{object_key}"
            
            return url

    async def delete_file(self, file_path: str):
        # For bucket, file_path is the full URL or we need to extract the key
        # If it's the full URL, we extract the key (everything after bucket_name/)
        if self.bucket_name in file_path:
            key = file_path.split(f"{self.bucket_name}/")[-1]
            async with self.session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region_name
            ) as s3:
                await s3.delete_object(Bucket=self.bucket_name, Key=key)

def get_storage_provider() -> IStorageProvider:
    provider_type = os.getenv("STORAGE_PROVIDER", "disk").lower()
    if provider_type == "bucket":
        return BucketStorageProvider()
    else:
        # Default to disk
        storage_path = os.getenv("STORAGE_PATH", "/data/uploads")
        # In main.py, we had some fallback logic for UPLOAD_DIR. 
        # We'll use a simpler version here or let main.py pass it.
        return DiskStorageProvider(storage_path)
