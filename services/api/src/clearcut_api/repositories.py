from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Asset, Document, Job, Project, ResearchRun, SourceRecord


class ProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, project: Project) -> Project:
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def list(self, organization_id: str) -> list[Project]:
        statement = (
            select(Project)
            .where(Project.organization_id == organization_id)
            .order_by(Project.updated_at.desc())
        )
        return list(self.session.scalars(statement))

    def get(self, project_id: str, organization_id: str) -> Project | None:
        statement = select(Project).where(
            Project.id == project_id, Project.organization_id == organization_id
        )
        return self.session.scalar(statement)


class JobRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, job: Job) -> Job:
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get(self, job_id: str, organization_id: str) -> Job | None:
        statement = select(Job).where(Job.id == job_id, Job.organization_id == organization_id)
        return self.session.scalar(statement)

    def update_status(
        self, job_id: str, status: str, *, error_code: str | None = None
    ) -> Job | None:
        job = self.session.get(Job, job_id)
        if job is None:
            return None
        job.status = status
        job.error_code = error_code
        self.session.commit()
        self.session.refresh(job)
        return job


class DocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, document: Document) -> Document:
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def list(self, project_id: str, organization_id: str) -> list[Document]:
        statement = (
            select(Document)
            .where(Document.project_id == project_id, Document.organization_id == organization_id)
            .order_by(Document.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def get(self, document_id: str, organization_id: str) -> Document | None:
        statement = select(Document).where(
            Document.id == document_id, Document.organization_id == organization_id
        )
        return self.session.scalar(statement)

    def update_status(self, document_id: str, status: str) -> Document | None:
        document = self.session.get(Document, document_id)
        if document is None:
            return None
        document.status = status
        self.session.commit()
        self.session.refresh(document)
        return document


class AssetRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_many(self, assets: list[Asset]) -> list[Asset]:
        self.session.add_all(assets)
        self.session.commit()
        for asset in assets:
            self.session.refresh(asset)
        return assets

    def list_for_project(self, project_id: str, organization_id: str) -> list[Asset]:
        statement = (
            select(Asset)
            .where(Asset.project_id == project_id, Asset.organization_id == organization_id)
            .order_by(Asset.created_at.asc())
        )
        return list(self.session.scalars(statement))

    def get(self, asset_id: str, organization_id: str) -> Asset | None:
        statement = select(Asset).where(
            Asset.id == asset_id, Asset.organization_id == organization_id
        )
        return self.session.scalar(statement)


class ResearchRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, run: ResearchRun) -> ResearchRun:
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def get(self, run_id: str, organization_id: str) -> ResearchRun | None:
        statement = select(ResearchRun).where(
            ResearchRun.id == run_id, ResearchRun.organization_id == organization_id
        )
        return self.session.scalar(statement)

    def update(self, run_id: str, **values: str | None) -> ResearchRun | None:
        run = self.session.get(ResearchRun, run_id)
        if run is None:
            return None
        for key, value in values.items():
            setattr(run, key, value)
        self.session.commit()
        self.session.refresh(run)
        return run

    def add_sources(self, sources: list[SourceRecord]) -> list[SourceRecord]:
        self.session.add_all(sources)
        self.session.commit()
        for source in sources:
            self.session.refresh(source)
        return sources

    def list_sources(self, run_id: str) -> list[SourceRecord]:
        statement = (
            select(SourceRecord)
            .where(SourceRecord.research_run_id == run_id)
            .order_by(SourceRecord.retrieved_at.asc())
        )
        return list(self.session.scalars(statement))
