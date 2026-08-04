"""
Application configuration using Pydantic Settings
"""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    Cosmos DB configuration for serverless deployment
    """
    
    # Cosmos DB (Azure Cosmos DB connection string)
    cosmos_db_connection_string: str
    cosmos_db_database_id: str = "barebonde"

    # Azure Blob Storage for bilag files
    azure_storage_connection_string: str = ""
    azure_storage_container_name: str = "bilag"

    # OCR (Azure AI Document Intelligence)
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""
    ocr_default_language: str = "nb"

    # Email (Plunk) - Optional
    plunk_secret_api_key: str = ""
    plunk_public_api_key: str = ""
    
    # Retained for the current API surface; server-managed sessions are planned.
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    
    # API
    api_port: int = 8000
    api_host: str = "0.0.0.0"
    env: str = "development"
    frontend_url: str = "http://localhost:3000"  # Frontend base URL for redirects
    
    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://salmon-ocean-076260203.7.azurestaticapps.net",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
