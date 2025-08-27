from pathlib import Path
from typing import Optional

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from psycopg_pool import ConnectionPool

from app.core.config import settings


def build_checkpointer() -> Optional[object]:
    # 1) Prefer Postgres (shared across replicas)
    try:
        pool = ConnectionPool(conninfo=settings.langgraph_database_url, kwargs={"autocommit": True})
        cp = PostgresSaver(pool)
        if hasattr(cp, "setup"):
            cp.setup()
        return cp
    except Exception:
        pass

    # 2) Fallback to local SQLite (single-process persistence)
    try:
        sqlite_path = Path(".langgraph.sqlite").resolve()
        cp = SqliteSaver.from_conn_string(f"sqlite:///{sqlite_path}")
        if hasattr(cp, "setup"):
            cp.setup()
        return cp
    except Exception:
        return None