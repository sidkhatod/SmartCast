from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """Application settings"""

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "SmartCast"
    VERSION: str = "1.0.0"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str = "postgresql://smartcast:smartcast123@localhost:5432/smartcast"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:8501",
        "http://localhost:3000",
        "http://localhost:8080"
    ]

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    CDN_DIR: str = "./cdn" 
    STORAGE_DIR: str = "./storage"

    # FFmpeg
    FFMPEG_PATH: str = "/usr/bin/ffmpeg"
    FFPROBE_PATH: str = "/usr/bin/ffprobe"

    # RTMP
    RTMP_PORT: int = 1935
    RTMP_APP: str = "live"

    # CDN
    CDN_SERVERS: List[str] = ["cdn1", "cdn2", "cdn3"]
    CDN_BASE_URL: str = "http://localhost:8080"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
