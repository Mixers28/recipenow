"""
Configuration for RecipeNow API.
Loads settings from environment variables.
"""
import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # API Configuration
    API_TITLE: str = "RecipeNow API"
    API_VERSION: str = "0.1.0"

    # CORS Configuration
    # Comma-separated list of allowed origins
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,"
        "http://localhost:5173,"
        "https://recipenow-seven.vercel.app"
    )

    # Logging Configuration
    LOG_LEVEL: str = "INFO"

    # Database Configuration (if needed)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    class Config:
        # Load from .env file if it exists
        env_file = ".env"
        case_sensitive = True

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse comma-separated origins into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


# Load settings (will use environment variables or .env file)
settings = Settings()
