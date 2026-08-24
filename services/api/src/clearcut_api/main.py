import json
from contextlib import asynccontextmanager
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

from .config import settings
from .db import Database, create_database
from .models import (
    Approval,
    Asset,
    AuditEvent,
    ClearanceCard,
    ClearanceReport,
    Document,
    Job,
    OutreachDraft,
    Project,
    ResearchRun,
    ResearchSession,
    ResearchTask,
    SourceRecord,
)
from .outreach import build_outreach_draft
from .pdf import build_pdf
from .reporting import build_clearance_report
from .repositories import (
    ApprovalRepository,
    AssetRepository,
    ClearanceCardRepository,
    ClearanceReportRepository,
    DocumentRepository,
    JobRepository,
    OutreachDraftRepository,
    ProjectRepository,
    ResearchRunRepository,
    ResearchSessionRepository,
    ResearchTaskRepository,
)
from .schemas import (
    AnalysisRunCreate,
    ApprovalCreate,
    ApprovalRead,
    AssetRead,
    ClearanceCardRead,
    ClearanceReportRead,
    DocumentRead,
    JobRead,
    OutreachDraftCreate,
    OutreachDraftRead,
    ProjectCreate,
    ProjectRead,
    ResearchRunCreate,
    ResearchRunRead,
    ResearchSessionCreate,
    ResearchSessionRead,
    SourceRecordRead,
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

    def get_db():
        with db.session_factory() as session:
            yield session

    def get_organization_id(x_organization_id: str | None = Header(default=None)) -> str:
        return x_organization_id or settings.default_organization_id

    def require_project(session: Session, project_id: str, organization_id: str) -> Project:
        project = ProjectRepository(session).get(project_id, organization_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project_not_found")
        return project

    def research_session_payload(
        research_session: ResearchSession, tasks: list[ResearchTask]
    ) -> dict[str, object]:
        return {
            "id": research_session.id,
            "organization_id": research_session.organization_id,
            "asset_id": research_session.asset_id,
            "provider": research_session.provider,
            "objective": research_session.objective,
            "status": research_session.status,
            "total_tasks": research_session.total_tasks,
            "completed_tasks": research_session.completed_tasks,
            "created_at": research_session.created_at,
            "updated_at": research_session.updated_at,
            "tasks": tasks,
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

    @app.post(
        "/v1/projects",
        response_model=ProjectRead,
        status_code=status.HTTP_201_CREATED,
        tags=["projects"],
    )
    def create_project(
        payload: ProjectCreate,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Project:
        project = Project(organization_id=organization_id, **payload.model_dump())
        return ProjectRepository(session).create(project)

    @app.get("/v1/projects", response_model=list[ProjectRead], tags=["projects"])
    def list_projects(
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> list[Project]:
        return ProjectRepository(session).list(organization_id)

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
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Document:
        require_project(session, project_id, organization_id)
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
        )
        return DocumentRepository(session).create(document)

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

    @app.get("/v1/projects/{project_id}/assets", response_model=list[AssetRead], tags=["assets"])
    def list_assets(
        project_id: str,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ):
        require_project(session, project_id, organization_id)
        return AssetRepository(session).list_for_project(project_id, organization_id)

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
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Job:
        require_project(session, project_id, organization_id)
        if payload.document_id is not None:
            document = DocumentRepository(session).get(payload.document_id, organization_id)
            if document is None or document.project_id != project_id:
                raise HTTPException(status_code=404, detail="document_not_found")
        job = Job(
            organization_id=organization_id,
            project_id=project_id,
            job_type="document_analysis",
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
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
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
        return [
            research_session_payload(
                research_session, tasks.list_for_session(research_session.id, organization_id)
            )
            for research_session in sessions
        ]

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
        return research_session_payload(research_session, tasks)

    @app.post(
        "/v1/research-sessions/{session_id}/retry",
        response_model=ResearchSessionRead,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["research"],
    )
    def retry_research_session(
        session_id: str,
        background_tasks: BackgroundTasks,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> dict[str, object]:
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
        "/v1/assets/{asset_id}/research-runs",
        response_model=ResearchRunRead,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["research"],
    )
    def create_research_run(
        asset_id: str,
        payload: ResearchRunCreate,
        background_tasks: BackgroundTasks,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> ResearchRun:
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

    @app.post(
        "/v1/assets/{asset_id}/approvals",
        response_model=ApprovalRead,
        status_code=status.HTTP_201_CREATED,
        tags=["review"],
    )
    def record_approval(
        asset_id: str,
        payload: ApprovalCreate,
        x_actor_id: str | None = Header(default=None),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Approval:
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
        latest_approval = ApprovalRepository(session).get_latest_for_card(card.id, organization_id)
        approval = Approval(
            organization_id=organization_id,
            asset_id=asset_id,
            clearance_card_id=card.id,
            decision=payload.decision,
            note=payload.note,
            actor_id=x_actor_id or "demo-user",
            supersedes_id=latest_approval.id if latest_approval else None,
        )
        card.status = card_status
        card.needs_human_review = needs_human_review
        asset.risk_status = risk_status
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
        x_actor_id: str | None = Header(default=None),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> OutreachDraft:
        asset = AssetRepository(session).get(asset_id, organization_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="asset_not_found")
        card = ClearanceCardRepository(session).get_for_asset(asset_id, organization_id)
        if card is None:
            raise HTTPException(status_code=404, detail="clearance_card_not_found")
        project = require_project(session, asset.project_id, organization_id)
        subject, body = build_outreach_draft(project, asset, card, payload.recipient_hint)
        actor_id = x_actor_id or "demo-user"
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

    @app.post(
        "/v1/projects/{project_id}/reports",
        response_model=ClearanceReportRead,
        status_code=status.HTTP_201_CREATED,
        tags=["reports"],
    )
    def create_report(
        project_id: str,
        x_actor_id: str | None = Header(default=None),
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> ClearanceReport:
        project = require_project(session, project_id, organization_id)
        assets = AssetRepository(session).list_for_project(project_id, organization_id)
        cards = ClearanceCardRepository(session).list_for_project(project_id, organization_id)
        sources: list = []
        runs = ResearchRunRepository(session)
        for card in cards:
            sources.extend(runs.list_sources(card.research_run_id))
        report = ClearanceReport(
            organization_id=organization_id,
            project_id=project_id,
            report_type="clearance_summary",
            status="ready",
            generated_by="clearcut_report_builder",
            content_markdown=build_clearance_report(project, assets, cards, sources),
        )
        session.add(report)
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=x_actor_id or "demo-user",
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
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Response:
        require_project(session, project_id, organization_id)
        report = ClearanceReportRepository(session).get(report_id, project_id, organization_id)
        if report is None:
            raise HTTPException(status_code=404, detail="report_not_found")
        filename = f"clearcut-{project_id}-report.pdf"
        return Response(
            content=build_pdf(report.content_markdown),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/", include_in_schema=False)
    def root(request: Request) -> dict[str, str]:
        return {"service": "clearcut-api", "docs": str(request.url) + "docs"}

    return app


app = create_app()
