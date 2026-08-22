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
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .config import settings
from .db import Database, create_database
from .models import (
    Approval,
    AuditEvent,
    ClearanceCard,
    ClearanceReport,
    Document,
    Job,
    OutreachDraft,
    Project,
    ResearchRun,
)
from .outreach import build_outreach_draft
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
    SourceRecordRead,
)
from .storage import ObjectStore, create_object_store
from .workflows import process_document_analysis, process_research_run

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

    @app.get("/healthz", tags=["system"])
    def healthz() -> dict[str, str]:
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

    @app.get("/", include_in_schema=False)
    def root(request: Request) -> dict[str, str]:
        return {"service": "clearcut-api", "docs": str(request.url) + "docs"}

    return app


app = create_app()
