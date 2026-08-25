"""Add production workspace, collaboration, and delivery primitives.

Revision ID: 0004_production_workspace
Revises: 0003_research_findings
Create Date: 2026-08-25
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0004_production_workspace"
down_revision = "0003_research_findings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    op.create_table(
        "memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=120), nullable=False),
        sa.Column("actor_id", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"])
    op.create_index("ix_memberships_actor_id", "memberships", ["actor_id"])
    op.create_index("ix_memberships_role", "memberships", ["role"])
    op.create_index("ix_memberships_status", "memberships", ["status"])

    op.add_column("documents", sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("documents", sa.Column("parent_document_id", sa.String(length=36), nullable=True))
    op.create_index("ix_documents_parent_document_id", "documents", ["parent_document_id"])

    op.add_column("assets", sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"))
    op.add_column("assets", sa.Column("owner_id", sa.String(length=120), nullable=True))
    op.add_column("assets", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("assets", sa.Column("next_action", sa.String(length=160), nullable=True))
    op.create_index("ix_assets_priority", "assets", ["priority"])
    op.create_index("ix_assets_owner_id", "assets", ["owner_id"])
    op.create_index("ix_assets_due_at", "assets", ["due_at"])

    op.add_column("outreach_drafts", sa.Column("recipient_email", sa.String(length=320), nullable=True))
    op.add_column("outreach_drafts", sa.Column("response_note", sa.Text(), nullable=True))
    op.add_column("outreach_drafts", sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("outreach_drafts", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "outreach_drafts",
        sa.Column("terms", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_outreach_drafts_due_at", "outreach_drafts", ["due_at"])

    op.add_column("clearance_reports", sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("clearance_reports", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("clearance_reports", sa.Column("policy_version", sa.String(length=80), nullable=True))
    op.add_column("clearance_reports", sa.Column("source_snapshot_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "research_rechecks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=120), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("cadence_days", sa.Integer(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_session_id", sa.String(length=36), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_rechecks_organization_id", "research_rechecks", ["organization_id"])
    op.create_index("ix_research_rechecks_asset_id", "research_rechecks", ["asset_id"])
    op.create_index("ix_research_rechecks_next_run_at", "research_rechecks", ["next_run_at"])
    op.create_index("ix_research_rechecks_active", "research_rechecks", ["active"])

    op.create_table(
        "asset_comments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=120), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("author_id", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mention_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_comments_organization_id", "asset_comments", ["organization_id"])
    op.create_index("ix_asset_comments_asset_id", "asset_comments", ["asset_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=120), nullable=False),
        sa.Column("actor_id", sa.String(length=120), nullable=False),
        sa.Column("notification_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_organization_id", "notifications", ["organization_id"])
    op.create_index("ix_notifications_actor_id", "notifications", ["actor_id"])
    op.create_index("ix_notifications_notification_type", "notifications", ["notification_type"])

    op.create_table(
        "project_attachments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=120), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("attachment_type", sa.String(length=60), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index("ix_project_attachments_organization_id", "project_attachments", ["organization_id"])
    op.create_index("ix_project_attachments_project_id", "project_attachments", ["project_id"])
    op.create_index("ix_project_attachments_asset_id", "project_attachments", ["asset_id"])
    op.create_index("ix_project_attachments_sha256", "project_attachments", ["sha256"])

    op.create_table(
        "review_shares",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=120), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_review_shares_organization_id", "review_shares", ["organization_id"])
    op.create_index("ix_review_shares_project_id", "review_shares", ["project_id"])
    op.create_index("ix_review_shares_token_hash", "review_shares", ["token_hash"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("key_prefix", sa.String(length=20), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_api_keys_organization_id", "api_keys", ["organization_id"])
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])

    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=120), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False),
        sa.Column("event_types", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_endpoints_organization_id", "webhook_endpoints", ["organization_id"])
    op.create_index("ix_webhook_endpoints_active", "webhook_endpoints", ["active"])

    organizations = sa.table(
        "organizations",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    memberships = sa.table(
        "memberships",
        sa.column("id", sa.String),
        sa.column("organization_id", sa.String),
        sa.column("actor_id", sa.String),
        sa.column("display_name", sa.String),
        sa.column("role", sa.String),
        sa.column("status", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    now = datetime.now(UTC)
    op.bulk_insert(
        organizations,
        [{"id": "demo-org", "name": "Studio Meridian", "slug": "studio-meridian", "created_at": now, "updated_at": now}],
    )
    op.bulk_insert(
        memberships,
        [
            {"id": "demo-membership-admin", "organization_id": "demo-org", "actor_id": "demo-user", "display_name": "Studio Admin", "role": "admin", "status": "active", "created_at": now, "updated_at": now},
            {"id": "demo-membership-producer", "organization_id": "demo-org", "actor_id": "demo-producer", "display_name": "Demo Producer", "role": "producer", "status": "active", "created_at": now, "updated_at": now},
            {"id": "demo-membership-reviewer", "organization_id": "demo-org", "actor_id": "demo-reviewer", "display_name": "Legal Reviewer", "role": "legal_reviewer", "status": "active", "created_at": now, "updated_at": now},
        ],
    )


def downgrade() -> None:
    op.drop_table("webhook_endpoints")
    op.drop_table("api_keys")
    op.drop_table("review_shares")
    op.drop_table("project_attachments")
    op.drop_table("notifications")
    op.drop_table("asset_comments")
    op.drop_table("research_rechecks")
    op.drop_column("clearance_reports", "source_snapshot_at")
    op.drop_column("clearance_reports", "policy_version")
    op.drop_column("clearance_reports", "content_hash")
    op.drop_column("clearance_reports", "version_number")
    op.drop_index("ix_outreach_drafts_due_at", table_name="outreach_drafts")
    op.drop_column("outreach_drafts", "terms")
    op.drop_column("outreach_drafts", "due_at")
    op.drop_column("outreach_drafts", "responded_at")
    op.drop_column("outreach_drafts", "response_note")
    op.drop_column("outreach_drafts", "recipient_email")
    op.drop_index("ix_assets_due_at", table_name="assets")
    op.drop_index("ix_assets_owner_id", table_name="assets")
    op.drop_index("ix_assets_priority", table_name="assets")
    op.drop_column("assets", "next_action")
    op.drop_column("assets", "due_at")
    op.drop_column("assets", "owner_id")
    op.drop_column("assets", "priority")
    op.drop_index("ix_documents_parent_document_id", table_name="documents")
    op.drop_column("documents", "parent_document_id")
    op.drop_column("documents", "version_number")
    op.drop_table("memberships")
    op.drop_table("organizations")
