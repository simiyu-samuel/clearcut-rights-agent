import difflib
import json
import logging
import re
import secrets
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import AuthenticatedIdentity, authenticate_request
from .config import settings
from .db import Database, create_database
from .models import (
    ApiKey,
    Approval,
    Asset,
    AssetComment,
    AuditEvent,
    ClearanceCard,
    ClearanceReport,
    Document,
    Job,
    Membership,
    Notification,
    Organization,
    OrganizationInvitation,
    OutreachDraft,
    Project,
    ProjectAttachment,
    ResearchRecheck,
    ResearchRun,
    ResearchSession,
    ResearchTask,
    ReviewShare,
    SourceRecord,
    WebhookEndpoint,
)
from .outreach import build_outreach_draft
from .pdf import build_pdf
from .playbooks import playbook_for
from .reporting import build_clearance_report
from .repositories import (
    ApiKeyRepository,
    ApprovalRepository,
    AssetCommentRepository,
    AssetRepository,
    AuditRepository,
    ClearanceCardRepository,
    ClearanceReportRepository,
    DocumentRepository,
    JobRepository,
    MembershipRepository,
    NotificationRepository,
    OrganizationInvitationRepository,
    OrganizationRepository,
    OutreachDraftRepository,
    ProjectAttachmentRepository,
    ProjectRepository,
    ResearchRecheckRepository,
    ResearchRunRepository,
    ResearchSessionRepository,
    ResearchTaskRepository,
    ReviewShareRepository,
    WebhookEndpointRepository,
)
from .schemas import (
    AnalysisRunCreate,
    ApiKeyCreate,
    ApiKeyRead,
    ApprovalCreate,
    ApprovalRead,
    AssetCommentCreate,
    AssetCommentRead,
    AssetRead,
    AssetUpdate,
    AuditEventRead,
    AuthIdentityRead,
    AuthMeRead,
    ClearanceCardRead,
    ClearanceReportRead,
    DeliveryReadinessRead,
    DocumentDiffRead,
    DocumentRead,
    JobRead,
    MediaUploadInit,
    MediaUploadSessionRead,
    MembershipRead,
    NotificationRead,
    OrganizationCreate,
    OrganizationInvitationCreate,
    OrganizationInvitationRead,
    OrganizationRead,
    OutreachDraftCreate,
    OutreachDraftRead,
    OutreachDraftUpdate,
    PlaybookRead,
    ProjectAttachmentRead,
    ProjectCreate,
    ProjectRead,
    ResearchFollowUpCreate,
    ResearchRecheckCreate,
    ResearchRecheckRead,
    ResearchRunCreate,
    ResearchRunRead,
    ResearchSessionCreate,
    ResearchSessionRead,
    ReviewShareCreate,
    ReviewShareRead,
    SourceRecordRead,
    WebhookEndpointCreate,
    WebhookEndpointRead,
    WorkspaceOverviewRead,
)
from .storage import ObjectStore, create_object_store
from .workflows import (
    build_research_plan,
    process_document_analysis,
    process_research_run,
    process_research_task,
)

ALLOWED_TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
ALLOWED_TEXT_MIME_TYPES = {"text/plain", "text/markdown", "application/octet-stream"}
ALLOWED_MEDIA_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".webm",
    ".mkv",
    ".mpeg",
    ".mpg",
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
}
ALLOWED_MEDIA_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
    "video/mpeg",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/webm",
    "audio/ogg",
}
MEDIA_MIME_BY_EXTENSION = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpeg",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
}
request_logger = logging.getLogger("clearcut.request")


