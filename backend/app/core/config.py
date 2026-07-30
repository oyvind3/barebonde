"""
Application configuration using Pydantic Settings
"""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    # Database
    database_url: str
    
    # ID-porten OAuth2
    idporten_client_id: str
    idporten_client_secret: str
    idporten_discovery_url: str
    idporten_redirect_url: str
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # API
    api_port: int = 8000
    api_host: str = "0.0.0.0"
    env: str = "development"
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
