import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic.v1 import BaseSettings, Field
from typing import List, Any

# BASE_DIR is one level above app/
BASE_DIR = Path(__file__).resolve().parent.parent

# load the .env in your project root
load_dotenv()


class Settings(BaseSettings):
    """
    Application settings, loaded from environment or .env file.
    """

    app_name: str = "API"
    api_v1_str: str = "/api/v1"

    # JWT
    secret_key: str = os.getenv("JWT_SECRET", "supersecretkey")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # PostgreSQL
    postgres_server: str = os.getenv("POSTGRES_SERVER", "db")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "password")
    postgres_db: str = os.getenv("POSTGRES_DB", "db")
    sqlalchemy_database_uri: str = ""  # built in __init__

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # CORS: comma-separated list in your .env
    backends_cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="BACKENDS_CORS_ORIGINS",
    )

    # OpenAI
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")

    # Scheduler timezone
    timezone: str = Field("America/Sao_Paulo", env="TIMEZONE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        if not self.sqlalchemy_database_uri:
            self.sqlalchemy_database_uri = (
                f"postgresql://{self.postgres_user}:"
                f"{self.postgres_password}@{self.postgres_server}:5432/"
                f"{self.postgres_db}"
            )


# instantiate once
settings = Settings()
