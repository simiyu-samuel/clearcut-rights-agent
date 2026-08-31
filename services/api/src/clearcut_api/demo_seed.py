"""Idempotent data for the public ClearCut judge account.

The demo workspace is intentionally separate from normal organizations. It gives a
judge a useful first session without making demo headers or an untrusted client a
production authentication mechanism.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import AuthenticatedIdentity
from .config import Settings
from .extraction import extract_candidate_assets
from .models import (
    Asset,
    AuditEvent,
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
from .reporting import build_clearance_report
from .storage import ObjectStore

DEMO_ORG_SLUG = "clearcut-demo-studio"
DEMO_PROJECT_ID = "clearcut-demo-project"
DEMO_DOCUMENT_ID = "clearcut-demo-document"
DEMO_REPORT_ID = "clearcut-demo-report-v1"

DEMO_SCRIPT = """# The Last Signal

> Synthetic demo screenplay for ClearCut. All creative works, places, and organizations in this fixture are fictional.

## Scene 04 — The night bus

Mara waits under a flickering sign while a radio plays **Neon Afterglow** from a nearby shop. She checks the **Harbor Light Café** menu through the glass.

## Scene 06 — The old station

The crew meets outside the **Old Railway Station**. A faded poster, **The Blue Hour**, hangs on the wall behind them.

## Scene 11 — The final transmission

