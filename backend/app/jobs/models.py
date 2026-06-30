import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "source_external_id"),
        Index("ix_jobs_canonical_url", "canonical_url"),
        Index("ix_jobs_description_hash", "description_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String)
    source_external_id: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    company: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    canonical_url: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    description_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    work_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String, nullable=True)
    posted_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String, nullable=True)
    technologies: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    languages: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    status: Mapped[str] = mapped_column(String, default="open", server_default="open")
    raw: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
