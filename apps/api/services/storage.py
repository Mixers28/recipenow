"""
Storage abstraction layer for local disk and MinIO.
Supports uploading, retrieving, and deleting files.
"""
import hashlib
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional
from uuid import UUID


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def save(self, file_data: BinaryIO, file_path: str) -> str:
        """
        Save a file and return the storage path.
        Args:
            file_data: File-like object to save
            file_path: Desired path (e.g., 'assets/user1/recipe.jpg')
        Returns:
            Actual storage path
        """
        pass

    @abstractmethod
    def get(self, file_path: str) -> bytes:
        """
        Retrieve file contents by path.
        Args:
            file_path: Path to file
        Returns:
            File contents as bytes
        """
        pass

    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """Delete a file. Returns True if successful."""
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """Check if a file exists."""
        pass


class LocalDiskStorage(StorageBackend):
    """Store files on local disk."""

    def __init__(self, base_dir: str = "/data/assets"):
        """
        Initialize local disk storage.
        Args:
            base_dir: Base directory for storing files (default: /data/assets)
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file_data: BinaryIO, file_path: str) -> str:
        """Save file to local disk."""
        full_path = self.base_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(file_data.read())

        return str(full_path)

    def get(self, file_path: str) -> bytes:
        """Retrieve file from local disk."""
        full_path = self.base_dir / file_path
        with open(full_path, "rb") as f:
            return f.read()

    def delete(self, file_path: str) -> bool:
        """Delete file from local disk."""
        full_path = self.base_dir / file_path
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    def exists(self, file_path: str) -> bool:
        """Check if file exists on local disk."""
        full_path = self.base_dir / file_path
        return full_path.exists()


class MinIOStorage(StorageBackend):
    """Store files in MinIO (S3-compatible)."""

    def __init__(
        self,
        endpoint: str = "minio:9000",
        access_key: str = "minio",
        secret_key: str = "minio123",
        bucket: str = "recipes",
    ):
        """
        Initialize MinIO storage.
        Args:
            endpoint: MinIO endpoint (host:port)
            access_key: Access key
            secret_key: Secret key
            bucket: Bucket name
        """
        try:
            from minio import Minio
        except ImportError:
            raise ImportError("Install minio with: pip install minio")

        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key)
        self.bucket = bucket

        # Create bucket if not exists
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def save(self, file_data: BinaryIO, file_path: str) -> str:
        """Save file to MinIO."""
        file_data.seek(0)
        file_size = len(file_data.read())
        file_data.seek(0)

        self.client.put_object(
            self.bucket,
            file_path,
            file_data,
            length=file_size,
        )
        return f"s3://{self.bucket}/{file_path}"

    def get(self, file_path: str) -> bytes:
        """Retrieve file from MinIO."""
        response = self.client.get_object(self.bucket, file_path)
        data = response.read()
        response.close()
        return data

    def delete(self, file_path: str) -> bool:
        """Delete file from MinIO."""
        try:
            self.client.remove_object(self.bucket, file_path)
            return True
        except Exception:
            return False

    def exists(self, file_path: str) -> bool:
        """Check if file exists in MinIO."""
        try:
            self.client.stat_object(self.bucket, file_path)
            return True
        except Exception:
            return False


def get_storage_backend() -> StorageBackend:
    """
    Get configured storage backend based on environment.
    Defaults to local disk if STORAGE_BACKEND not set.
    """
    backend = os.getenv("STORAGE_BACKEND", "local").lower()

    if backend == "minio":
        return MinIOStorage(
            endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minio"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minio123"),
            bucket=os.getenv("MINIO_BUCKET", "recipes"),
        )
    else:
        return LocalDiskStorage(base_dir=os.getenv("STORAGE_DIR", "/data/assets"))


def compute_sha256(file_data: BinaryIO) -> str:
    """Compute SHA256 hash of file."""
    file_data.seek(0)
    sha256_hash = hashlib.sha256()
    for chunk in iter(lambda: file_data.read(4096), b""):
        sha256_hash.update(chunk)
    file_data.seek(0)
    return sha256_hash.hexdigest()
