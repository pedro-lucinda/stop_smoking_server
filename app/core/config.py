import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic.v1 import BaseSettings

# BASE_DIR is your project root (one level above app/)
BASE_DIR = Path(__file__).resolve().parent.parent

# load the env file from app/.env
load_dotenv()


class Settings(BaseSettings):
    """
    Attributes:
        app_name: Human-friendly project name.
        api_v1_str: URL prefix for the v1 API.
        secret_key: JWT signing secret.
        algorithm: JWT algorithm.
        access_token_expire_minutes: Token lifetime in minutes.
        server_host: Host for Uvicorn to bind to.
        server_port: Port for Uvicorn to listen on.
        postgres_server: Hostname for PostgreSQL.
        postgres_user: Username for PostgreSQL.
        postgres_password: Password for PostgreSQL.
        postgres_db: Database name for PostgreSQL.
        sqlalchemy_database_uri: Complete SQLAlchemy connection URL.
        redis_url: Redis connection URL.
        backends_cors_origins: List of allowed CORS origins.
    """

    app_name: str = "API"
    api_v1_str: str = "/api/v1"

    # JWT settings
    secret_key: str = os.getenv("JWT_SECRET", default="supersecretkey")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # PostgreSQL
    postgres_server: str = os.getenv("POSTGRES_SERVER", default="db")
    postgres_user: str = os.getenv("POSTGRES_USER", default="postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", default="password")
    postgres_db: str = os.getenv("POSTGRES_DB", default="db")
    sqlalchemy_database_uri: str = ""  # computed

    # Redis
    redis_url: str = os.getenv("REDIS_URL", default="redis://localhost:6379/0")

    # CORS
    backends_cors_origins = os.getenv(
        "BACKENDS_CORS_ORIGINS", default="http://localhost:3000,http://localhost:8000"
    )

    class Config:
        """Pydantic settings config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.sqlalchemy_database_uri:
            self.sqlalchemy_database_uri = (
                f"postgresql://"
                f"{self.postgres_user}:"
                f"{self.postgres_password}@"
                f"{self.postgres_server}:5432/"
                f"{self.postgres_db}"
            )


# Singleton
settings = Settings()
