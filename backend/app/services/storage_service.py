"""Storage service for bilag file uploads to Azure Blob Storage."""

from datetime import datetime
from typing import Optional
import uuid

from azure.storage.blob import BlobServiceClient, ContentSettings

from app.core.config import settings


class StorageService:
    """Handles upload and delete operations for bilag files."""

    def __init__(self):
        self.connection_string = settings.azure_storage_connection_string
        self.container_name = settings.azure_storage_container_name

    def _get_container_client(self):
        if not self.connection_string:
            raise ValueError("Azure Storage er ikke konfigurert")

        blob_service = BlobServiceClient.from_connection_string(self.connection_string)
        container_client = blob_service.get_container_client(self.container_name)

        if not container_client.exists():
            container_client.create_container()

        return container_client

    def upload_file(
        self,
        farm_id: str,
        file_name: str,
        content_type: str,
        payload: bytes,
    ) -> dict:
        """Upload a file and return blob metadata."""
        container_client = self._get_container_client()

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        extension = ""
        if "." in file_name:
            extension = file_name[file_name.rfind("."):]

        blob_name = f"{farm_id}/{timestamp}-{uuid.uuid4().hex}{extension}"

        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(
            payload,
            overwrite=False,
            content_settings=ContentSettings(content_type=content_type),
        )

        return {
            "blob_name": blob_name,
            "blob_url": blob_client.url,
            "content_type": content_type,
            "size_bytes": len(payload),
        }

    def delete_file(self, blob_name: str) -> None:
        """Delete a file if present."""
        container_client = self._get_container_client()
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.delete_blob(delete_snapshots="include")


storage_service = StorageService()
