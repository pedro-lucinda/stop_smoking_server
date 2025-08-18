from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

from app.core.config import settings


def build_checkpointer() -> PostgresSaver:
    pool = ConnectionPool(
        conninfo=settings.langgraph_database_url, kwargs={"autocommit": True}
    )
    cp = PostgresSaver(pool)
    if hasattr(cp, "setup"):
        cp.setup()
    return cp
