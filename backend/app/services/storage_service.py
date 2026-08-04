"""Storage service for bilag file uploads to Azure Blob Storage."""

from pathlib import PurePath
import re

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

        return container_client

    @staticmethod
    def _safe_blob_filename(file_name: str) -> str:
        """Keep original filenames out of Blob paths while retaining a safe extension."""
        basename = re.split(r"[\\\\/]", file_name or "")[-1]
        extension = PurePath(basename).suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,10}", extension or ""):
            extension = ""
        return f"document{extension}"

    def upload_file(
        self,
        farm_id: str,
        document_id: str,
        file_name: str,
        content_type: str,
        payload: bytes,
    ) -> dict:
        """Upload a file and return blob metadata."""
        container_client = self._get_container_client()

        blob_name = f"{farm_id}/{document_id}/{self._safe_blob_filename(file_name)}"

        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(
            payload,
            overwrite=False,
            content_settings=ContentSettings(content_type=content_type),
        )

        return {
            "blob_name": blob_name,
            "content_type": content_type,
            "size_bytes": len(payload),
        }

    def download_file(self, blob_name: str) -> bytes:
        """Read a private blob only after the API has authorized its metadata."""
        container_client = self._get_container_client()
        return container_client.get_blob_client(blob_name).download_blob().readall()

    def delete_file(self, blob_name: str) -> None:
        """Delete a file if present."""
        container_client = self._get_container_client()
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.delete_blob(delete_snapshots="include")


storage_service = StorageService()
