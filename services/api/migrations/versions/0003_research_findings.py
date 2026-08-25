"""Add structured findings and angle-level source attribution.

Revision ID: 0003_research_findings
Revises: 0002_research_sessions
Create Date: 2026-08-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_research_findings"
down_revision = "0002_research_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "research_sessions",
        sa.Column("findings", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "research_tasks",
        sa.Column("findings", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "source_records",
        sa.Column("task_id", sa.String(length=36), nullable=True),
    )
    op.create_index("ix_source_records_task_id", "source_records", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_source_records_task_id", table_name="source_records")
    op.drop_column("source_records", "task_id")
    op.drop_column("research_tasks", "findings")
    op.drop_column("research_sessions", "findings")
