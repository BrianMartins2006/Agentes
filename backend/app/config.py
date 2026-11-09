from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    ingest_api_key: SecretStr
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    ml_auto_train_enabled: bool = True
    ml_check_seconds: int = Field(default=300, ge=30)
    ml_retrain_seconds: int = Field(default=3600, ge=300)
    ml_min_new_samples: int = Field(default=120, ge=1)
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
    )


settings = Settings()
