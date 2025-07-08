"""
Base class for all SQLAlchemy ORM models.

Import this Base in each models module so that
Alembic can auto-detect table metadata for migrations.
"""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
