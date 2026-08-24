"""Add multi-angle research sessions and task tracking.

Revision ID: 0002_research_sessions
Revises: 0001_initial_schema
Create Date: 2026-08-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_research_sessions"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=120), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("total_tasks", sa.Integer(), nullable=False),
        sa.Column("completed_tasks", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_research_sessions_organization_id", "research_sessions", ["organization_id"]
    )
    op.create_index("ix_research_sessions_asset_id", "research_sessions", ["asset_id"])
    op.create_index("ix_research_sessions_status", "research_sessions", ["status"])

    op.create_table(
        "research_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=120), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("research_run_id", sa.String(length=36), nullable=False),
        sa.Column("angle", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("quality_tier", sa.String(length=40), nullable=False),
        sa.Column("gap_codes", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_tasks_organization_id", "research_tasks", ["organization_id"])
    op.create_index("ix_research_tasks_session_id", "research_tasks", ["session_id"])
    op.create_index("ix_research_tasks_research_run_id", "research_tasks", ["research_run_id"])
    op.create_index("ix_research_tasks_angle", "research_tasks", ["angle"])
    op.create_index("ix_research_tasks_status", "research_tasks", ["status"])

def downgrade() -> None:
    op.drop_table("research_tasks")
    op.drop_table("research_sessions")
