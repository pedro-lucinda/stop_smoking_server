import os
from pathlib import Path
from typing import Any, List

from dotenv import load_dotenv
from pydantic.v1 import BaseSettings, Field

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

    # PostgreSQL
    postgres_server: str = os.getenv("POSTGRES_SERVER", "db")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "password")
    postgres_db: str = os.getenv("POSTGRES_DB", "db")
    sqlalchemy_database_uri: str = ""  # built in __init__

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Auth0
    auth0_domain: str = os.getenv("AUTH0_DOMAIN", "")
    auth0_api_audience: str = os.getenv("AUTH0_API_AUDIENCE", "ss_api")
    auth0_client_id: str = os.getenv("AUTH0_CLIENT_ID")
    auth0_mgmt_client_id: str = os.getenv("AUTH0_MGMT_CLIENT_ID", "")
    auth0_mgmt_client_secret: str = os.getenv("AUTH0_MGMT_CLIENT_SECRET", "")
    auth0_mgmt_audience: str = os.getenv("AUTH0_MGMT_AUDIENCE", "")

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
