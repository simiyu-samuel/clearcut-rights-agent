from dataclasses import replace

from sqlalchemy import func, select

from clearcut_api.auth import AuthenticatedIdentity
from clearcut_api.config import settings
from clearcut_api.demo_seed import (
    DEMO_DOCUMENT_ID,
    DEMO_ORG_SLUG,
    DEMO_PROJECT_ID,
    ensure_demo_workspace,
)
from clearcut_api.models import (
    Asset,
    ClearanceCard,
    ClearanceReport,
    Document,
    Membership,
    Notification,
    Organization,
    OutreachDraft,
    Project,
    ResearchRun,
    ResearchSession,
    ResearchTask,
    SourceRecord,
)
from clearcut_api.storage import LocalObjectStore

from .test_api import make_database


def test_judge_workspace_is_populated_and_idempotent(tmp_path) -> None:
    database = make_database()
    storage = LocalObjectStore(str(tmp_path))
    demo_settings = replace(
        settings,
        demo_access_enabled=True,
        demo_access_email="demo@clearcut.app",
        demo_access_organization_id="clearcut-demo-org",
        demo_access_organization_name="DEMO",
        demo_access_role="producer",
    )
    identity = AuthenticatedIdentity(
        actor_id="firebase-judge-actor",
        email="demo@clearcut.app",
        display_name="Hackathon Judge",
        claims={},
    )

    with database.session_factory() as session:
        ensure_demo_workspace(session, storage, demo_settings, identity)

    with database.session_factory() as session:
        assert session.get(Organization, "clearcut-demo-org").slug == DEMO_ORG_SLUG
        assert session.get(Project, DEMO_PROJECT_ID).title == "The Last Signal"
        assert session.get(Document, DEMO_DOCUMENT_ID).status == "analyzed"
        assert session.scalar(select(func.count()).select_from(Asset)) == 5
        assert session.scalar(select(func.count()).select_from(ClearanceCard)) == 2
        assert session.scalar(select(func.count()).select_from(ResearchRun)) == 2
        assert session.scalar(select(func.count()).select_from(ResearchSession)) == 2
        assert session.scalar(select(func.count()).select_from(ResearchTask)) == 8
        assert session.scalar(select(func.count()).select_from(SourceRecord)) == 2
        assert session.scalar(select(func.count()).select_from(ClearanceReport)) == 1
        assert session.scalar(select(func.count()).select_from(OutreachDraft)) == 1
        assert session.scalar(select(func.count()).select_from(Notification)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(Membership)
                .where(Membership.actor_id == identity.actor_id)
            )
            == 1
        )

    with database.session_factory() as session:
        ensure_demo_workspace(session, storage, demo_settings, identity)

    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Asset)) == 5
        assert session.scalar(select(func.count()).select_from(ClearanceCard)) == 2
        assert session.scalar(select(func.count()).select_from(ClearanceReport)) == 1
        assert session.scalar(select(func.count()).select_from(OutreachDraft)) == 1
        assert session.scalar(select(func.count()).select_from(Notification)) == 1
