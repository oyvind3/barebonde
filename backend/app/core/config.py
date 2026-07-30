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
    
    # Better Auth
    better_auth_api_key: str
    better_auth_base_url: str = "https://api.better-auth.com/v1"
    
    # Email (Plunk) - Optional, configured in better-auth.com dashboard
    plunk_secret_api_key: str = ""  # Secret key for server-side (better-auth uses this)
    plunk_public_api_key: str = ""  # Public key for client-side (if needed)
    
    # JWT (still used for API tokens if needed, but better-auth handles sessions)
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    
    # API
    api_port: int = 8000
    api_host: str = "0.0.0.0"
    env: str = "development"
    frontend_url: str = "http://localhost:3000"  # Frontend base URL for redirects
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
