from contextlib import asynccontextmanager
import json

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import settings
from .db import Database, create_database
from .models import Job, Project
from .repositories import JobRepository, ProjectRepository
from .schemas import AnalysisRunCreate, JobRead, ProjectCreate, ProjectRead


def create_app(database: Database | None = None) -> FastAPI:
    db = database or create_database(settings.database_url)

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

    def get_db():
        with db.session_factory() as session:
            yield session

    def get_organization_id(x_organization_id: str | None = Header(default=None)) -> str:
        return x_organization_id or settings.default_organization_id

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

    @app.post("/v1/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED, tags=["projects"])
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
        project = ProjectRepository(session).get(project_id, organization_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project_not_found")
        return project

    @app.post("/v1/projects/{project_id}/analysis-runs", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED, tags=["analysis"])
    def create_analysis_run(
        project_id: str,
        payload: AnalysisRunCreate,
        session: Session = Depends(get_db),
        organization_id: str = Depends(get_organization_id),
    ) -> Job:
        project = ProjectRepository(session).get(project_id, organization_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project_not_found")
        job = Job(
            organization_id=organization_id,
            project_id=project_id,
            job_type="document_analysis",
            status="queued",
            metadata_json=json.dumps({"document_id": payload.document_id}),
        )
        return JobRepository(session).create(job)

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

    @app.get("/", include_in_schema=False)
    def root(request: Request) -> dict[str, str]:
        return {"service": "clearcut-api", "docs": str(request.url) + "docs"}

    return app


app = create_app()
