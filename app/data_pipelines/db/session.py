"""SQLAlchemy engine helpers for the curation metadata DB."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.data_pipelines.db.models import Base


def get_database_url() -> str:
    return os.getenv(
        "VANGUARD_METADATA_DATABASE_URL",
        "sqlite+pysqlite:///:memory:",
    )


def create_db_engine(url: str | None = None) -> Engine:
    database_url = url or get_database_url()
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, connect_args=connect_args)


def init_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
