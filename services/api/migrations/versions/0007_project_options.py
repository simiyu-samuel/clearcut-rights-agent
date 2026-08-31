"""Add workspace-managed project metadata options.

Revision ID: 0007_project_options
Revises: 0006_video_ingestion
Create Date: 2026-08-31
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_project_options"
down_revision = "0006_video_ingestion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_options",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=120), nullable=False),
        sa.Column("option_type", sa.String(length=40), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("normalized_label", sa.String(length=120), nullable=False),
        sa.Column("created_by_actor_id", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "option_type",
            "normalized_label",
            name="uq_organization_options_label",
        ),
    )
    op.create_index(
        "ix_organization_options_organization_id",
        "organization_options",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_options_option_type",
        "organization_options",
        ["option_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_organization_options_option_type", table_name="organization_options")
    op.drop_index(
        "ix_organization_options_organization_id", table_name="organization_options"
    )
    op.drop_table("organization_options")