def as_utc(value: datetime) -> datetime:
    """Normalize datetimes returned by SQLite and timezone-aware databases."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def create_app(
    database: Database | None = None, storage: ObjectStore | None = None
) -> FastAPI:
    db = database or create_database(settings.resolved_database_url())
    object_store = storage or create_object_store(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        db.init()
        yield

    app = FastAPI(
        title="ClearCut API",
        version="0.1.0",
        description="Evidence-backed rights-clearance workflow API.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip() for origin in settings.web_allowed_origins.split(",") if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.database = db
    app.state.object_store = object_store

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        correlation_id = request.headers.get("x-correlation-id") or str(uuid4())
        request.state.correlation_id = correlation_id
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            request_logger.exception(
                "request_failed method=%s path=%s correlation_id=%s",
                request.method,
                request.url.path,
                correlation_id,
            )
            raise
        response.headers["x-correlation-id"] = correlation_id
        request_logger.info(
            "request_complete method=%s path=%s status=%s duration_ms=%s correlation_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            round((time.perf_counter() - started_at) * 1000, 2),
            correlation_id,
        )
        return response

    def get_db():
        with db.session_factory() as session:
            yield session

    def get_auth_identity(
        request: Request,
        authorization: str | None = Header(default=None),
        x_actor_id: str | None = Header(default=None),
    ) -> AuthenticatedIdentity:
        return authenticate_request(request, authorization, x_actor_id, settings)

    def get_actor_id(identity: AuthenticatedIdentity = Depends(get_auth_identity)) -> str:
        return identity.actor_id

    def get_organization_id(
        x_organization_id: str | None = Header(default=None),
        identity: AuthenticatedIdentity = Depends(get_auth_identity),
        session: Session = Depends(get_db),
    ) -> str:
        if settings.auth_mode == "demo":
            return x_organization_id or settings.default_organization_id

        organization_id = x_organization_id
        if not organization_id:
            memberships = MembershipRepository(session).list_for_actor(identity.actor_id)
            if len(memberships) == 1:
                organization_id = memberships[0].organization_id
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_selection_required")
        if MembershipRepository(session).get(organization_id, identity.actor_id) is None:
            raise HTTPException(status_code=403, detail="organization_membership_required")
        return organization_id

    def require_role(
        session: Session, organization_id: str, actor_id: str, allowed_roles: set[str]
    ) -> Membership:
        membership = MembershipRepository(session).get(organization_id, actor_id)
        if membership is None and settings.auth_mode == "demo" and organization_id == settings.default_organization_id:
            fallback_roles = {
                "demo-user": "admin",
                "demo-producer": "producer",
                "demo-reviewer": "legal_reviewer",
            }
            fallback_role = fallback_roles.get(actor_id)
            if fallback_role in allowed_roles:
                return Membership(
                    organization_id=organization_id,
                    actor_id=actor_id,
                    display_name=actor_id,
                    role=fallback_role,
                    status="active",
                )
        if membership is None or membership.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="insufficient_workspace_role")
        return membership

    def require_project(session: Session, project_id: str, organization_id: str) -> Project:
        project = ProjectRepository(session).get(project_id, organization_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project_not_found")
        return project

    def research_session_payload(
        research_session: ResearchSession,
        tasks: list[ResearchTask],
        sources_by_task: dict[str, list[SourceRecord]] | None = None,
        provider_request_ids: dict[str, str | None] | None = None,
    ) -> dict[str, object]:
        sources_by_task = sources_by_task or {}
        provider_request_ids = provider_request_ids or {}
        return {
            "id": research_session.id,
            "organization_id": research_session.organization_id,
            "asset_id": research_session.asset_id,
            "provider": research_session.provider,
            "objective": research_session.objective,
            "status": research_session.status,
            "total_tasks": research_session.total_tasks,
            "completed_tasks": research_session.completed_tasks,
            "findings": research_session.findings or [],
            "created_at": research_session.created_at,
            "updated_at": research_session.updated_at,
            "tasks": [
                {
                    "id": task.id,
                    "organization_id": task.organization_id,
                    "session_id": task.session_id,
                    "research_run_id": task.research_run_id,
                    "angle": task.angle,
                    "title": task.title,
                    "objective": task.objective,
                    "query": task.query,
                    "status": task.status,
                    "provider_request_id": provider_request_ids.get(task.id),
                    "source_count": task.source_count,
                    "quality_tier": task.quality_tier,
                    "gap_codes": task.gap_codes or [],
                    "findings": task.findings or [],
                    "sources": sources_by_task.get(task.id, []),
                    "error_code": task.error_code,
                    "created_at": task.created_at,
                    "updated_at": task.updated_at,
                }
                for task in tasks
            ],
        }

    def create_research_session_records(
        session: Session,
        asset: Asset,
        organization_id: str,
        objective: str | None,
    ) -> tuple[ResearchSession, list[ResearchTask]]:
        plan_objective, plans = build_research_plan(asset, objective)
        run = ResearchRun(
            organization_id=organization_id,
            asset_id=asset.id,
            provider="parallel",
            operation="multi_angle_search",
            objective=plan_objective,
            query=f"{asset.canonical_name} {asset.category} rights clearance research session",
        )
        run = ResearchRunRepository(session).create(run)
        research_session = ResearchSession(
            organization_id=organization_id,
            asset_id=asset.id,
            provider="parallel",
            objective=plan_objective,
            status="planned",
            total_tasks=len(plans),
            completed_tasks=0,
        )
        research_session = ResearchSessionRepository(session).create(research_session)
        tasks = ResearchTaskRepository(session).create_many(
            [
                ResearchTask(
                    organization_id=organization_id,
                    session_id=research_session.id,
                    research_run_id=run.id,
                    angle=plan.angle,
                    title=plan.title,
                    objective=plan.objective,
                    query=plan.query,
                    status="queued",
                    source_count=0,
                    quality_tier="unrated",
                    gap_codes=[],
                )
                for plan in plans
            ]
        )
        return research_session, tasks

    def sources_by_task(
        session: Session, tasks: list[ResearchTask]
    ) -> dict[str, list[SourceRecord]]:
        repository = ResearchRunRepository(session)
        return {task.id: repository.list_sources_for_task(task.id) for task in tasks}

    def provider_request_ids(
        session: Session, tasks: list[ResearchTask]
    ) -> dict[str, str | None]:
        repository = ResearchRunRepository(session)
        request_ids: dict[str, str | None] = {}
        for task in tasks:
            run = repository.get(task.research_run_id, task.organization_id)
            request_ids[task.id] = run.provider_request_id if run else None
        return request_ids

    def create_follow_up_records(
        session: Session,
        task: ResearchTask,
        asset: Asset,
        organization_id: str,
        objective: str | None,
    ) -> tuple[ResearchSession, list[ResearchTask]]:
        gap_text = ", ".join(task.gap_codes) or "independent confirmation"
        follow_up_objective = objective or (
            f'Run a focused follow-up for "{asset.canonical_name}" focused on the '
            f"{task.title.lower()} angle. Resolve these findings: {gap_text}. Return an "
            "authoritative source, rights contact, or a clearly documented reason evidence "
            "cannot be confirmed."
        )
        run = ResearchRun(
            organization_id=organization_id,
            asset_id=asset.id,
            provider="parallel",
            operation="focused_follow_up",
            objective=follow_up_objective,
            query=f"{task.query} independent authoritative rights source direct contact {gap_text}",
        )
        run = ResearchRunRepository(session).create(run)
        research_session = ResearchSession(
            organization_id=organization_id,
            asset_id=asset.id,
            provider="parallel",
            objective=follow_up_objective,
            status="planned",
            total_tasks=1,
            completed_tasks=0,
            findings=[],
        )
        research_session = ResearchSessionRepository(session).create(research_session)
        follow_up_task = ResearchTask(
            organization_id=organization_id,
            session_id=research_session.id,
            research_run_id=run.id,
            angle=f"{task.angle}_follow_up",
            title=f"Follow-up · {task.title}",
            objective=follow_up_objective,
            query=run.query,
            status="queued",
            source_count=0,
            quality_tier="unrated",
            gap_codes=[],
            findings=[],
        )
        return research_session, ResearchTaskRepository(session).create_many([follow_up_task])

    @app.get("/healthz", tags=["system"])
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "clearcut-api", "version": "0.1.0"}

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "clearcut-api", "version": "0.1.0"}

    @app.get("/readyz", tags=["system"])
    def readyz(session: Session = Depends(get_db)) -> dict[str, str]:
        try:
            session.connection()
        except Exception as exc:  # pragma: no cover - defensive operational boundary
            raise HTTPException(status_code=503, detail="database_not_ready") from exc
        return {"status": "ready"}

    @app.get("/v1/auth/me", response_model=AuthMeRead, tags=["auth"])
    def get_auth_me(
        identity: AuthenticatedIdentity = Depends(get_auth_identity),
        session: Session = Depends(get_db),
    ) -> dict[str, object]:
        if settings.auth_mode != "demo" and identity.email:
            normalized_email = identity.email.strip().lower()
            now = datetime.now(UTC)
            invitation_repository = OrganizationInvitationRepository(session)
            pending_invitations = invitation_repository.list_pending_for_email(normalized_email)
            changed = False
            for invitation in pending_invitations:
                if as_utc(invitation.expires_at) <= now:
                    invitation.status = "expired"
                    invitation.updated_at = now
                    changed = True
                    continue
                existing = MembershipRepository(session).get(
                    invitation.organization_id, identity.actor_id
                )
                if existing is None:
                    session.add(
                        Membership(
                            organization_id=invitation.organization_id,
                            actor_id=identity.actor_id,
                            display_name=invitation.display_name or identity.display_name,
                            role=invitation.role,
                            status="active",
                        )
                    )
                invitation.status = "accepted"
                invitation.accepted_by_actor_id = identity.actor_id
                invitation.accepted_at = now
                invitation.updated_at = now
                session.add(
                    AuditEvent(
                        organization_id=invitation.organization_id,
                        actor_type="user",
                        actor_id=identity.actor_id,
                        action="organization.invitation_accepted",
                        resource_type="organization_invitation",
                        resource_id=invitation.id,
                        metadata_json=json.dumps({"email": normalized_email}),
                    )
                )
                changed = True
            if changed:
                session.commit()
        memberships = MembershipRepository(session).list_for_actor(identity.actor_id)
        if settings.auth_mode == "demo" and not memberships:
            now = datetime.now(UTC)
            memberships = [
                Membership(
                    id=f"demo-membership-{identity.actor_id}",
                    organization_id=settings.default_organization_id,
                    actor_id=identity.actor_id,
                    display_name=identity.display_name,
                    role="admin",
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            ]
        organizations = {
            membership.organization_id: OrganizationRepository(session).get(membership.organization_id)
            for membership in memberships
        }
        membership_reads = [
            {
                "id": membership.id,
                "organization_id": membership.organization_id,
                "organization_name": (
                    organizations[membership.organization_id].name
                    if organizations.get(membership.organization_id) is not None
                    else (
                        "Studio Meridian"
                        if membership.organization_id == settings.default_organization_id
                        else membership.organization_id
                    )
                ),
                "actor_id": membership.actor_id,
                "display_name": membership.display_name,
                "role": membership.role,
                "status": membership.status,
                "created_at": membership.created_at,
                "updated_at": membership.updated_at,
            }
            for membership in memberships
        ]
        return {
            "identity": AuthIdentityRead(
                actor_id=identity.actor_id,
                email=identity.email,
                display_name=identity.display_name,
            ),
            "memberships": membership_reads,
        }

    @app.post(
        "/v1/organizations",
        response_model=OrganizationRead,
        status_code=status.HTTP_201_CREATED,
        tags=["organization"],
    )
    def create_organization(
        payload: OrganizationCreate,
        identity: AuthenticatedIdentity = Depends(get_auth_identity),
        session: Session = Depends(get_db),
    ) -> Organization:
        organization_id = str(uuid4())
        base_slug = payload.slug or re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")
        slug = f"{base_slug or 'workspace'}-{organization_id[:8]}"
        organization = Organization(id=organization_id, name=payload.name, slug=slug)
        session.add(organization)
        session.add(
            Membership(
                organization_id=organization_id,
                actor_id=identity.actor_id,
                display_name=identity.display_name,
                role="admin",
                status="active",
            )
        )
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=identity.actor_id,
                action="organization.created",
                resource_type="organization",
                resource_id=organization_id,
                metadata_json=json.dumps({"name": organization.name}),
            )
        )
        session.commit()
        session.refresh(organization)
        return organization

    @app.post(
        "/v1/projects",
        response_model=ProjectRead,
        status_code=status.HTTP_201_CREATED,
        tags=["projects"],
    )
    def create_project(
        payload: ProjectCreate,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Project:
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin", "producer", "coordinator"})
        project = Project(organization_id=organization_id, **payload.model_dump())
        created = ProjectRepository(session).create(project)
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="project.created",
                resource_type="project",
                resource_id=created.id,
                metadata_json=json.dumps({"title": created.title}),
            )
        )
        session.commit()
        session.refresh(created)
        return created

    @app.get("/v1/projects", response_model=list[ProjectRead], tags=["projects"])
    def list_projects(
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[Project]:
        return ProjectRepository(session).list(organization_id)

    @app.get(
        "/v1/organizations/current",
        response_model=OrganizationRead,
        tags=["organization"],
    )
    def get_current_organization(
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Organization:
        organization = OrganizationRepository(session).get(organization_id)
        if organization is not None:
            return organization
        if settings.auth_mode != "demo":
            raise HTTPException(status_code=404, detail="organization_not_found")
        now = datetime.now(UTC)
        return Organization(
            id=organization_id,
            name="Studio Meridian" if organization_id == "demo-org" else organization_id,
            slug=organization_id,
            created_at=now,
            updated_at=now,
        )

    @app.get(
        "/v1/organizations/current/members",
        response_model=list[MembershipRead],
        tags=["organization"],
    )
    def list_members(
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[Membership]:
        members = MembershipRepository(session).list_for_organization(organization_id)
        if members or settings.auth_mode != "demo":
            return members
        now = datetime.now(UTC)
        return [
            Membership(
                id=f"demo-membership-{actor_id}",
                organization_id=organization_id,
                actor_id=actor_id,
                display_name=display_name,
                role=role,
                status="active",
                created_at=now,
                updated_at=now,
            )
            for actor_id, display_name, role in (
                ("demo-user", "Studio Admin", "admin"),
                ("demo-producer", "Demo Producer", "producer"),
                ("demo-reviewer", "Legal Reviewer", "legal_reviewer"),
            )
        ]

    @app.get(
        "/v1/organizations/current/invitations",
        response_model=list[OrganizationInvitationRead],
        tags=["organization"],
    )
    def list_invitations(
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[OrganizationInvitation]:
        require_role(session, organization_id, x_actor_id or "demo-user", {"admin"})
        now = datetime.now(UTC)
        invitations = OrganizationInvitationRepository(session).list_for_organization(organization_id)
        changed = False
        for invitation in invitations:
            if invitation.status == "pending" and as_utc(invitation.expires_at) <= now:
                invitation.status = "expired"
                invitation.updated_at = now
                changed = True
        if changed:
            session.commit()
        return invitations

    @app.post(
        "/v1/organizations/current/invitations",
        response_model=OrganizationInvitationRead,
        status_code=status.HTTP_201_CREATED,
        tags=["organization"],
    )
    def create_invitation(
        payload: OrganizationInvitationCreate,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> OrganizationInvitation:
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin"})
        email = payload.email.strip().lower()
        if "@" not in email:
            raise HTTPException(status_code=422, detail="valid_email_required")
        repository = OrganizationInvitationRepository(session)
        existing = repository.pending_for_email(organization_id, email)
        if existing is not None and as_utc(existing.expires_at) > datetime.now(UTC):
            raise HTTPException(status_code=409, detail="invitation_already_pending")
        invitation = OrganizationInvitation(
            id=str(uuid4()),
            organization_id=organization_id,
            email=email,
            display_name=payload.display_name.strip() if payload.display_name else None,
            role=payload.role,
            status="pending",
            invited_by_actor_id=actor_id,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        session.add(invitation)
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="organization.invitation_created",
                resource_type="organization_invitation",
                resource_id=invitation.id,
                metadata_json=json.dumps({"email": email, "role": payload.role}),
            )
        )
        session.commit()
        session.refresh(invitation)
        return invitation

    @app.post(
        "/v1/organizations/current/invitations/{invitation_id}/revoke",
        response_model=OrganizationInvitationRead,
        tags=["organization"],
    )
    def revoke_invitation(
        invitation_id: str,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> OrganizationInvitation:
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin"})
        invitation = OrganizationInvitationRepository(session).get(invitation_id, organization_id)
        if invitation is None:
            raise HTTPException(status_code=404, detail="invitation_not_found")
        if invitation.status != "pending":
            raise HTTPException(status_code=409, detail="invitation_not_pending")
        invitation.status = "revoked"
        invitation.updated_at = datetime.now(UTC)
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="organization.invitation_revoked",
                resource_type="organization_invitation",
                resource_id=invitation.id,
            )
        )
        session.commit()
        session.refresh(invitation)
        return invitation

    @app.get(
        "/v1/workspace/overview",
        response_model=WorkspaceOverviewRead,
        tags=["workspace"],
    )
    def workspace_overview(
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, int]:
        from datetime import UTC, datetime, timedelta

        period_days = 30
        period_start = datetime.now(UTC) - timedelta(days=period_days)
        project_count = int(
            session.scalar(
                select(func.count(Project.id)).where(Project.organization_id == organization_id)
            )
            or 0
        )
        total_assets = int(
            session.scalar(
                select(func.count(Asset.id)).where(
                    Asset.organization_id == organization_id,
                    Asset.created_at >= period_start,
                )
            )
            or 0
        )
        assets_reviewed = int(
            session.scalar(
                select(func.count(func.distinct(ClearanceCard.asset_id)))
                .join(Asset, Asset.id == ClearanceCard.asset_id)
                .where(
                    ClearanceCard.organization_id == organization_id,
                    ClearanceCard.created_at >= period_start,
                )
            )
            or 0
        )
        attention_statuses = ("high_risk", "needs_review", "blocked", "insufficient_evidence")
        assets_need_attention = int(
            session.scalar(
                select(func.count(Asset.id)).where(
                    Asset.organization_id == organization_id,
                    Asset.updated_at >= period_start,
                    Asset.risk_status.in_(attention_statuses),
                )
            )
            or 0
        )
        high_priority_items = int(
            session.scalar(
                select(func.count(Asset.id)).where(
                    Asset.organization_id == organization_id,
                    Asset.updated_at >= period_start,
                    Asset.risk_status.in_(("high_risk", "blocked")),
                )
            )
            or 0
        )
        evidence_assets = int(
            session.scalar(
                select(func.count(func.distinct(ClearanceCard.asset_id)))
                .join(Asset, Asset.id == ClearanceCard.asset_id)
                .where(
                    ClearanceCard.organization_id == organization_id,
                    ClearanceCard.created_at >= period_start,
                    ClearanceCard.evidence_count > 0,
                )
            )
            or 0
        )
        research_runs = int(
            session.scalar(
                select(func.count(ResearchRun.id)).where(
                    ResearchRun.organization_id == organization_id,
                    ResearchRun.created_at >= period_start,
                )
            )
            or 0
        )
        parallel_sources = int(
            session.scalar(
                select(func.count(SourceRecord.id))
                .join(ResearchRun, ResearchRun.id == SourceRecord.research_run_id)
                .where(
                    ResearchRun.organization_id == organization_id,
                    SourceRecord.retrieved_at >= period_start,
                )
            )
            or 0
        )
        evidence_coverage = round((evidence_assets / total_assets) * 100) if total_assets else 0
        return {
            "period_days": period_days,
            "project_count": project_count,
            "assets_reviewed": assets_reviewed,
            "assets_need_attention": assets_need_attention,
            "high_priority_items": high_priority_items,
            "evidence_coverage": evidence_coverage,
            "research_runs": research_runs,
            "parallel_sources": parallel_sources,
        }

    @app.get("/v1/projects/{project_id}", response_model=ProjectRead, tags=["projects"])
    def get_project(
        project_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Project:
        return require_project(session, project_id, organization_id)

    @app.post(
        "/v1/projects/{project_id}/documents",
        response_model=DocumentRead,
        status_code=status.HTTP_201_CREATED,
        tags=["documents"],
    )
    async def upload_document(
        project_id: str,
        file: UploadFile = File(...),
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Document:
        require_project(session, project_id, organization_id)
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin", "producer", "coordinator"})
        filename = Path(file.filename or "upload.txt").name
        extension = Path(filename).suffix.lower()
        content_type = (file.content_type or "application/octet-stream").lower()
        if extension not in ALLOWED_TEXT_EXTENSIONS or content_type not in ALLOWED_TEXT_MIME_TYPES:
            raise HTTPException(
                status_code=415, detail="only_utf8_text_and_markdown_documents_are_supported"
            )
        content = await file.read(settings.max_upload_bytes + 1)
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="document_too_large")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=415, detail="document_must_be_utf8") from exc

        document_id = str(uuid4())
        object_key = f"{organization_id}/{project_id}/{document_id}.source"
        object_store.save_bytes(object_key, content)
        previous = DocumentRepository(session).latest_for_project(project_id, organization_id)
        document = Document(
            id=document_id,
            organization_id=organization_id,
            project_id=project_id,
            original_filename=filename,
            mime_type=content_type,
            size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
            object_key=object_key,
            extracted_text=content.decode("utf-8"),
            version_number=(previous.version_number + 1) if previous else 1,
            parent_document_id=previous.id if previous else None,
        )
        created = DocumentRepository(session).create(document)
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="document.uploaded",
                resource_type="project",
                resource_id=project_id,
                metadata_json=json.dumps(
                    {"document_id": created.id, "version_number": created.version_number}
                ),
            )
        )
        session.commit()
        session.refresh(created)
        return created

    @app.post(
        "/v1/projects/{project_id}/media",
        response_model=DocumentRead,
        status_code=status.HTTP_201_CREATED,
        tags=["media"],
    )
    async def upload_media(
        project_id: str,
        file: UploadFile = File(...),
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Document:
        """Bounded multipart fallback for local development and small media samples."""
        require_project(session, project_id, organization_id)
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin", "producer", "coordinator"})
        filename = Path(file.filename or "upload.mp4").name
        extension = Path(filename).suffix.lower()
        content_type = (file.content_type or "application/octet-stream").lower()
        if content_type == "application/octet-stream":
            content_type = MEDIA_MIME_BY_EXTENSION.get(extension, content_type)
        if extension not in ALLOWED_MEDIA_EXTENSIONS or (
            content_type not in ALLOWED_MEDIA_MIME_TYPES
            and content_type != "application/octet-stream"
        ):
            raise HTTPException(status_code=415, detail="unsupported_media_type")
        content = await file.read(settings.max_media_upload_bytes + 1)
        if len(content) > settings.max_media_upload_bytes:
            raise HTTPException(status_code=413, detail="media_multipart_upload_too_large")
        media_kind = "video" if content_type.startswith("video/") or extension in {
            ".mp4",
            ".mov",
            ".webm",
            ".mkv",
            ".mpeg",
            ".mpg",
        } else "audio"
        document_id = str(uuid4())
        object_key = f"{organization_id}/{project_id}/{document_id}.media"
        object_store.save_bytes(object_key, content)
        previous = DocumentRepository(session).latest_for_project(project_id, organization_id)
        document = Document(
            id=document_id,
            organization_id=organization_id,
            project_id=project_id,
            original_filename=filename,
            mime_type=content_type,
            size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
            object_key=object_key,
            extracted_text="",
            source_kind=media_kind,
            media_metadata={"upload_mode": "multipart"},
            version_number=(previous.version_number + 1) if previous else 1,
            parent_document_id=previous.id if previous else None,
        )
        created = DocumentRepository(session).create(document)
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="media.uploaded",
                resource_type="project",
                resource_id=project_id,
                metadata_json=json.dumps(
                    {
                        "document_id": created.id,
                        "source_kind": media_kind,
                        "version_number": created.version_number,
                        "upload_mode": "multipart",
                    }
                ),
            )
        )
        session.commit()
        session.refresh(created)
        return created

    @app.post(
        "/v1/projects/{project_id}/media-uploads",
        response_model=MediaUploadSessionRead,
        status_code=status.HTTP_201_CREATED,
        tags=["media"],
    )
    def initiate_media_upload(
        project_id: str,
        payload: MediaUploadInit,
        request: Request,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
        """Create a Cloud Storage resumable upload session for production-size media."""
        require_project(session, project_id, organization_id)
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin", "producer", "coordinator"})
        filename = Path(payload.filename).name
        extension = Path(filename).suffix.lower()
        content_type = payload.mime_type.lower()
        if content_type == "application/octet-stream":
            content_type = MEDIA_MIME_BY_EXTENSION.get(extension, content_type)
        if extension not in ALLOWED_MEDIA_EXTENSIONS or (
            content_type not in ALLOWED_MEDIA_MIME_TYPES
            and content_type != "application/octet-stream"
        ):
            raise HTTPException(status_code=415, detail="unsupported_media_type")
        if payload.size_bytes > settings.max_media_size_bytes:
            raise HTTPException(status_code=413, detail="media_too_large")
        if not object_store.supports_resumable_uploads():
            raise HTTPException(status_code=501, detail="resumable_media_upload_requires_gcs")

        media_kind = "video" if content_type.startswith("video/") or extension in {
            ".mp4",
            ".mov",
            ".webm",
            ".mkv",
            ".mpeg",
            ".mpg",
        } else "audio"
        document_id = str(uuid4())
        object_key = f"{organization_id}/{project_id}/{document_id}.media"
        try:
            upload_url = object_store.create_resumable_upload_session(
                object_key,
                content_type,
                payload.size_bytes,
                origin=request.headers.get("origin"),
            )
        except Exception as exc:
            request_logger.exception("media_upload_session_creation_failed")
            raise HTTPException(status_code=503, detail="media_upload_session_unavailable") from exc
        previous = DocumentRepository(session).latest_for_project(project_id, organization_id)
        document = Document(
            id=document_id,
            organization_id=organization_id,
            project_id=project_id,
            original_filename=filename,
            mime_type=content_type,
            size_bytes=payload.size_bytes,
            sha256="pending",
            object_key=object_key,
            extracted_text="",
            source_kind=media_kind,
            media_metadata={"upload_mode": "resumable", "upload_state": "started"},
            status="uploading",
            version_number=(previous.version_number + 1) if previous else 1,
            parent_document_id=previous.id if previous else None,
        )
        created = DocumentRepository(session).create(document)
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="media.upload_started",
                resource_type="project",
                resource_id=project_id,
                metadata_json=json.dumps(
                    {"document_id": created.id, "source_kind": media_kind, "upload_mode": "resumable"}
                ),
            )
        )
        session.commit()
        return {
            "document_id": created.id,
            "object_key": object_key,
            "upload_url": upload_url,
            "source_kind": media_kind,
            "expires_in_seconds": 3600,
        }

    @app.post(
        "/v1/documents/{document_id}/complete-upload",
        response_model=DocumentRead,
        tags=["media"],
    )
    def complete_media_upload(
        document_id: str,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Document:
        actor_id = x_actor_id or "demo-user"
        document = DocumentRepository(session).get(document_id, organization_id)
        if document is None or document.source_kind not in {"video", "audio"}:
            raise HTTPException(status_code=404, detail="media_document_not_found")
        require_role(session, organization_id, actor_id, {"admin", "producer", "coordinator"})
        try:
            metadata = object_store.get_metadata(document.object_key)
        except Exception as exc:
            request_logger.exception("media_upload_completion_metadata_failed")
            raise HTTPException(status_code=409, detail="media_upload_not_found") from exc
        if metadata.size_bytes != document.size_bytes:
            raise HTTPException(status_code=409, detail="media_size_mismatch")
        document.status = "uploaded"
        document.media_metadata = {
            **(document.media_metadata or {}),
            "upload_state": "complete",
            "content_type": metadata.content_type or document.mime_type,
            "md5_hash": metadata.md5_hash,
        }
        if document.sha256 == "pending":
            document.sha256 = f"gcs-md5:{metadata.md5_hash or 'unavailable'}"
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="media.upload_completed",
                resource_type="document",
                resource_id=document.id,
                metadata_json=json.dumps({"size_bytes": metadata.size_bytes}),
            )
        )
        session.commit()
        session.refresh(document)
        return document

    @app.get(
        "/v1/projects/{project_id}/documents", response_model=list[DocumentRead], tags=["documents"]
    )
    def list_documents(
        project_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[Document]:
        require_project(session, project_id, organization_id)
        return DocumentRepository(session).list(project_id, organization_id)

    @app.get(
        "/v1/projects/{project_id}/documents/{from_document_id}/diff/{to_document_id}",
        response_model=DocumentDiffRead,
        tags=["documents"],
    )
    def diff_documents(
        project_id: str,
        from_document_id: str,
        to_document_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
        require_project(session, project_id, organization_id)
        documents = DocumentRepository(session)
        before = documents.get(from_document_id, organization_id)
        after = documents.get(to_document_id, organization_id)
        if (
            before is None
            or after is None
            or before.project_id != project_id
            or after.project_id != project_id
        ):
            raise HTTPException(status_code=404, detail="document_not_found")
        matcher = difflib.SequenceMatcher(
            a=before.extracted_text.splitlines(), b=after.extracted_text.splitlines()
        )
        added_lines = removed_lines = changed_lines = 0
        for tag, start_before, end_before, start_after, end_after in matcher.get_opcodes():
            if tag == "insert":
                added_lines += end_after - start_after
            elif tag == "delete":
                removed_lines += end_before - start_before
            elif tag == "replace":
                changed_lines += max(end_before - start_before, end_after - start_after)
        before_assets = {
            asset.canonical_name
            for asset in AssetRepository(session).list_for_project(project_id, organization_id)
            if asset.document_id == before.id
        }
        after_assets = {
            asset.canonical_name
            for asset in AssetRepository(session).list_for_project(project_id, organization_id)
            if asset.document_id == after.id
        }
        return {
            "project_id": project_id,
            "from_document_id": before.id,
            "to_document_id": after.id,
            "added_lines": added_lines,
            "removed_lines": removed_lines,
            "changed_lines": changed_lines,
            "added_assets": sorted(after_assets - before_assets),
            "removed_assets": sorted(before_assets - after_assets),
        }

    @app.post(
        "/v1/projects/{project_id}/attachments",
        response_model=ProjectAttachmentRead,
        status_code=status.HTTP_201_CREATED,
        tags=["delivery"],
    )
    async def upload_project_attachment(
        project_id: str,
        file: UploadFile = File(...),
        asset_id: str | None = None,
        attachment_type: str = "supporting_document",
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> ProjectAttachment:
        require_project(session, project_id, organization_id)
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin", "producer", "coordinator", "legal_reviewer"})
        if asset_id is not None:
            asset = AssetRepository(session).get(asset_id, organization_id)
            if asset is None or asset.project_id != project_id:
                raise HTTPException(status_code=404, detail="asset_not_found")
        filename = Path(file.filename or "attachment.bin").name
        content = await file.read(settings.max_upload_bytes + 1)
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="attachment_too_large")
        attachment_id = str(uuid4())
        object_key = f"{organization_id}/{project_id}/attachments/{attachment_id}-{filename}"
        object_store.save_bytes(object_key, content)
        attachment = ProjectAttachment(
            id=attachment_id,
            organization_id=organization_id,
            project_id=project_id,
            asset_id=asset_id,
            original_filename=filename,
            mime_type=(file.content_type or "application/octet-stream"),
            size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
            object_key=object_key,
            attachment_type=attachment_type,
            created_by=actor_id,
        )
        return ProjectAttachmentRepository(session).create(attachment)

    @app.get(
        "/v1/projects/{project_id}/attachments",
        response_model=list[ProjectAttachmentRead],
        tags=["delivery"],
    )
    def list_project_attachments(
        project_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[ProjectAttachment]:
        require_project(session, project_id, organization_id)
        return ProjectAttachmentRepository(session).list_for_project(project_id, organization_id)

    @app.get("/v1/projects/{project_id}/assets", response_model=list[AssetRead], tags=["assets"])
    def list_assets(
        project_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ):
        require_project(session, project_id, organization_id)
        return AssetRepository(session).list_for_project(project_id, organization_id)

    @app.patch(
        "/v1/assets/{asset_id}",
        response_model=AssetRead,
        tags=["assets"],
    )
    def update_asset(
        asset_id: str,
        payload: AssetUpdate,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Asset:
        actor_id = x_actor_id or "demo-user"
        require_role(
            session,
            organization_id,
            actor_id,
            {"admin", "producer", "coordinator", "legal_reviewer"},
        )
        values = payload.model_dump(exclude_unset=True)
        asset = AssetRepository(session).update(asset_id, organization_id, **values)
        if asset is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="asset.updated",
                resource_type="asset",
                resource_id=asset_id,
                metadata_json=json.dumps(values, default=str),
            )
        )
        session.commit()
        session.refresh(asset)
        if asset.owner_id and asset.owner_id != actor_id:
            session.add(
                Notification(
                    organization_id=organization_id,
                    actor_id=asset.owner_id,
                    notification_type="asset.assigned",
                    title="Asset assigned to you",
                    body=f"{asset.canonical_name} has a new review assignment.",
                    resource_type="asset",
                    resource_id=asset.id,
                )
            )
            session.commit()
        return asset

    @app.get(
        "/v1/assets/{asset_id}/playbook",
        response_model=PlaybookRead,
        tags=["research"],
    )
    def get_asset_playbook(
        asset_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
        asset = AssetRepository(session).get(asset_id, organization_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        return {"category": asset.category, **playbook_for(asset.category)}

    @app.get(
        "/v1/assets/{asset_id}/research-recheck",
        response_model=ResearchRecheckRead,
        tags=["research"],
    )
    def get_asset_recheck(
        asset_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> ResearchRecheck:
        if AssetRepository(session).get(asset_id, organization_id) is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        recheck = ResearchRecheckRepository(session).get_for_asset(asset_id, organization_id)
        if recheck is None:
            raise HTTPException(status_code=404, detail="research_recheck_not_found")
        return recheck

    @app.post(
        "/v1/assets/{asset_id}/research-recheck",
        response_model=ResearchRecheckRead,
        status_code=status.HTTP_201_CREATED,
        tags=["research"],
    )
    def schedule_asset_recheck(
        asset_id: str,
        payload: ResearchRecheckCreate,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> ResearchRecheck:
        actor_id = x_actor_id or "demo-user"
        require_role(
            session,
            organization_id,
            actor_id,
            {"admin", "producer", "coordinator", "legal_reviewer"},
        )
        if AssetRepository(session).get(asset_id, organization_id) is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        now = datetime.now(UTC)
        repository = ResearchRecheckRepository(session)
        existing = repository.get_for_asset(asset_id, organization_id)
        if existing is not None:
            return repository.update(
                existing.id,
                organization_id,
                cadence_days=payload.cadence_days,
                next_run_at=now + timedelta(days=payload.cadence_days),
                active=True,
            )
        return repository.create(
            ResearchRecheck(
                organization_id=organization_id,
                asset_id=asset_id,
                cadence_days=payload.cadence_days,
                next_run_at=now + timedelta(days=payload.cadence_days),
                active=True,
                created_by=actor_id,
            )
        )

    @app.post(
        "/v1/assets/{asset_id}/research-recheck/run",
        response_model=ResearchSessionRead,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["research"],
    )
    def run_asset_recheck(
        asset_id: str,
        background_tasks: BackgroundTasks,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
        actor_id = x_actor_id or "demo-user"
        require_role(
            session,
            organization_id,
            actor_id,
            {"admin", "producer", "coordinator", "legal_reviewer"},
        )
        asset = AssetRepository(session).get(asset_id, organization_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        recheck = ResearchRecheckRepository(session).get_for_asset(asset_id, organization_id)
        if recheck is None:
            raise HTTPException(status_code=404, detail="research_recheck_not_found")
        research_session, tasks = create_research_session_records(
            session, asset, organization_id, None
        )
        now = datetime.now(UTC)
        ResearchRecheckRepository(session).update(
            recheck.id,
            organization_id,
            last_run_at=now,
            last_session_id=research_session.id,
            next_run_at=now + timedelta(days=recheck.cadence_days),
        )
        for task in tasks:
            background_tasks.add_task(process_research_task, db, task.id, organization_id, settings)
        return research_session_payload(research_session, tasks)

    @app.get(
        "/v1/projects/{project_id}/research-rechecks",
        response_model=list[ResearchRecheckRead],
        tags=["research"],
    )
    def list_project_rechecks(
        project_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[ResearchRecheck]:
        require_project(session, project_id, organization_id)
        return ResearchRecheckRepository(session).list_for_project(project_id, organization_id)

    @app.post(
        "/v1/research-rechecks/run-due",
        response_model=dict[str, object],
        status_code=status.HTTP_202_ACCEPTED,
        tags=["research"],
    )
    def run_due_rechecks(
        background_tasks: BackgroundTasks,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin", "producer", "coordinator"})
        now = datetime.now(UTC)
        due = list(
            session.scalars(
                select(ResearchRecheck)
                .where(
                    ResearchRecheck.organization_id == organization_id,
                    ResearchRecheck.active.is_(True),
                    ResearchRecheck.next_run_at <= now,
                )
                .order_by(ResearchRecheck.next_run_at.asc())
                .limit(25)
            )
        )
        scheduled: list[str] = []
        deferred: list[str] = []
        for recheck in due:
            asset = AssetRepository(session).get(recheck.asset_id, organization_id)
            if asset is None:
                recheck.active = False
                continue
            active_session = next(
                (
                    item
                    for item in ResearchSessionRepository(session).list_for_asset(
                        asset.id, organization_id
                    )
                    if item.status in {"planned", "running"}
                ),
                None,
            )
            if active_session is not None:
                recheck.next_run_at = now + timedelta(minutes=15)
                deferred.append(recheck.id)
                continue
            research_session, tasks = create_research_session_records(
                session, asset, organization_id, None
            )
            recheck.last_run_at = now
            recheck.last_session_id = research_session.id
            recheck.next_run_at = now + timedelta(days=recheck.cadence_days)
            scheduled.append(recheck.id)
            for task in tasks:
                background_tasks.add_task(
                    process_research_task, db, task.id, organization_id, settings
                )
        if due:
            session.commit()
        return {
            "scheduled_count": len(scheduled),
            "recheck_ids": scheduled,
            "deferred_count": len(deferred),
            "deferred_recheck_ids": deferred,
        }

    @app.get(
        "/v1/projects/{project_id}/delivery-readiness",
        response_model=DeliveryReadinessRead,
        tags=["delivery"],
    )
    def project_delivery_readiness(
        project_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
        require_project(session, project_id, organization_id)
        assets = AssetRepository(session).list_for_project(project_id, organization_id)
        cards = ClearanceCardRepository(session).list_for_project(project_id, organization_id)
        latest_cards: dict[str, ClearanceCard] = {}
        for card in cards:
            latest_cards.setdefault(card.asset_id, card)
        clear_assets = sum(
            card.status == "approved" and not card.needs_human_review
            for card in latest_cards.values()
        )
        blocked_assets = sum(asset.risk_status == "blocked" for asset in assets)
        unresolved_assets = max(len(assets) - clear_assets, 0)
        now = datetime.now(UTC)
        stale_rechecks = sum(
            recheck.active and as_utc(recheck.next_run_at) <= now
            for recheck in ResearchRecheckRepository(session).list_for_project(
                project_id, organization_id
            )
        )
        open_requests = int(
            session.scalar(
                select(func.count(OutreachDraft.id))
                .join(Asset, Asset.id == OutreachDraft.asset_id)
                .where(
                    Asset.project_id == project_id,
                    Asset.organization_id == organization_id,
                    OutreachDraft.organization_id == organization_id,
                    OutreachDraft.status.not_in(("closed", "cancelled")),
                )
            )
            or 0
        )
        required_actions: list[str] = []
        if unresolved_assets:
            required_actions.append(f"Resolve {unresolved_assets} asset review item(s)")
        if blocked_assets:
            required_actions.append(f"Address {blocked_assets} blocked asset(s)")
        if stale_rechecks:
            required_actions.append(f"Recheck {stale_rechecks} stale evidence schedule(s)")
        if open_requests:
            required_actions.append(f"Close or update {open_requests} permission request(s)")
        if not assets:
            required_actions.append("Upload and analyze source material")
        readiness = "ready" if assets and not required_actions else "conditional" if assets else "not_ready"
        return {
            "project_id": project_id,
            "status": readiness,
            "total_assets": len(assets),
            "clear_assets": clear_assets,
            "unresolved_assets": unresolved_assets,
            "blocked_assets": blocked_assets,
            "stale_rechecks": stale_rechecks,
            "open_requests": open_requests,
            "required_actions": required_actions,
        }

    @app.get(
        "/v1/projects/{project_id}/activity",
        response_model=list[AuditEventRead],
        tags=["audit"],
    )
    def list_project_activity(
        project_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[AuditEvent]:
        require_project(session, project_id, organization_id)
        return AuditRepository(session).list_for_project(project_id, organization_id)

    @app.get(
        "/v1/activity",
        response_model=list[AuditEventRead],
        tags=["audit"],
    )
    def list_workspace_activity(
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[AuditEvent]:
        return AuditRepository(session).list_for_organization(organization_id)

    @app.get(
        "/v1/notifications",
        response_model=list[NotificationRead],
        tags=["collaboration"],
    )
    def list_notifications(
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[Notification]:
        actor_id = x_actor_id or "demo-user"
        require_role(
            session,
            organization_id,
            actor_id,
            {"admin", "producer", "coordinator", "legal_reviewer", "post_supervisor", "viewer"},
        )
        return NotificationRepository(session).list_for_actor(organization_id, actor_id)

    @app.post(
        "/v1/notifications/{notification_id}/read",
        response_model=NotificationRead,
        tags=["collaboration"],
    )
    def mark_notification_read(
        notification_id: str,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Notification:
        actor_id = x_actor_id or "demo-user"
        require_role(
            session,
            organization_id,
            actor_id,
            {"admin", "producer", "coordinator", "legal_reviewer", "post_supervisor", "viewer"},
        )
        notification = NotificationRepository(session).mark_read(
            notification_id, organization_id, actor_id
        )
        if notification is None:
            raise HTTPException(status_code=404, detail="notification_not_found")
        return notification

    @app.get(
        "/v1/assets/{asset_id}/comments",
        response_model=list[AssetCommentRead],
        tags=["collaboration"],
    )
    def list_asset_comments(
        asset_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[AssetComment]:
        if AssetRepository(session).get(asset_id, organization_id) is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        return AssetCommentRepository(session).list_for_asset(asset_id, organization_id)

    @app.post(
        "/v1/assets/{asset_id}/comments",
        response_model=AssetCommentRead,
        status_code=status.HTTP_201_CREATED,
        tags=["collaboration"],
    )
    def create_asset_comment(
        asset_id: str,
        payload: AssetCommentCreate,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> AssetComment:
        actor_id = x_actor_id or "demo-user"
        require_role(
            session,
            organization_id,
            actor_id,
            {"admin", "producer", "coordinator", "legal_reviewer", "post_supervisor", "viewer"},
        )
        if AssetRepository(session).get(asset_id, organization_id) is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        mention_ids = list(dict.fromkeys(payload.mention_ids))
        member_ids = {
            member.actor_id
            for member in MembershipRepository(session).list_for_organization(organization_id)
            if member.status == "active"
        }
        if organization_id == settings.default_organization_id:
            member_ids.update({"demo-user", "demo-producer", "demo-reviewer"})
        invalid_mentions = sorted(set(mention_ids) - member_ids)
        if invalid_mentions:
            raise HTTPException(
                status_code=422,
                detail={"code": "unknown_mention", "actor_ids": invalid_mentions},
            )
        comment = AssetComment(
            organization_id=organization_id,
            asset_id=asset_id,
            author_id=actor_id,
            body=payload.body,
            mention_ids=mention_ids,
        )
        for mentioned_actor_id in mention_ids:
            session.add(
                Notification(
                    organization_id=organization_id,
                    actor_id=mentioned_actor_id,
                    notification_type="asset.mentioned",
                    title="You were mentioned in an asset comment",
                    body=payload.body,
                    resource_type="asset",
                    resource_id=asset_id,
                )
            )
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="asset.comment_created",
                resource_type="asset",
                resource_id=asset_id,
                metadata_json=json.dumps({"mention_ids": mention_ids}),
            )
        )
        return AssetCommentRepository(session).create(comment)

    @app.get(
        "/v1/projects/{project_id}/clearance-cards",
        response_model=list[ClearanceCardRead],
        tags=["review"],
    )
    def list_clearance_cards(
        project_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[ClearanceCard]:
        require_project(session, project_id, organization_id)
        return ClearanceCardRepository(session).list_for_project(project_id, organization_id)

    @app.get(
        "/v1/projects/{project_id}/approvals",
        response_model=list[ApprovalRead],
        tags=["review"],
    )
    def list_project_approvals(
        project_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[Approval]:
        require_project(session, project_id, organization_id)
        return ApprovalRepository(session).list_for_project(project_id, organization_id)

    @app.post(
        "/v1/projects/{project_id}/analysis-runs",
        response_model=JobRead,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["analysis"],
    )
    def create_analysis_run(
        project_id: str,
        payload: AnalysisRunCreate,
        background_tasks: BackgroundTasks,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Job:
        require_project(session, project_id, organization_id)
        require_role(
            session,
            organization_id,
            x_actor_id or "demo-user",
            {"admin", "producer", "coordinator"},
        )
        document: Document | None = None
        if payload.document_id is not None:
            document = DocumentRepository(session).get(payload.document_id, organization_id)
            if document is None or document.project_id != project_id:
                raise HTTPException(status_code=404, detail="document_not_found")
        job_type = "media_analysis" if document and document.source_kind in {"video", "audio"} else "document_analysis"
        job = Job(
            organization_id=organization_id,
            project_id=project_id,
            job_type=job_type,
            status="queued",
            metadata_json=json.dumps({"document_id": payload.document_id}),
        )
        created = JobRepository(session).create(job)
        if payload.document_id is not None:
            background_tasks.add_task(
                process_document_analysis,
                db,
                object_store,
                created.id,
                payload.document_id,
                organization_id,
            )
        return created

    @app.get("/v1/jobs/{job_id}", response_model=JobRead, tags=["analysis"])
    def get_job(
        job_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Job:
        job = JobRepository(session).get(job_id, organization_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job_not_found")
        return job

    @app.post(
        "/v1/assets/{asset_id}/research-sessions",
        response_model=ResearchSessionRead,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["research"],
    )
    def create_research_session(
        asset_id: str,
        payload: ResearchSessionCreate,
        background_tasks: BackgroundTasks,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
        require_role(
            session,
            organization_id,
            x_actor_id or "demo-user",
            {"admin", "producer", "coordinator", "legal_reviewer"},
        )
        asset = AssetRepository(session).get(asset_id, organization_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        active_session = next(
            (
                item
                for item in ResearchSessionRepository(session).list_for_asset(
                    asset_id, organization_id
                )
                if item.status in {"planned", "running"}
            ),
            None,
        )
        if active_session is not None:
            raise HTTPException(status_code=409, detail="research_session_already_running")
        research_session, tasks = create_research_session_records(
            session, asset, organization_id, payload.objective
        )
        for task in tasks:
            background_tasks.add_task(
                process_research_task, db, task.id, organization_id, settings
            )
        return research_session_payload(research_session, tasks)

    @app.get(
        "/v1/projects/{project_id}/research-sessions",
        response_model=list[ResearchSessionRead],
        tags=["research"],
    )
    def list_research_sessions(
        project_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[dict[str, object]]:
        require_project(session, project_id, organization_id)
        sessions = ResearchSessionRepository(session).list_for_project(
            project_id, organization_id
        )
        tasks = ResearchTaskRepository(session)
        payloads = []
        for research_session in sessions:
            session_tasks = tasks.list_for_session(research_session.id, organization_id)
            payloads.append(
                research_session_payload(
                    research_session,
                    session_tasks,
                    sources_by_task(session, session_tasks),
                    provider_request_ids(session, session_tasks),
                )
            )
        return payloads

    @app.get(
        "/v1/research-sessions/{session_id}",
        response_model=ResearchSessionRead,
        tags=["research"],
    )
    def get_research_session(
        session_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
        research_session = ResearchSessionRepository(session).get(session_id, organization_id)
        if research_session is None:
            raise HTTPException(status_code=404, detail="research_session_not_found")
        tasks = ResearchTaskRepository(session).list_for_session(session_id, organization_id)
        return research_session_payload(
            research_session,
            tasks,
            sources_by_task(session, tasks),
            provider_request_ids(session, tasks),
        )

    @app.post(
        "/v1/research-sessions/{session_id}/retry",
        response_model=ResearchSessionRead,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["research"],
    )
    def retry_research_session(
        session_id: str,
        background_tasks: BackgroundTasks,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
        require_role(
            session,
            organization_id,
            x_actor_id or "demo-user",
            {"admin", "producer", "coordinator", "legal_reviewer"},
        )
        previous = ResearchSessionRepository(session).get(session_id, organization_id)
        if previous is None:
            raise HTTPException(status_code=404, detail="research_session_not_found")
        asset = AssetRepository(session).get(previous.asset_id, organization_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        research_session, tasks = create_research_session_records(
            session, asset, organization_id, previous.objective
        )
        for task in tasks:
            background_tasks.add_task(
                process_research_task, db, task.id, organization_id, settings
            )
        return research_session_payload(research_session, tasks)

    @app.post(
        "/v1/research-tasks/{task_id}/follow-up",
        response_model=ResearchSessionRead,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["research"],
    )
    def create_research_follow_up(
        task_id: str,
        payload: ResearchFollowUpCreate,
        background_tasks: BackgroundTasks,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
        require_role(
            session,
            organization_id,
            x_actor_id or "demo-user",
            {"admin", "producer", "coordinator", "legal_reviewer"},
        )
        task = ResearchTaskRepository(session).get(task_id, organization_id)
        if task is None:
            raise HTTPException(status_code=404, detail="research_task_not_found")
        parent_session = ResearchSessionRepository(session).get(task.session_id, organization_id)
        if parent_session is None:
            raise HTTPException(status_code=404, detail="research_session_not_found")
        asset = AssetRepository(session).get(parent_session.asset_id, organization_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        active_session = next(
            (
                item
                for item in ResearchSessionRepository(session).list_for_asset(
                    asset.id, organization_id
                )
                if item.status in {"planned", "running"}
            ),
            None,
        )
        if active_session is not None:
            raise HTTPException(status_code=409, detail="research_session_already_running")
        research_session, tasks = create_follow_up_records(
            session, task, asset, organization_id, payload.objective
        )
        for follow_up_task in tasks:
            background_tasks.add_task(
                process_research_task, db, follow_up_task.id, organization_id, settings
            )
        return research_session_payload(research_session, tasks)

    @app.post(
        "/v1/assets/{asset_id}/research-runs",
        response_model=ResearchRunRead,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["research"],
    )
    def create_research_run(
        asset_id: str,
        payload: ResearchRunCreate,
        background_tasks: BackgroundTasks,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> ResearchRun:
        require_role(
            session,
            organization_id,
            x_actor_id or "demo-user",
            {"admin", "producer", "coordinator", "legal_reviewer"},
        )
        asset = AssetRepository(session).get(asset_id, organization_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        run = ResearchRun(
            organization_id=organization_id,
            asset_id=asset_id,
            provider="parallel",
            operation="search",
            objective=payload.objective,
            query=payload.query,
        )
        created = ResearchRunRepository(session).create(run)
        background_tasks.add_task(process_research_run, db, created.id, organization_id, settings)
        return created

    @app.get("/v1/research-runs/{run_id}", response_model=ResearchRunRead, tags=["research"])
    def get_research_run(
        run_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> ResearchRun:
        run = ResearchRunRepository(session).get(run_id, organization_id)
        if run is None:
            raise HTTPException(status_code=404, detail="research_run_not_found")
        return run

    @app.get(
        "/v1/research-runs/{run_id}/sources",
        response_model=list[SourceRecordRead],
        tags=["research"],
    )
    def list_research_sources(
        run_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ):
        run = ResearchRunRepository(session).get(run_id, organization_id)
        if run is None:
            raise HTTPException(status_code=404, detail="research_run_not_found")
        return ResearchRunRepository(session).list_sources(run_id)

    @app.get(
        "/v1/assets/{asset_id}/clearance-card",
        response_model=ClearanceCardRead,
        tags=["review"],
    )
    def get_clearance_card(
        asset_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> ClearanceCard:
        asset = AssetRepository(session).get(asset_id, organization_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        card = ClearanceCardRepository(session).get_for_asset(asset_id, organization_id)
        if card is None:
            raise HTTPException(status_code=404, detail="clearance_card_not_found")
        return card

    @app.get(
        "/v1/assets/{asset_id}/approvals",
        response_model=list[ApprovalRead],
        tags=["review"],
    )
    def list_asset_approvals(
        asset_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[Approval]:
        asset = AssetRepository(session).get(asset_id, organization_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        return ApprovalRepository(session).list_for_asset(asset_id, organization_id)

    @app.post(
        "/v1/assets/{asset_id}/approvals",
        response_model=ApprovalRead,
        status_code=status.HTTP_201_CREATED,
        tags=["review"],
    )
    def record_approval(
        asset_id: str,
        payload: ApprovalCreate,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Approval:
        actor_id = x_actor_id or "demo-user"
        require_role(
            session,
            organization_id,
            actor_id,
            {"admin", "producer", "coordinator", "legal_reviewer"},
        )
        asset = AssetRepository(session).get(asset_id, organization_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        cards = ClearanceCardRepository(session)
        card = cards.get_for_asset(asset_id, organization_id)
        if card is None:
            raise HTTPException(status_code=404, detail="clearance_card_not_found")

        card_status_by_decision = {
            "approve_next_action": ("approved", "approved_for_delivery", False),
            "request_more_research": ("needs_more_research", "needs_review", True),
            "mark_not_applicable": ("approved", "likely_clear", False),
            "reject": ("rejected", "blocked", False),
            "escalate_to_legal": ("escalated", "blocked", True),
        }
        card_status, risk_status, needs_human_review = card_status_by_decision[payload.decision]
        next_action_by_decision = {
            "approve_next_action": "Proceed with permission work or delivery review",
            "request_more_research": "Run a focused evidence follow-up",
            "mark_not_applicable": "Record the editorial rationale",
            "reject": "Replace or remove the asset",
            "escalate_to_legal": "Confirm rights position with legal",
        }
        latest_approval = ApprovalRepository(session).get_latest_for_card(card.id, organization_id)
        approval = Approval(
            organization_id=organization_id,
            asset_id=asset_id,
            clearance_card_id=card.id,
            decision=payload.decision,
            note=payload.note,
            actor_id=actor_id,
            supersedes_id=latest_approval.id if latest_approval else None,
        )
        card.status = card_status
        card.needs_human_review = needs_human_review
        asset.risk_status = risk_status
        asset.next_action = next_action_by_decision[payload.decision]
        session.add(approval)
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=approval.actor_id,
                action="approval.recorded",
                resource_type="asset",
                resource_id=asset_id,
                metadata_json=json.dumps(
                    {"decision": payload.decision, "clearance_card_id": card.id}
                ),
            )
        )
        if asset.owner_id and asset.owner_id != actor_id:
            session.add(
                Notification(
                    organization_id=organization_id,
                    actor_id=asset.owner_id,
                    notification_type="approval.recorded",
                    title="Asset decision recorded",
                    body=f"{actor_id} recorded {payload.decision.replace('_', ' ')} for {asset.canonical_name}.",
                    resource_type="asset",
                    resource_id=asset_id,
                )
            )
        session.commit()
        session.refresh(approval)
        return approval

    @app.post(
        "/v1/assets/{asset_id}/outreach-drafts",
        response_model=OutreachDraftRead,
        status_code=status.HTTP_201_CREATED,
        tags=["outreach"],
    )
    def create_outreach_draft(
        asset_id: str,
        payload: OutreachDraftCreate,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> OutreachDraft:
        actor_id = x_actor_id or "demo-user"
        require_role(
            session,
            organization_id,
            actor_id,
            {"admin", "producer", "coordinator", "legal_reviewer"},
        )
        asset = AssetRepository(session).get(asset_id, organization_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        card = ClearanceCardRepository(session).get_for_asset(asset_id, organization_id)
        if card is None:
            raise HTTPException(status_code=404, detail="clearance_card_not_found")
        project = require_project(session, asset.project_id, organization_id)
        subject, body = build_outreach_draft(project, asset, card, payload.recipient_hint)
        draft = OutreachDraft(
            organization_id=organization_id,
            asset_id=asset_id,
            clearance_card_id=card.id,
            recipient_hint=payload.recipient_hint,
            subject=subject,
            body=body,
            status="draft",
            generated_by="clearcut_template",
            created_by=actor_id,
        )
        session.add(draft)
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="outreach_draft.created",
                resource_type="asset",
                resource_id=asset_id,
                metadata_json=json.dumps({"recipient_hint": payload.recipient_hint}),
            )
        )
        session.commit()
        session.refresh(draft)
        return draft

    @app.get(
        "/v1/assets/{asset_id}/outreach-drafts",
        response_model=list[OutreachDraftRead],
        tags=["outreach"],
    )
    def list_outreach_drafts(
        asset_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[OutreachDraft]:
        asset = AssetRepository(session).get(asset_id, organization_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        return OutreachDraftRepository(session).list_for_asset(asset_id, organization_id)

    @app.patch(
        "/v1/outreach-drafts/{draft_id}",
        response_model=OutreachDraftRead,
        tags=["outreach"],
    )
    def update_outreach_draft(
        draft_id: str,
        payload: OutreachDraftUpdate,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> OutreachDraft:
        actor_id = x_actor_id or "demo-user"
        require_role(
            session,
            organization_id,
            actor_id,
            {"admin", "producer", "coordinator", "legal_reviewer"},
        )
        values = payload.model_dump(exclude_unset=True)
        if values.get("status") == "approved":
            values["approved_by"] = actor_id
        if values.get("status") == "sent":
            values["sent_at"] = datetime.now(UTC)
        if values.get("status") == "response_received":
            values["responded_at"] = datetime.now(UTC)
        draft = OutreachDraftRepository(session).update(draft_id, organization_id, **values)
        if draft is None:
            raise HTTPException(status_code=404, detail="outreach_draft_not_found")
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="outreach_draft.updated",
                resource_type="asset",
                resource_id=draft.asset_id,
                metadata_json=json.dumps(values, default=str),
            )
        )
        session.commit()
        session.refresh(draft)
        return draft

    @app.post(
        "/v1/projects/{project_id}/reports",
        response_model=ClearanceReportRead,
        status_code=status.HTTP_201_CREATED,
        tags=["reports"],
    )
    def create_report(
        project_id: str,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> ClearanceReport:
        actor_id = x_actor_id or "demo-user"
        require_role(
            session,
            organization_id,
            actor_id,
            {"admin", "producer", "coordinator", "legal_reviewer"},
        )
        project = require_project(session, project_id, organization_id)
        assets = AssetRepository(session).list_for_project(project_id, organization_id)
        cards = ClearanceCardRepository(session).list_for_project(project_id, organization_id)
        sources: list = []
        runs = ResearchRunRepository(session)
        for card in cards:
            sources.extend(runs.list_sources(card.research_run_id))
        approvals = ApprovalRepository(session).list_for_project(project_id, organization_id)
        drafts: list[OutreachDraft] = []
        outreach = OutreachDraftRepository(session)
        for asset in assets:
            drafts.extend(outreach.list_for_asset(asset.id, organization_id))
        previous_report = ClearanceReportRepository(session).list_for_project(
            project_id, organization_id
        )
        report_version = (previous_report[0].version_number + 1) if previous_report else 1
        policy_version = "risk-policy-v1"
        content_markdown = build_clearance_report(
            project,
            assets,
            cards,
            sources,
            approvals,
            report_version=report_version,
            policy_version=policy_version,
            drafts=drafts,
        )
        report = ClearanceReport(
            organization_id=organization_id,
            project_id=project_id,
            report_type="clearance_summary",
            status="ready",
            generated_by="clearcut_report_builder",
            content_markdown=content_markdown,
            version_number=report_version,
            content_hash=sha256(content_markdown.encode("utf-8")).hexdigest(),
            policy_version=policy_version,
            source_snapshot_at=datetime.now(UTC),
        )
        session.add(report)
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="report.created",
                resource_type="project",
                resource_id=project_id,
                metadata_json=json.dumps({"report_type": report.report_type}),
            )
        )
        session.commit()
        session.refresh(report)
        return report

    @app.get(
        "/v1/projects/{project_id}/reports",
        response_model=list[ClearanceReportRead],
        tags=["reports"],
    )
    def list_reports(
        project_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[ClearanceReport]:
        require_project(session, project_id, organization_id)
        return ClearanceReportRepository(session).list_for_project(project_id, organization_id)

    @app.get(
        "/v1/projects/{project_id}/reports/{report_id}",
        response_model=ClearanceReportRead,
        tags=["reports"],
    )
    def get_report(
        project_id: str,
        report_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> ClearanceReport:
        require_project(session, project_id, organization_id)
        report = ClearanceReportRepository(session).get(report_id, project_id, organization_id)
        if report is None:
            raise HTTPException(status_code=404, detail="report_not_found")
        return report

    @app.get(
        "/v1/projects/{project_id}/reports/{report_id}/pdf",
        response_class=Response,
        responses={200: {"content": {"application/pdf": {}}}},
        tags=["reports"],
    )
    def download_report_pdf(
        project_id: str,
        report_id: str,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Response:
        require_project(session, project_id, organization_id)
        report = ClearanceReportRepository(session).get(report_id, project_id, organization_id)
        if report is None:
            raise HTTPException(status_code=404, detail="report_not_found")
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=x_actor_id or "demo-user",
                action="report.downloaded",
                resource_type="project",
                resource_id=project_id,
                metadata_json=json.dumps({"report_id": report_id, "format": "pdf"}),
            )
        )
        session.commit()
        filename = f"clearcut-{project_id}-report.pdf"
        return Response(
            content=build_pdf(report.content_markdown),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.post(
        "/v1/projects/{project_id}/review-shares",
        response_model=ReviewShareRead,
        status_code=status.HTTP_201_CREATED,
        tags=["collaboration"],
    )
    def create_review_share(
        project_id: str,
        payload: ReviewShareCreate,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin", "producer", "coordinator", "legal_reviewer"})
        require_project(session, project_id, organization_id)
        token = f"ccreview_{secrets.token_urlsafe(32)}"
        share = ReviewShare(
            organization_id=organization_id,
            project_id=project_id,
            token_hash=sha256(token.encode("utf-8")).hexdigest(),
            label=payload.label,
            expires_at=payload.expires_at,
            created_by=actor_id,
        )
        created = ReviewShareRepository(session).create(share)
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="review_share.created",
                resource_type="project",
                resource_id=project_id,
                metadata_json=json.dumps({"share_id": created.id, "label": created.label}),
            )
        )
        session.commit()
        return {"id": created.id, "project_id": project_id, "label": created.label, "expires_at": created.expires_at, "revoked_at": created.revoked_at, "created_by": created.created_by, "created_at": created.created_at, "share_token": token}

    @app.get(
        "/v1/projects/{project_id}/review-shares",
        response_model=list[ReviewShareRead],
        tags=["collaboration"],
    )
    def list_review_shares(
        project_id: str,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[ReviewShare]:
        require_project(session, project_id, organization_id)
        require_role(
            session,
            organization_id,
            x_actor_id or "demo-user",
            {"admin", "producer", "coordinator", "legal_reviewer"},
        )
        return ReviewShareRepository(session).list_for_project(project_id, organization_id)

    @app.post(
        "/v1/projects/{project_id}/review-shares/{share_id}/revoke",
        response_model=ReviewShareRead,
        tags=["collaboration"],
    )
    def revoke_review_share(
        project_id: str,
        share_id: str,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> ReviewShare:
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin", "producer", "coordinator"})
        require_project(session, project_id, organization_id)
        share = session.scalar(
            select(ReviewShare).where(
                ReviewShare.id == share_id,
                ReviewShare.project_id == project_id,
                ReviewShare.organization_id == organization_id,
            )
        )
        if share is None:
            raise HTTPException(status_code=404, detail="review_share_not_found")
        revoked = ReviewShareRepository(session).revoke(share_id, organization_id)
        if revoked is None:
            raise HTTPException(status_code=404, detail="review_share_not_found")
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="review_share.revoked",
                resource_type="project",
                resource_id=project_id,
                metadata_json=json.dumps({"share_id": share_id}),
            )
        )
        session.commit()
        return revoked

    @app.get("/v1/review-shares/{share_token}", tags=["collaboration"])
    def get_public_review_share(
        share_token: str,
        session: Session = Depends(get_db),
    ) -> dict[str, object]:
        share = ReviewShareRepository(session).get_by_hash(
            sha256(share_token.encode("utf-8")).hexdigest()
        )
        if (
            share is None
            or share.revoked_at is not None
            or (share.expires_at is not None and as_utc(share.expires_at) <= datetime.now(UTC))
        ):
            raise HTTPException(status_code=404, detail="review_share_not_found")
        project = ProjectRepository(session).get(share.project_id, share.organization_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project_not_found")
        assets = AssetRepository(session).list_for_project(share.project_id, share.organization_id)
        cards = ClearanceCardRepository(session).list_for_project(share.project_id, share.organization_id)
        return {
            "project": {"id": project.id, "title": project.title, "project_type": project.project_type, "status": project.status},
            "readiness": project_delivery_readiness(share.project_id, session, share.organization_id),
            "assets": [
                {"id": asset.id, "canonical_name": asset.canonical_name, "category": asset.category, "risk_status": asset.risk_status}
                for asset in assets
            ],
            "clearance_cards": [
                {"id": card.id, "asset_id": card.asset_id, "status": card.status, "risk_score": card.risk_score, "summary": card.summary, "recommendation": card.recommendation, "evidence_count": card.evidence_count}
                for card in cards
            ],
        }

    @app.post(
        "/v1/organizations/current/api-keys",
        response_model=ApiKeyRead,
        status_code=status.HTTP_201_CREATED,
        tags=["integrations"],
    )
    def create_api_key(
        payload: ApiKeyCreate,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin"})
        secret = f"cc_live_{secrets.token_urlsafe(32)}"
        key = ApiKey(
            organization_id=organization_id,
            name=payload.name,
            key_prefix=secret[:16],
            key_hash=sha256(secret.encode("utf-8")).hexdigest(),
            created_by=actor_id,
        )
        created = ApiKeyRepository(session).create(key)
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="api_key.created",
                resource_type="organization",
                resource_id=organization_id,
                metadata_json=json.dumps({"key_id": created.id, "name": created.name}),
            )
        )
        session.commit()
        return {"id": created.id, "organization_id": created.organization_id, "name": created.name, "key_prefix": created.key_prefix, "created_by": created.created_by, "last_used_at": created.last_used_at, "revoked_at": created.revoked_at, "created_at": created.created_at, "secret": secret}

    @app.get(
        "/v1/organizations/current/api-keys",
        response_model=list[ApiKeyRead],
        tags=["integrations"],
    )
    def list_api_keys(
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[ApiKey]:
        require_role(session, organization_id, x_actor_id or "demo-user", {"admin"})
        return ApiKeyRepository(session).list_for_organization(organization_id)

    @app.post(
        "/v1/organizations/current/api-keys/{key_id}/revoke",
        response_model=ApiKeyRead,
        tags=["integrations"],
    )
    def revoke_api_key(
        key_id: str,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> ApiKey:
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin"})
        key = ApiKeyRepository(session).revoke(key_id, organization_id)
        if key is None:
            raise HTTPException(status_code=404, detail="api_key_not_found")
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="api_key.revoked",
                resource_type="organization",
                resource_id=organization_id,
                metadata_json=json.dumps({"key_id": key_id}),
            )
        )
        session.commit()
        return key

    @app.post(
        "/v1/organizations/current/webhooks",
        response_model=WebhookEndpointRead,
        status_code=status.HTTP_201_CREATED,
        tags=["integrations"],
    )
    def create_webhook(
        payload: WebhookEndpointCreate,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> WebhookEndpoint:
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin"})
        created = WebhookEndpointRepository(session).create(
            WebhookEndpoint(
                organization_id=organization_id,
                url=payload.url,
                event_types=payload.event_types,
                secret_hash=sha256(secrets.token_urlsafe(32).encode("utf-8")).hexdigest(),
                active=True,
                created_by=actor_id,
            )
        )
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="webhook.created",
                resource_type="organization",
                resource_id=organization_id,
                metadata_json=json.dumps({"webhook_id": created.id, "url": created.url}),
            )
        )
        session.commit()
        return created

    @app.get(
        "/v1/organizations/current/webhooks",
        response_model=list[WebhookEndpointRead],
        tags=["integrations"],
    )
    def list_webhooks(
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[WebhookEndpoint]:
        require_role(session, organization_id, x_actor_id or "demo-user", {"admin"})
        return WebhookEndpointRepository(session).list_for_organization(organization_id)

    @app.post(
        "/v1/organizations/current/webhooks/{webhook_id}/toggle",
        response_model=WebhookEndpointRead,
        tags=["integrations"],
    )
    def toggle_webhook(
        webhook_id: str,
        x_actor_id: str | None = Depends(get_actor_id),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> WebhookEndpoint:
        actor_id = x_actor_id or "demo-user"
        require_role(session, organization_id, actor_id, {"admin"})
        endpoint = WebhookEndpointRepository(session).list_for_organization(organization_id)
        current = next((item for item in endpoint if item.id == webhook_id), None)
        if current is None:
            raise HTTPException(status_code=404, detail="webhook_not_found")
        updated = WebhookEndpointRepository(session).update(
            webhook_id, organization_id, active=not current.active
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="webhook_not_found")
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_id,
                action="webhook.toggled",
                resource_type="organization",
                resource_id=organization_id,
                metadata_json=json.dumps({"webhook_id": webhook_id, "active": updated.active}),
            )
        )
        session.commit()
        return updated

    @app.get("/", include_in_schema=False)
    def root(request: Request) -> dict[str, str]:
        return {"service": "clearcut-api", "docs": str(request.url) + "docs"}

    return app


app = create_app()
