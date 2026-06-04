"""
Application configuration using Pydantic Settings.

Loads environment variables from a .env file and provides
typed, validated configuration for the SourceSage backend.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the SourceSage application.

    Attributes:
        GOOGLE_API_KEY: API key for Google Gemini.
        TEMP_DIR: Directory for temporarily cloned repositories.
        MODEL_NAME: Gemini model to use for analysis.
        MAX_FILE_SIZE_KB: Maximum file size (in KB) to send to the LLM.
    """

    GOOGLE_API_KEY: str = ""
    TEMP_DIR: str = "./tmp_repos"
    MODEL_NAME: str = "gemini-2.5-flash"
    MAX_FILE_SIZE_KB: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def temp_path(self) -> Path:
        """Return TEMP_DIR as a resolved Path object."""
        return Path(self.TEMP_DIR).resolve()


# Singleton settings instance
settings = Settings()
