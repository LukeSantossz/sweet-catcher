"""create jobs table

Revision ID: 0003_create_jobs
Revises: 0002_create_search_criteria
Create Date: 2026-06-30 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_create_jobs"
down_revision: str | None = "0002_create_search_criteria"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_external_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("canonical_url", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("description_hash", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("work_mode", sa.String(), nullable=True),
        sa.Column("contract_type", sa.String(), nullable=True),
        sa.Column("posted_at", sa.Date(), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(), nullable=True),
        sa.Column("technologies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("languages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_external_id"),
    )
    op.create_index("ix_jobs_canonical_url", "jobs", ["canonical_url"])
    op.create_index("ix_jobs_description_hash", "jobs", ["description_hash"])


def downgrade() -> None:
    op.drop_index("ix_jobs_description_hash", table_name="jobs")
    op.drop_index("ix_jobs_canonical_url", table_name="jobs")
    op.drop_table("jobs")
