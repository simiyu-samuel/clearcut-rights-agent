from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from clearcut_api.db import Database
from clearcut_api.main import as_utc, create_app
from clearcut_api.models import (
    Approval,
    Asset,
    AuditEvent,
    Base,
    ClearanceCard,
    Job,
    OrganizationInvitation,
    Project,
)
from clearcut_api.repositories import (
    ApprovalRepository,
    JobRepository,
    OrganizationInvitationRepository,
    ProjectRepository,
)


def make_database() -> Database:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return Database(
        engine=engine, session_factory=sessionmaker(bind=engine, expire_on_commit=False)
    )


def test_system_routes_are_registered() -> None:
    app = create_app(make_database())
    routes = {route.path for route in app.routes}
    assert {"/healthz", "/health", "/readyz", "/openapi.json"}.issubset(routes)
    assert {
        "/v1/auth/me",
        "/v1/organizations",
        "/v1/organizations/current/invitations",
        "/v1/organizations/current/invitations/{invitation_id}/revoke",
        "/v1/projects/{project_id}/approvals",
        "/v1/projects/{project_id}",
        "/v1/assets/{asset_id}/approvals",
        "/v1/projects/{project_id}/delivery-readiness",
        "/v1/projects/{project_id}/activity",
        "/v1/projects/{project_id}/media",
        "/v1/projects/{project_id}/media-uploads",
        "/v1/documents/{document_id}/complete-upload",
        "/v1/assets/{asset_id}/research-recheck",
        "/v1/assets/{asset_id}/comments",
        "/v1/projects/{project_id}/review-shares",
        "/v1/organizations/current/api-keys",
        "/v1/organizations/current/api-keys/{key_id}/revoke",
        "/v1/organizations/current/webhooks",
        "/v1/organizations/current/webhooks/{webhook_id}/toggle",
        "/v1/research-rechecks/run-due",
    }.issubset(routes)
    assert app.title == "ClearCut API"


def test_invitation_repository_matches_pending_email_only() -> None:
    database = make_database()
    with database.session_factory() as session:
        repository = OrganizationInvitationRepository(session)
        pending = repository.create(
            OrganizationInvitation(
                organization_id="studio-a",
                email="producer@example.com",
                role="producer",
                status="pending",
                invited_by_actor_id="admin",
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
        )
        repository.create(
            OrganizationInvitation(
                organization_id="studio-a",
                email="other@example.com",
                role="viewer",
                status="pending",
                invited_by_actor_id="admin",
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
        )

        matches = repository.list_pending_for_email("producer@example.com")
        assert [item.id for item in matches] == [pending.id]


def test_invitation_id_is_available_for_audit_event_before_flush() -> None:
    database = make_database()
    with database.session_factory() as session:
        invitation = OrganizationInvitation(
            id="invitation-for-audit",
            organization_id="studio-a",
            email="producer@example.com",
            role="producer",
            status="pending",
            invited_by_actor_id="admin",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        session.add(invitation)
        session.add(
            AuditEvent(
                organization_id="studio-a",
                actor_type="user",
                actor_id="admin",
                action="organization.invitation_created",
                resource_type="organization_invitation",
                resource_id=invitation.id,
            )
        )
        session.commit()

        audit_event = session.query(AuditEvent).one()
        assert audit_event.resource_id == "invitation-for-audit"


def test_as_utc_normalizes_sqlite_naive_datetimes() -> None:
    naive = datetime(2026, 8, 25, 12, 0, 0)
    aware = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)

    assert as_utc(naive) == aware
    assert as_utc(aware) == aware


def test_project_lifecycle_and_tenant_scope() -> None:
    database = make_database()
    with database.session_factory() as session:
        repository = ProjectRepository(session)
        created = repository.create(
            Project(
                organization_id="studio-a", title="The Last Signal", project_type="Feature film"
            )
        )

        assert repository.list("studio-a")[0].id == created.id
        assert repository.list("studio-b") == []
        assert repository.get(created.id, "studio-b") is None
        target_release = datetime(2026, 12, 1, tzinfo=UTC)
        updated = repository.update(created.id, "studio-a", target_release_at=target_release)
        assert updated is not None
        assert as_utc(updated.target_release_at) == target_release


def test_analysis_run_is_queued_for_async_processing() -> None:
    database = make_database()
    with database.session_factory() as session:
        project = ProjectRepository(session).create(
            Project(organization_id="demo-org", title="North Star", project_type="Series")
        )
        job = JobRepository(session).create(
            Job(
                organization_id="demo-org",
                project_id=project.id,
                job_type="document_analysis",
                status="queued",
            )
        )

        stored = JobRepository(session).get(job.id, "demo-org")
        assert stored is not None
        assert stored.project_id == project.id
        assert stored.status == "queued"


def test_approval_history_is_newest_first_and_tenant_scoped() -> None:
    database = make_database()
    with database.session_factory() as session:
        project = ProjectRepository(session).create(
            Project(organization_id="studio-a", title="North Star", project_type="Series")
        )
        other_project = ProjectRepository(session).create(
            Project(organization_id="studio-b", title="Other project", project_type="Feature film")
        )
        asset = Asset(
            organization_id="studio-a",
            project_id=project.id,
            document_id="document-a",
            canonical_name="Neon Afterglow",
            category="Music",
            context="Radio in scene 4",
            source_start=1,
            source_end=2,
            extraction_confidence=0.9,
        )
        other_org_asset = Asset(
            organization_id="studio-b",
            project_id=other_project.id,
            document_id="document-b",
            canonical_name="Other asset",
            category="Prop",
            context="Background detail",
            source_start=3,
            source_end=4,
            extraction_confidence=0.9,
        )
        session.add_all([asset, other_org_asset])
        session.flush()
        card = ClearanceCard(
            organization_id="studio-a",
            asset_id=asset.id,
            research_run_id="run-a",
            generated_by="vertex_gemini",
            risk_score=80,
            confidence_score=0.8,
            summary="Needs review",
            recommendation="Confirm rights",
        )
        session.add(card)
        session.flush()
        newest = Approval(
            organization_id="studio-a",
            asset_id=asset.id,
            clearance_card_id=card.id,
            decision="escalate_to_legal",
            actor_id="legal-reviewer",
            created_at=datetime.now(UTC),
        )
        older = Approval(
            organization_id="studio-a",
            asset_id=asset.id,
            clearance_card_id=card.id,
            decision="request_more_research",
            actor_id="producer",
            created_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        hidden = Approval(
            organization_id="studio-b",
            asset_id=other_org_asset.id,
            clearance_card_id="card-b",
            decision="approve_next_action",
            actor_id="other-reviewer",
        )
        session.add_all([newest, older, hidden])
        session.commit()

        repository = ApprovalRepository(session)
        assert [item.id for item in repository.list_for_asset(asset.id, "studio-a")] == [
            newest.id,
            older.id,
        ]
        assert [item.id for item in repository.list_for_project(project.id, "studio-a")] == [
            newest.id,
            older.id,
        ]
        assert repository.list_for_asset(asset.id, "studio-b") == []
