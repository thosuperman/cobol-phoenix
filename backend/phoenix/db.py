"""Persistence (SQLAlchemy 2.x). SQLite by default; models are PostgreSQL compatible."""

from __future__ import annotations

import datetime as dt
import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import get_settings


def _id() -> str:
    return uuid.uuid4().hex[:16]


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    source_kind: Mapped[str] = mapped_column(String(32))  # sample | upload | zip | github | local
    source_ref: Mapped[str] = mapped_column(String(500), default="")
    license: Mapped[str] = mapped_column(String(200), default="")
    format_override: Mapped[str | None] = mapped_column(String(10), nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    line_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    analyzed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    fixtures_json: Mapped[str] = mapped_column(Text, default="{}")
    import_report_json: Mapped[str] = mapped_column(Text, default="{}")

    generations: Mapped[list[Generation]] = relationship(back_populates="project", cascade="all, delete-orphan")

    @property
    def analysis(self) -> dict | None:
        return json.loads(self.analysis_json) if self.analysis_json else None


class Generation(Base):
    __tablename__ = "generations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    entry: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    mutation_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mutation_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    summary_json: Mapped[str] = mapped_column(Text, default="{}")

    project: Mapped[Project] = relationship(back_populates="generations")
    runs: Mapped[list[VerificationRun]] = relationship(back_populates="generation", cascade="all, delete-orphan")


class VerificationRun(Base):
    __tablename__ = "verification_runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    generation_id: Mapped[str] = mapped_column(ForeignKey("generations.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued | running | completed | error
    progress: Mapped[str] = mapped_column(Text, default="")
    with_mutation: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    report_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    mutation_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    generation: Mapped[Generation] = relationship(back_populates="runs")


_engine = None
_Session = None


def engine():
    global _engine, _Session
    if _engine is None:
        url = get_settings().db_url
        kw = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {"pool_pre_ping": True}
        _engine = create_engine(url, **kw)
        if url.startswith("sqlite"):

            @event.listens_for(_engine, "connect")
            def _fk_on(dbapi_conn, _):  # pragma: no cover - sqlite pragma
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.execute("PRAGMA journal_mode=WAL")
                cur.close()

        _Session = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def init_db() -> None:
    """Create tables if needed. Production deployments run `alembic upgrade head`."""
    Base.metadata.create_all(engine())


@contextmanager
def session() -> Iterator:
    engine()
    s = _Session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def reset_for_tests() -> None:
    global _engine, _Session
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _Session = None
