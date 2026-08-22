from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from clearcut_api.db import Database
from clearcut_api.main import create_app
from clearcut_api.models import Base, Job, Project
from clearcut_api.repositories import JobRepository, ProjectRepository


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
    assert {"/healthz", "/readyz", "/openapi.json"}.issubset(routes)
    assert app.title == "ClearCut API"


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
