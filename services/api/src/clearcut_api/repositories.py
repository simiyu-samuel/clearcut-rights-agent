from sqlalchemy import select
from sqlalchemy.orm import Session

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


class OrganizationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, organization_id: str) -> Organization | None:
        return self.session.get(Organization, organization_id)

    def create(self, organization: Organization) -> Organization:
        self.session.add(organization)
        self.session.commit()
        self.session.refresh(organization)
        return organization


class MembershipRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, organization_id: str, actor_id: str) -> Membership | None:
        statement = select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.actor_id == actor_id,
            Membership.status == "active",
        )
        return self.session.scalar(statement)

    def list_for_actor(self, actor_id: str) -> list[Membership]:
        statement = (
            select(Membership)
            .where(Membership.actor_id == actor_id, Membership.status == "active")
            .order_by(Membership.created_at.asc())
        )
        return list(self.session.scalars(statement))

    def list_for_organization(self, organization_id: str) -> list[Membership]:
        statement = (
            select(Membership)
            .where(Membership.organization_id == organization_id)
            .order_by(Membership.display_name.asc())
        )
        return list(self.session.scalars(statement))

    def create(self, membership: Membership) -> Membership:
        self.session.add(membership)
        self.session.commit()
        self.session.refresh(membership)
        return membership


class OrganizationInvitationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, invitation_id: str, organization_id: str) -> OrganizationInvitation | None:
        statement = select(OrganizationInvitation).where(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == organization_id,
        )
        return self.session.scalar(statement)

    def list_for_organization(self, organization_id: str) -> list[OrganizationInvitation]:
        statement = (
            select(OrganizationInvitation)
            .where(OrganizationInvitation.organization_id == organization_id)
            .order_by(OrganizationInvitation.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def list_pending_for_email(self, email: str) -> list[OrganizationInvitation]:
        statement = (
            select(OrganizationInvitation)
            .where(
                OrganizationInvitation.email == email,
                OrganizationInvitation.status == "pending",
            )
            .order_by(OrganizationInvitation.created_at.asc())
        )
        return list(self.session.scalars(statement))

    def pending_for_email(
        self, organization_id: str, email: str
    ) -> OrganizationInvitation | None:
        statement = (
            select(OrganizationInvitation)
            .where(
                OrganizationInvitation.organization_id == organization_id,
                OrganizationInvitation.email == email,
                OrganizationInvitation.status == "pending",
            )
            .order_by(OrganizationInvitation.created_at.desc())
        )
        return self.session.scalar(statement)

    def create(self, invitation: OrganizationInvitation) -> OrganizationInvitation:
        self.session.add(invitation)
        self.session.commit()
        self.session.refresh(invitation)
        return invitation


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

    def update(self, project_id: str, organization_id: str, **values: object) -> Project | None:
        project = self.get(project_id, organization_id)
        if project is None:
            return None
        for key, value in values.items():
            setattr(project, key, value)
        self.session.commit()
        self.session.refresh(project)
        return project

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

    def latest_for_project(self, project_id: str, organization_id: str) -> Document | None:
        statement = (
            select(Document)
            .where(Document.project_id == project_id, Document.organization_id == organization_id)
            .order_by(Document.version_number.desc(), Document.created_at.desc())
        )
        return self.session.scalars(statement).first()

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

    def update(self, asset_id: str, organization_id: str, **values: object) -> Asset | None:
        asset = self.get(asset_id, organization_id)
        if asset is None:
            return None
        for key, value in values.items():
            setattr(asset, key, value)
        self.session.commit()
        self.session.refresh(asset)
        return asset


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

    def list_for_asset(self, asset_id: str, organization_id: str) -> list[Approval]:
        statement = (
            select(Approval)
            .where(
                Approval.asset_id == asset_id,
                Approval.organization_id == organization_id,
            )
            .order_by(Approval.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def list_for_project(self, project_id: str, organization_id: str) -> list[Approval]:
        statement = (
            select(Approval)
            .join(Asset, Asset.id == Approval.asset_id)
            .where(
                Asset.project_id == project_id,
                Asset.organization_id == organization_id,
                Approval.organization_id == organization_id,
            )
            .order_by(Approval.created_at.desc())
        )
        return list(self.session.scalars(statement))


class AuditRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, event: AuditEvent) -> AuditEvent:
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def list_for_organization(self, organization_id: str, limit: int = 100) -> list[AuditEvent]:
        statement = (
            select(AuditEvent)
            .where(AuditEvent.organization_id == organization_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_for_project(
        self, project_id: str, organization_id: str, limit: int = 100
    ) -> list[AuditEvent]:
        resource_ids = set(
            self.session.scalars(
                select(Asset.id).where(
                    Asset.project_id == project_id, Asset.organization_id == organization_id
                )
            )
        )
        resource_ids.add(project_id)
        if not resource_ids:
            return []
        statement = (
            select(AuditEvent)
            .where(
                AuditEvent.organization_id == organization_id,
                AuditEvent.resource_id.in_(resource_ids),
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))


class ResearchRecheckRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_for_asset(self, asset_id: str, organization_id: str) -> ResearchRecheck | None:
        statement = (
            select(ResearchRecheck)
            .where(
                ResearchRecheck.asset_id == asset_id,
                ResearchRecheck.organization_id == organization_id,
            )
            .order_by(ResearchRecheck.created_at.desc())
        )
        return self.session.scalars(statement).first()

    def list_for_project(self, project_id: str, organization_id: str) -> list[ResearchRecheck]:
        statement = (
            select(ResearchRecheck)
            .join(Asset, Asset.id == ResearchRecheck.asset_id)
            .where(
                Asset.project_id == project_id,
                Asset.organization_id == organization_id,
                ResearchRecheck.organization_id == organization_id,
            )
            .order_by(ResearchRecheck.next_run_at.asc())
        )
        return list(self.session.scalars(statement))

    def create(self, recheck: ResearchRecheck) -> ResearchRecheck:
        self.session.add(recheck)
        self.session.commit()
        self.session.refresh(recheck)
        return recheck

    def update(self, recheck_id: str, organization_id: str, **values: object) -> ResearchRecheck | None:
        recheck = self.session.scalar(
            select(ResearchRecheck).where(
                ResearchRecheck.id == recheck_id,
                ResearchRecheck.organization_id == organization_id,
            )
        )
        if recheck is None:
            return None
        for key, value in values.items():
            setattr(recheck, key, value)
        self.session.commit()
        self.session.refresh(recheck)
        return recheck


class AssetCommentRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_for_asset(self, asset_id: str, organization_id: str) -> list[AssetComment]:
        statement = (
            select(AssetComment)
            .where(
                AssetComment.asset_id == asset_id,
                AssetComment.organization_id == organization_id,
            )
            .order_by(AssetComment.created_at.asc())
        )
        return list(self.session.scalars(statement))

    def create(self, comment: AssetComment) -> AssetComment:
        self.session.add(comment)
        self.session.commit()
        self.session.refresh(comment)
        return comment


class NotificationRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_for_actor(self, organization_id: str, actor_id: str) -> list[Notification]:
        statement = (
            select(Notification)
            .where(Notification.organization_id == organization_id, Notification.actor_id == actor_id)
            .order_by(Notification.created_at.desc())
            .limit(100)
        )
        return list(self.session.scalars(statement))

    def create(self, notification: Notification) -> Notification:
        self.session.add(notification)
        self.session.commit()
        self.session.refresh(notification)
        return notification

    def mark_read(self, notification_id: str, organization_id: str, actor_id: str) -> Notification | None:
        notification = self.session.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.organization_id == organization_id,
                Notification.actor_id == actor_id,
            )
        )
        if notification is None:
            return None
        from .models import utc_now

        notification.read_at = utc_now()
        self.session.commit()
        self.session.refresh(notification)
        return notification


class OutreachDraftRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, draft: OutreachDraft) -> OutreachDraft:
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)
        return draft

    def get(self, draft_id: str, organization_id: str) -> OutreachDraft | None:
        return self.session.scalar(
            select(OutreachDraft).where(
                OutreachDraft.id == draft_id,
                OutreachDraft.organization_id == organization_id,
            )
        )

    def update(self, draft_id: str, organization_id: str, **values: object) -> OutreachDraft | None:
        draft = self.get(draft_id, organization_id)
        if draft is None:
            return None
        for key, value in values.items():
            setattr(draft, key, value)
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


class ProjectAttachmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_for_project(self, project_id: str, organization_id: str) -> list[ProjectAttachment]:
        statement = (
            select(ProjectAttachment)
            .where(
                ProjectAttachment.project_id == project_id,
                ProjectAttachment.organization_id == organization_id,
            )
            .order_by(ProjectAttachment.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def create(self, attachment: ProjectAttachment) -> ProjectAttachment:
        self.session.add(attachment)
        self.session.commit()
        self.session.refresh(attachment)
        return attachment


class ReviewShareRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_for_project(self, project_id: str, organization_id: str) -> list[ReviewShare]:
        statement = (
            select(ReviewShare)
            .where(
                ReviewShare.project_id == project_id,
                ReviewShare.organization_id == organization_id,
            )
            .order_by(ReviewShare.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def get_by_hash(self, token_hash: str) -> ReviewShare | None:
        return self.session.scalar(select(ReviewShare).where(ReviewShare.token_hash == token_hash))

    def create(self, share: ReviewShare) -> ReviewShare:
        self.session.add(share)
        self.session.commit()
        self.session.refresh(share)
        return share

    def revoke(self, share_id: str, organization_id: str) -> ReviewShare | None:
        share = self.session.scalar(
            select(ReviewShare).where(
                ReviewShare.id == share_id,
                ReviewShare.organization_id == organization_id,
            )
        )
        if share is None:
            return None
        from .models import utc_now

        share.revoked_at = utc_now()
        self.session.commit()
        self.session.refresh(share)
        return share


class ApiKeyRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_for_organization(self, organization_id: str) -> list[ApiKey]:
        statement = (
            select(ApiKey)
            .where(ApiKey.organization_id == organization_id)
            .order_by(ApiKey.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def create(self, key: ApiKey) -> ApiKey:
        self.session.add(key)
        self.session.commit()
        self.session.refresh(key)
        return key

    def revoke(self, key_id: str, organization_id: str) -> ApiKey | None:
        key = self.session.scalar(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.organization_id == organization_id)
        )
        if key is None:
            return None
        from .models import utc_now

        key.revoked_at = utc_now()
        self.session.commit()
        self.session.refresh(key)
        return key


class WebhookEndpointRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_for_organization(self, organization_id: str) -> list[WebhookEndpoint]:
        statement = (
            select(WebhookEndpoint)
            .where(WebhookEndpoint.organization_id == organization_id)
            .order_by(WebhookEndpoint.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def create(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        self.session.add(endpoint)
        self.session.commit()
        self.session.refresh(endpoint)
        return endpoint

    def update(self, endpoint_id: str, organization_id: str, **values: object) -> WebhookEndpoint | None:
        endpoint = self.session.scalar(
            select(WebhookEndpoint).where(
                WebhookEndpoint.id == endpoint_id,
                WebhookEndpoint.organization_id == organization_id,
            )
        )
        if endpoint is None:
            return None
        for key, value in values.items():
            setattr(endpoint, key, value)
        self.session.commit()
        self.session.refresh(endpoint)
        return endpoint
