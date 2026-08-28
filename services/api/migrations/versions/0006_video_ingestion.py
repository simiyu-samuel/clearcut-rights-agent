"""Add first-class media ingestion fields to source documents.

Revision ID: 0006_video_ingestion
Revises: 0005_organization_invitations
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_video_ingestion"
down_revision = "0005_organization_invitations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("source_kind", sa.String(length=20), nullable=False, server_default="document"),
    )
    op.add_column(
        "documents",
        sa.Column(
            "media_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.create_index("ix_documents_source_kind", "documents", ["source_kind"])


def downgrade() -> None:
    op.drop_index("ix_documents_source_kind", table_name="documents")
    op.drop_column("documents", "media_metadata")
    op.drop_column("documents", "source_kind")
