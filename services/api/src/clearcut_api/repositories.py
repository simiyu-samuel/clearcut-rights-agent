from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Job, Project


class ProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, project: Project) -> Project:
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def list(self, organization_id: str) -> list[Project]:
        statement = select(Project).where(Project.organization_id == organization_id).order_by(Project.updated_at.desc())
        return list(self.session.scalars(statement))

    def get(self, project_id: str, organization_id: str) -> Project | None:
        statement = select(Project).where(Project.id == project_id, Project.organization_id == organization_id)
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
