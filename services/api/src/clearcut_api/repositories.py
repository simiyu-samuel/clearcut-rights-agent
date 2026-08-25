from sqlalchemy import select
from sqlalchemy.orm import Session

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
        projects = list(self.session.scalars(statement))
        return [self.sync_status(project) for project in projects]

    def get(self, project_id: str, organization_id: str) -> Project | None:
        statement = select(Project).where(
            Project.id == project_id, Project.organization_id == organization_id
        )
        project = self.session.scalar(statement)
        return self.sync_status(project) if project is not None else None

    def sync_status(self, project: Project) -> Project:
        asset_ids = set(
            self.session.scalars(
                select(Asset.id).where(
                    Asset.project_id == project.id,
                    Asset.organization_id == project.organization_id,
                )
            )
        )
        cards = list(
            self.session.scalars(
                select(ClearanceCard)
                .join(Asset, Asset.id == ClearanceCard.asset_id)
                .where(
                    Asset.project_id == project.id,
                    ClearanceCard.organization_id == project.organization_id,
                )
                .order_by(ClearanceCard.created_at.desc())
            )
        )
        latest_cards: dict[str, ClearanceCard] = {}
        for card in cards:
            latest_cards.setdefault(card.asset_id, card)

        if not asset_ids:
            desired_status = "draft"
        elif len(latest_cards) < len(asset_ids):
            desired_status = "active"
        elif all(card.status == "approved" for card in latest_cards.values()):
            desired_status = "complete"
        else:
            desired_status = "review"

        if project.status != desired_status:
            project.status = desired_status
            self.session.commit()
            self.session.refresh(project)
        return project


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

    def list_sources_for_task(self, task_id: str) -> list[SourceRecord]:
        statement = (
            select(SourceRecord)
            .where(SourceRecord.task_id == task_id)
            .order_by(SourceRecord.retrieved_at.asc())
        )
        return list(self.session.scalars(statement))


class ResearchSessionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, research_session: ResearchSession) -> ResearchSession:
        self.session.add(research_session)
        self.session.commit()
        self.session.refresh(research_session)
        return research_session

    def get(self, session_id: str, organization_id: str) -> ResearchSession | None:
        statement = select(ResearchSession).where(
            ResearchSession.id == session_id,
            ResearchSession.organization_id == organization_id,
        )
        return self.session.scalar(statement)

    def list_for_asset(self, asset_id: str, organization_id: str) -> list[ResearchSession]:
        statement = (
            select(ResearchSession)
            .where(
                ResearchSession.asset_id == asset_id,
                ResearchSession.organization_id == organization_id,
            )
            .order_by(ResearchSession.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def list_for_project(self, project_id: str, organization_id: str) -> list[ResearchSession]:
        statement = (
            select(ResearchSession)
            .join(Asset, Asset.id == ResearchSession.asset_id)
            .where(
                Asset.project_id == project_id,
                ResearchSession.organization_id == organization_id,
            )
            .order_by(ResearchSession.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def update(self, session_id: str, **values: object) -> ResearchSession | None:
        research_session = self.session.get(ResearchSession, session_id)
        if research_session is None:
            return None
        for key, value in values.items():
            setattr(research_session, key, value)
        self.session.commit()
        self.session.refresh(research_session)
        return research_session


class ResearchTaskRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_many(self, tasks: list[ResearchTask]) -> list[ResearchTask]:
        self.session.add_all(tasks)
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        return tasks

    def get(self, task_id: str, organization_id: str) -> ResearchTask | None:
        statement = select(ResearchTask).where(
            ResearchTask.id == task_id,
            ResearchTask.organization_id == organization_id,
        )
        return self.session.scalar(statement)

    def list_for_session(self, session_id: str, organization_id: str) -> list[ResearchTask]:
        statement = (
            select(ResearchTask)
            .where(
                ResearchTask.session_id == session_id,
                ResearchTask.organization_id == organization_id,
            )
            .order_by(ResearchTask.created_at.asc())
        )
        return list(self.session.scalars(statement))

    def update(self, task_id: str, **values: object) -> ResearchTask | None:
        task = self.session.get(ResearchTask, task_id)
        if task is None:
            return None
        for key, value in values.items():
            setattr(task, key, value)
        self.session.commit()
        self.session.refresh(task)
        return task


class ClearanceCardRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, card: ClearanceCard) -> ClearanceCard:
        self.session.add(card)
        self.session.commit()
        self.session.refresh(card)
        return card

    def get_for_asset(self, asset_id: str, organization_id: str) -> ClearanceCard | None:
        statement = (
            select(ClearanceCard)
            .where(
                ClearanceCard.asset_id == asset_id,
                ClearanceCard.organization_id == organization_id,
            )
            .order_by(ClearanceCard.created_at.desc())
        )
        return self.session.scalars(statement).first()

    def get_for_run(self, research_run_id: str, organization_id: str) -> ClearanceCard | None:
        statement = select(ClearanceCard).where(
            ClearanceCard.research_run_id == research_run_id,
            ClearanceCard.organization_id == organization_id,
        )
        return self.session.scalars(statement).first()

    def list_for_project(self, project_id: str, organization_id: str) -> list[ClearanceCard]:
        statement = (
            select(ClearanceCard)
            .join(Asset, Asset.id == ClearanceCard.asset_id)
            .where(
                Asset.project_id == project_id,
                ClearanceCard.organization_id == organization_id,
            )
            .order_by(ClearanceCard.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def update(self, card_id: str, **values: object) -> ClearanceCard | None:
        card = self.session.get(ClearanceCard, card_id)
        if card is None:
            return None
        for key, value in values.items():
            setattr(card, key, value)
        self.session.commit()
        self.session.refresh(card)
        return card


class ApprovalRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, approval: Approval) -> Approval:
        self.session.add(approval)
        self.session.commit()
        self.session.refresh(approval)
        return approval

    def get_latest_for_card(self, clearance_card_id: str, organization_id: str) -> Approval | None:
        statement = (
            select(Approval)
            .where(
                Approval.clearance_card_id == clearance_card_id,
                Approval.organization_id == organization_id,
            )
            .order_by(Approval.created_at.desc())
        )
        return self.session.scalars(statement).first()


class AuditRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, event: AuditEvent) -> AuditEvent:
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event


class OutreachDraftRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, draft: OutreachDraft) -> OutreachDraft:
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)
        return draft

    def list_for_asset(self, asset_id: str, organization_id: str) -> list[OutreachDraft]:
        statement = (
            select(OutreachDraft)
            .where(
                OutreachDraft.asset_id == asset_id,
                OutreachDraft.organization_id == organization_id,
            )
            .order_by(OutreachDraft.created_at.desc())
        )
        return list(self.session.scalars(statement))


class ClearanceReportRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, report: ClearanceReport) -> ClearanceReport:
        self.session.add(report)
        self.session.commit()
        self.session.refresh(report)
        return report

    def get(self, report_id: str, project_id: str, organization_id: str) -> ClearanceReport | None:
        statement = select(ClearanceReport).where(
            ClearanceReport.id == report_id,
            ClearanceReport.project_id == project_id,
            ClearanceReport.organization_id == organization_id,
        )
        return self.session.scalar(statement)

    def list_for_project(self, project_id: str, organization_id: str) -> list[ClearanceReport]:
        statement = (
            select(ClearanceReport)
            .where(
                ClearanceReport.project_id == project_id,
                ClearanceReport.organization_id == organization_id,
            )
            .order_by(ClearanceReport.created_at.desc())
        )
        return list(self.session.scalars(statement))