Jonah says that the **National Falcons** won again, then folds the newspaper and looks toward the platform.
"""


def _now() -> datetime:
    return datetime.now(UTC)


def _actor_membership_id(organization_id: str, actor_id: str) -> str:
    return f"demo-member-{sha256(f'{organization_id}:{actor_id}'.encode()).hexdigest()[:24]}"


def _actor_notification_id(actor_id: str) -> str:
    return f"demo-notify-{sha256(actor_id.encode()).hexdigest()[:24]}"


def _ensure_static_membership(
    session: Session,
    *,
    organization_id: str,
    actor_id: str,
    display_name: str,
    role: str,
) -> None:
    existing = session.scalar(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.actor_id == actor_id,
            Membership.status == "active",
        )
    )
    if existing is not None:
        return
    session.add(
        Membership(
            id=_actor_membership_id(organization_id, actor_id),
            organization_id=organization_id,
            actor_id=actor_id,
            display_name=display_name,
            role=role,
            status="active",
        )
    )


def _ensure_seeded_research(
    session: Session,
    *,
    organization_id: str,
    asset: Asset,
    card_id: str,
    run_id: str,
    session_id: str,
    risk_score: int,
    summary: str,
    recommendation: str,
    reason_codes: list[str],
    sources: list[tuple[str, str, str, str]],
) -> None:
    run = session.get(ResearchRun, run_id)
    if run is None:
        run = ResearchRun(
            id=run_id,
            organization_id=organization_id,
            asset_id=asset.id,
            provider="parallel",
            operation="multi_angle_search",
            objective=f'Build an evidence-backed clearance plan for "{asset.canonical_name}".',
            query=f"{asset.canonical_name} {asset.category} rights clearance",
            status="completed",
            provider_request_id=f"parallel-demo-{asset.id}",
        )
        session.add(run)

    research_session = session.get(ResearchSession, session_id)
    if research_session is None:
        research_session = ResearchSession(
            id=session_id,
            organization_id=organization_id,
            asset_id=asset.id,
            provider="parallel",
            objective=f'Four-angle research snapshot for "{asset.canonical_name}".',
            status="completed",
            total_tasks=4,
            completed_tasks=4,
            findings=[
                {
                    "code": "human_rights_verification_required",
                    "kind": "next_step",
                    "severity": "low",
                    "title": "Human verification required",
                    "detail": "Research evidence informs workflow triage but does not establish legal clearance.",
                    "action": "Have a producer or legal reviewer confirm the next rights action.",
                }
            ],
        )
        session.add(research_session)

    angles = [
        ("rights_owner", "Owner & control"),
        ("licensing_path", "Licensing path"),
        ("territory_scope", "Territory & usage"),
        ("conflicts_and_exclusions", "Conflicts & exclusions"),
    ]
    for index, (angle, title) in enumerate(angles):
        task_id = f"{session_id.removeprefix('clearcut-demo-session-')}-{angle}"
        task = session.get(ResearchTask, task_id)
        if task is None:
            task = ResearchTask(
                id=task_id,
                organization_id=organization_id,
                session_id=session_id,
                research_run_id=run_id,
                angle=angle,
                title=title,
                objective=f"Review the {title.lower()} for {asset.canonical_name}.",
                query=f"{asset.canonical_name} {angle.replace('_', ' ')} rights",
                status="completed",
                source_count=0,
                quality_tier="demo_snapshot",
                gap_codes=["human_rights_verification_required"],
                findings=[
                    {
                        "code": "demo_snapshot",
                        "kind": "quality",
                        "severity": "low",
                        "title": "Judge workspace snapshot",
                        "detail": "This populated workspace uses a reproducible research snapshot so the workflow is immediately reviewable.",
                        "action": "Run fresh Parallel research before relying on this finding in production.",
                    }
                ],
            )
            session.add(task)
        if index < len(sources):
            source_url, source_title, excerpt, quality = sources[index]
            source_id = f"{task_id}-source"
            if session.get(SourceRecord, source_id) is None:
                session.add(
                    SourceRecord(
                        id=source_id,
                        research_run_id=run_id,
                        task_id=task_id,
                        url=source_url,
                        title=source_title,
                        excerpt=excerpt,
                        source_quality=quality,
                        provider_session_id=f"parallel-demo-session-{asset.id}",
                    )
                )
            task.source_count = 1

    if session.get(ClearanceCard, card_id) is None:
        session.add(
            ClearanceCard(
                id=card_id,
                organization_id=organization_id,
                asset_id=asset.id,
                research_run_id=run_id,
                generated_by="demo_seed",
                model_name="Gemini on Vertex AI · judge snapshot",
                status="pending_review",
                risk_score=risk_score,
                confidence_score=0.94,
                summary=summary,
                recommendation=recommendation,
                reason_codes=reason_codes,
                evidence_count=len(sources),
                needs_human_review=True,
            )
        )


def ensure_demo_workspace(
    session: Session,
    storage: ObjectStore,
    settings: Settings,
    identity: AuthenticatedIdentity,
) -> None:
    """Create the isolated demo workspace and its records once, then reuse them."""

    organization_id = settings.demo_access_organization_id
    now = _now()
    organization = session.get(Organization, organization_id)
    if organization is None:
        organization = Organization(
            id=organization_id,
            name=settings.demo_access_organization_name,
            slug=DEMO_ORG_SLUG,
        )
        session.add(organization)
    elif organization.name != settings.demo_access_organization_name:
        organization.name = settings.demo_access_organization_name

    _ensure_static_membership(
        session,
        organization_id=organization_id,
        actor_id=identity.actor_id,
        display_name="Hackathon Judge",
        role=settings.demo_access_role,
    )
    _ensure_static_membership(
        session,
        organization_id=organization_id,
        actor_id="demo-legal-reviewer",
        display_name="Legal Reviewer",
        role="legal_reviewer",
    )

    project = session.get(Project, DEMO_PROJECT_ID)
    if project is None:
        project = Project(
            id=DEMO_PROJECT_ID,
            organization_id=organization_id,
            title="The Last Signal",
            project_type="Feature film",
            territories=["Kenya", "United Kingdom", "United States"],
            distribution_modes=["Streaming", "Theatrical"],
            target_release_at=now + timedelta(days=79),
            status="review",
        )
        session.add(project)

    script_bytes = DEMO_SCRIPT.encode("utf-8")
    script_key = f"{organization_id}/{DEMO_PROJECT_ID}/{DEMO_DOCUMENT_ID}.source"
    storage.save_bytes(script_key, script_bytes)
    document = session.get(Document, DEMO_DOCUMENT_ID)
    if document is None:
        document = Document(
            id=DEMO_DOCUMENT_ID,
            organization_id=organization_id,
            project_id=DEMO_PROJECT_ID,
            original_filename="the-last-signal.md",
            mime_type="text/markdown",
            size_bytes=len(script_bytes),
            sha256=sha256(script_bytes).hexdigest(),
            object_key=script_key,
            extracted_text=DEMO_SCRIPT,
            source_kind="document",
            media_metadata={},
            version_number=1,
            status="analyzed",
        )
        session.add(document)

    candidates = {item.canonical_name: item for item in extract_candidate_assets(DEMO_SCRIPT)}
    asset_order = [
        "Neon Afterglow",
        "Harbor Light Café",
        "Old Railway Station",
        "The Blue Hour",
        "National Falcons",
    ]
    assets: dict[str, Asset] = {}
    for index, name in enumerate(asset_order):
        candidate = candidates[name]
        asset_id = f"clearcut-demo-asset-{index + 1}"
        asset = session.get(Asset, asset_id)
        if asset is None:
            asset = Asset(
                id=asset_id,
                organization_id=organization_id,
                project_id=DEMO_PROJECT_ID,
                document_id=DEMO_DOCUMENT_ID,
                canonical_name=candidate.canonical_name,
                category=candidate.category,
                context=candidate.context,
                scene_reference=candidate.scene_reference,
                source_start=candidate.source_start,
                source_end=candidate.source_end,
                extraction_confidence=candidate.extraction_confidence,
                risk_status=candidate.risk_status,
                reason_codes=candidate.reason_codes,
                priority="high" if candidate.category == "music" else "medium",
                owner_id=identity.actor_id,
                due_at=now + timedelta(days=14 + index),
                next_action=(
                    "Confirm sync and master rights"
                    if candidate.category == "music"
                    else "Research ownership and permission path"
                ),
            )
            session.add(asset)
        assets[name] = asset

    _ensure_seeded_research(
        session,
        organization_id=organization_id,
        asset=assets["Neon Afterglow"],
        card_id="clearcut-demo-card-1",
        run_id="clearcut-demo-run-1",
        session_id="clearcut-demo-session-1",
        risk_score=90,
        summary="Commercial music is identified in the scene. Composition and master rights require confirmation before distribution.",
        recommendation="Request a synchronization and master-use license covering the planned territories, term, media, and scene usage.",
        reason_codes=[
            "copyrighted_music_signal",
            "sync_license_required",
            "master_use_license_required",
        ],
        sources=[
            (
                "https://www.copyright.gov/",
                "U.S. Copyright Office",
                "Public copyright reference for the judge snapshot; verify the specific composition and recording owners.",
                "demo_snapshot",
            ),
        ],
    )
    _ensure_seeded_research(
        session,
        organization_id=organization_id,
        asset=assets["Harbor Light Café"],
        card_id="clearcut-demo-card-2",
        run_id="clearcut-demo-run-2",
        session_id="clearcut-demo-session-2",
        risk_score=62,
        summary="A recognizable café brand appears in the scene. The production should confirm filming, trademark, and implied-endorsement permissions.",
        recommendation="Confirm the location release and obtain brand approval or replace the visible mark before final delivery.",
        reason_codes=[
            "commercial_brand_signal",
            "trademark_review_required",
            "location_permission_signal",
        ],
        sources=[
            (
                "https://www.uspto.gov/trademarks",
                "U.S. Patent and Trademark Office · Trademarks",
                "Public trademark reference for the judge snapshot; confirm the relevant mark and owner for the production territory.",
                "demo_snapshot",
            ),
        ],
    )

    card = session.get(ClearanceCard, "clearcut-demo-card-1")
    if card is not None and session.get(OutreachDraft, "clearcut-demo-outreach-1") is None:
        session.add(
            OutreachDraft(
                id="clearcut-demo-outreach-1",
                organization_id=organization_id,
                asset_id=assets["Neon Afterglow"].id,
                clearance_card_id=card.id,
                recipient_hint="Music publisher / master rights representative",
                subject="Permission request · Neon Afterglow · The Last Signal",
                body="Hello,\n\nWe are preparing a feature film and would like to confirm availability and terms for the composition and master recording referenced as Neon Afterglow. Please share the appropriate rights-holder and licensing contact.\n\nThank you,\nClearCut production team",
                terms={
                    "territories": "Kenya, United Kingdom, United States",
                    "media": "Streaming and theatrical",
                    "term": "Per production release schedule",
                    "usage": "Background radio use in Scene 04",
                },
                due_at=now + timedelta(days=14),
                status="draft",
                generated_by="demo_seed",
                created_by=identity.actor_id,
            )
        )

    audit_events = [
        ("clearcut-demo-audit-1", "project.created", "project", DEMO_PROJECT_ID),
        ("clearcut-demo-audit-2", "document.analyzed", "document", DEMO_DOCUMENT_ID),
        ("clearcut-demo-audit-3", "research.completed", "research_run", "clearcut-demo-run-1"),
        ("clearcut-demo-audit-4", "report.ready", "clearance_report", DEMO_REPORT_ID),
    ]
    for event_id, action, resource_type, resource_id in audit_events:
        if session.get(AuditEvent, event_id) is None:
            session.add(
                AuditEvent(
                    id=event_id,
                    organization_id=organization_id,
                    actor_type="system",
                    actor_id=identity.actor_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    metadata_json=json.dumps({"source": "judge_demo_snapshot"}),
                )
            )

    notification_id = _actor_notification_id(identity.actor_id)
    if session.get(Notification, notification_id) is None:
        session.add(
            Notification(
                id=notification_id,
                organization_id=organization_id,
                actor_id=identity.actor_id,
                notification_type="demo_workspace_ready",
                title="Your demo workspace is ready",
                body="The Last Signal is populated with research, review cards, evidence, and a permission draft.",
                resource_type="project",
                resource_id=DEMO_PROJECT_ID,
            )
        )

    session.flush()
    seeded_assets = list(
        session.scalars(
            select(Asset).where(
                Asset.organization_id == organization_id,
                Asset.project_id == DEMO_PROJECT_ID,
            )
        )
    )
    seeded_cards = list(
        session.scalars(
            select(ClearanceCard).where(ClearanceCard.organization_id == organization_id)
        )
    )
    run_ids = {card.research_run_id for card in seeded_cards}
    seeded_sources = (
        list(session.scalars(select(SourceRecord).where(SourceRecord.research_run_id.in_(run_ids))))
        if run_ids
        else []
    )
    seeded_report = session.get(ClearanceReport, DEMO_REPORT_ID)
    if seeded_report is None:
        content = build_clearance_report(
            project,
            sorted(seeded_assets, key=lambda item: item.id),
            sorted(seeded_cards, key=lambda item: item.id),
            seeded_sources,
            report_version=1,
            policy_version="risk-policy-v1-demo",
            drafts=[
                draft
                for draft in session.scalars(
                    select(OutreachDraft).where(OutreachDraft.organization_id == organization_id)
                )
            ],
        )
        session.add(
            ClearanceReport(
                id=DEMO_REPORT_ID,
                organization_id=organization_id,
                project_id=DEMO_PROJECT_ID,
                report_type="clearance_summary",
                status="ready",
                generated_by="demo_seed",
                content_markdown=content,
                version_number=1,
                content_hash=sha256(content.encode("utf-8")).hexdigest(),
                policy_version="risk-policy-v1-demo",
                source_snapshot_at=now,
            )
        )

    session.commit()
