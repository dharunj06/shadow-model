from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "ShadowML"
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/shadowml"
    DATABASE_URL_SYNC: str = "postgresql://postgres:password@localhost:5432/shadowml"

    # Model endpoints
    MODEL_V1_URL: str = "http://localhost:8001"
    MODEL_V2_URL: str = "http://localhost:8002"

    # MLflow
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"

    # Shadow evaluation
    PROMOTION_THRESHOLD: int = 100
    PROMOTION_ACCURACY_DELTA: float = 0.02

    # JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
