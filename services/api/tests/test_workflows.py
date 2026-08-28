import asyncio
from datetime import UTC, datetime

from clearcut_api.agent_runtime import FixtureClearanceAgent
from clearcut_api.agent_tools import (
    REGISTERED_AGENT_TOOLS,
    calculate_clearance_risk,
    extract_rights_source,
    request_human_approval,
    search_rights_sources,
)
from clearcut_api.config import Settings
from clearcut_api.extraction import extract_candidate_assets
from clearcut_api.media_analysis import VertexGeminiMediaAnalyzer
from clearcut_api.models import (
    Asset,
    ClearanceCard,
    Document,
    Job,
    Project,
    ResearchRun,
    ResearchSession,
    ResearchTask,
    SourceRecord,
)
from clearcut_api.outreach import build_outreach_draft
from clearcut_api.pdf import _parse_report, build_pdf
from clearcut_api.playbooks import playbook_for
from clearcut_api.providers.parallel_api import ParallelApiProvider
from clearcut_api.reporting import build_clearance_report
from clearcut_api.repositories import (
    AssetRepository,
    ClearanceCardRepository,
    DocumentRepository,
    JobRepository,
    ProjectRepository,
    ResearchRunRepository,
    ResearchSessionRepository,
    ResearchTaskRepository,
)
from clearcut_api.storage import LocalObjectStore
from clearcut_api.workflows import (
    build_research_plan,
    process_document_analysis,
    process_research_run,
    process_research_task,
)

from .test_api import make_database


def test_fixture_script_extracts_scene_aware_assets() -> None:
    text = """## Scene 04 — The night bus

        Mara waits while a radio plays **Midnight City** from the **Harbor Light Café** menu.

## Scene 06 — The old station

The crew meets outside the **Old Railway Station** beside a **The Blue Hour** photograph.
"""

    assets = extract_candidate_assets(text)
    by_name = {asset.canonical_name: asset for asset in assets}

    assert by_name["Midnight City"].category == "music"
    assert by_name["Midnight City"].risk_status == "high_risk"
    assert by_name["Midnight City"].scene_reference == "04"
    assert by_name["Harbor Light Café"].category == "brand"
    assert by_name["Old Railway Station"].category == "location"


def test_category_playbook_exposes_rights_specific_questions() -> None:
    playbook = playbook_for("music")

    assert "composition" in " ".join(playbook["rights_questions"]).lower()
    assert playbook["required_evidence"]
    assert playbook["escalation_signals"]


def test_document_analysis_persists_assets_and_updates_job(tmp_path) -> None:
    database = make_database()
    store = LocalObjectStore(str(tmp_path))
    content = "## Scene 04 — Night\nA radio plays **Midnight City**."

    with database.session_factory() as session:
        project = ProjectRepository(session).create(
            Project(
                organization_id="demo-org", title="The Last Signal", project_type="Feature film"
            )
        )
        document = Document(
            organization_id="demo-org",
            project_id=project.id,
            original_filename="script.md",
            mime_type="text/markdown",
            size_bytes=len(content.encode()),
            sha256="fixture-hash",
            object_key="demo-org/script.source",
            extracted_text=content,
        )
        document = DocumentRepository(session).create(document)
        store.save_bytes(document.object_key, content.encode())
        job = JobRepository(session).create(
            Job(
                organization_id="demo-org",
                project_id=project.id,
                job_type="document_analysis",
                status="queued",
            )
        )

    process_document_analysis(database, store, job.id, document.id, "demo-org")

    with database.session_factory() as session:
        stored_job = JobRepository(session).get(job.id, "demo-org")
        stored_document = DocumentRepository(session).get(document.id, "demo-org")
        assets = AssetRepository(session).list_for_project(project.id, "demo-org")
        assert stored_job is not None and stored_job.status == "awaiting_review"
        assert stored_document is not None and stored_document.status == "analyzed"
        assert len(assets) == 1
        assert assets[0].canonical_name == "Midnight City"


def test_media_analysis_persists_transcript_and_metadata(tmp_path) -> None:
    database = make_database()
    store = LocalObjectStore(str(tmp_path))
    content = b"fixture media bytes"

    with database.session_factory() as session:
        project = ProjectRepository(session).create(
            Project(
                organization_id="demo-org", title="Media test", project_type="Feature film"
            )
        )
        document = Document(
            organization_id="demo-org",
            project_id=project.id,
            original_filename="screening-room.mp4",
            mime_type="video/mp4",
            size_bytes=len(content),
            sha256="fixture-hash",
            object_key="demo-org/media.source",
            extracted_text="",
            source_kind="video",
        )
        document = DocumentRepository(session).create(document)
        store.save_bytes(document.object_key, content)
        job = JobRepository(session).create(
            Job(
                organization_id="demo-org",
                project_id=project.id,
                job_type="media_analysis",
                status="queued",
            )
        )

    process_document_analysis(database, store, job.id, document.id, "demo-org")

    with database.session_factory() as session:
        stored_job = JobRepository(session).get(job.id, "demo-org")
        stored_document = DocumentRepository(session).get(document.id, "demo-org")
        assert stored_job is not None and stored_job.status == "awaiting_review"
        assert stored_document is not None and stored_document.status == "analyzed"
        assert stored_document.source_kind == "video"
        assert "Fixture transcript" in stored_document.extracted_text
        assert stored_document.media_metadata["provider"] == "fixture"
        assert stored_document.media_metadata["asset_count"] == 1
        assert AssetRepository(session).list_for_project(project.id, "demo-org")[0].canonical_name == "Sample music bed"


def test_vertex_media_payload_normalizes_timestamped_rights_signals() -> None:
    output = VertexGeminiMediaAnalyzer._parse_output(
        """
        {
          "summary": "A branded radio spot plays in the scene.",
          "transcript": "This is a test.",
          "duration_seconds": 65.5,
          "segments": [{"start_seconds": 42, "end_seconds": 48, "description": "Radio"}],
          "assets": [{
            "name": "Midnight City",
            "category": "music",
            "context": "The track is audible from a radio.",
            "start_seconds": 42,
            "end_seconds": 48,
            "confidence": 0.91,
            "risk_status": "high_risk",
            "reason_codes": ["recorded_music_signal"]
          }]
        }
        """,
        "video/mp4",
        "gemini-2.5-flash",
    )

    assert output.metadata["duration_seconds"] == 65.5
    assert output.candidates[0].scene_reference == "00:00:42"
    assert output.candidates[0].source_start == 42
    assert "video_visual_or_audio_signal" in output.candidates[0].reason_codes


def test_parallel_search_response_is_normalized() -> None:
    provider = ParallelApiProvider("test-key", base_url="https://parallel.test")

    async def fake_post(path: str, payload: dict) -> dict:
        assert path == "/v1/search"
        assert payload["search_queries"] == ["Midnight City licensing"]
        return {
            "search_id": "search_fixture_001",
            "results": [
                {
                    "url": "https://rights.example/music",
                    "title": "Music rights source",
                    "excerpts": ["A relevant licensing excerpt."],
                }
            ],
        }

    provider._post = fake_post  # type: ignore[method-assign]
    results = asyncio.run(
        provider.search("Midnight City licensing", objective="Find the rights owner.")
    )

    assert len(results) == 1
    assert results[0].request_id == "search_fixture_001"
    assert results[0].source_quality == "parallel_search"
    assert results[0].retrieved_at.tzinfo == UTC


def test_fixture_clearance_agent_requires_human_review() -> None:
    asset = Asset(
        id="asset-1",
        organization_id="demo-org",
        project_id="project-1",
        document_id="document-1",
        canonical_name="Midnight City",
        category="music",
        context="A radio plays Midnight City.",
        source_start=0,
        source_end=32,
        extraction_confidence=0.9,
        risk_status="high_risk",
        reason_codes=["music_identified"],
    )
    source = SourceRecord(
        research_run_id="run-1",
        url="https://example.com/rights",
        title="Rights source",
        excerpt="A licensing contact is identified.",
        source_quality="fixture",
    )

    output = asyncio.run(FixtureClearanceAgent().create_clearance_card(asset, [source]))

    assert output.risk_score == 90
    assert output.needs_human_review is True
    assert "music_rights_required" in output.reason_codes


def test_registered_agent_tools_use_fixture_provider_and_preserve_review_boundary() -> None:
    search_result = asyncio.run(
        search_rights_sources("Midnight City licensing", "Find the rights owner.", "run-1")
    )
    extract_result = asyncio.run(
        extract_rights_source("https://example.com/rights", "Extract licensing evidence.", "run-1")
    )
    risk_result = calculate_clearance_risk("music", 1, ["music_identified"])
    approval_result = request_human_approval(
        "asset-1", risk_result["recommendation"], risk_result["reason_codes"]
    )

    assert len(REGISTERED_AGENT_TOOLS) == 4
    assert search_result["status"] == "completed"
    assert search_result["sources"][0]["session_id"] == "run-1"
    assert extract_result["status"] == "completed"
    assert risk_result["needs_human_review"] is True
    assert approval_result["status"] == "pending_review"
    assert approval_result["requires_human_action"] is True


def test_outreach_draft_and_report_keep_human_boundary() -> None:
    project = Project(
        organization_id="demo-org",
        title="The Last Signal",
        project_type="Feature film",
    )
    project.updated_at = datetime.now(UTC)
    asset = Asset(
        id="asset-1",
        organization_id="demo-org",
        project_id="project-1",
        document_id="document-1",
        canonical_name="Midnight City",
        category="music",
        context="A radio plays Midnight City.",
        source_start=0,
        source_end=32,
        extraction_confidence=0.9,
        risk_status="high_risk",
        reason_codes=["music_identified"],
    )
    card = ClearanceCard(
        organization_id="demo-org",
        asset_id=asset.id,
        research_run_id="run-1",
        generated_by="fixture",
        status="pending_review",
        risk_score=90,
        confidence_score=0.55,
        summary="Evidence-backed music triage.",
        recommendation="Request a synchronization/music license.",
        reason_codes=["music_rights_required"],
        evidence_count=1,
        needs_human_review=True,
    )
    source = SourceRecord(
        research_run_id="run-1",
        url="https://example.com/rights",
        title="Rights source",
        excerpt="A licensing contact is identified.",
        source_quality="fixture",
    )

    subject, body = build_outreach_draft(project, asset, card, "Rights contact")
    report = build_clearance_report(project, [asset], [card], [source])

    assert "Midnight City" in subject
    assert "information request only" in body
    assert "Internal research note" not in body
    assert "not legal advice" in report
    assert "https://example.com/rights" in report
    assert "Report version: 1" in report
    assert "Policy version: risk-policy-v1" in report


def test_clearance_report_pdf_is_branded_and_structured() -> None:
    markdown = """# ClearCut clearance report — The Last Signal

- Project type: Feature film
- Generated: 2026-08-24T10:00:00+00:00
- Assets reviewed: 1

> ClearCut provides research and workflow support. This report is not legal advice.

## Asset summary

| Asset | Category | Status | Risk | Confidence | Evidence |
|---|---|---|---:|---:|---:|
| Midnight City | music | pending_review | 90/100 | 100% | 1 |

## Detailed review

### Midnight City

- Category: music
- Context: A radio plays Midnight City.
- Clearance card status: `pending_review`
- Risk score: `90/100`
- Confidence: `100%`
- Summary: Commercial music requires rights review.
- Recommended next action: Confirm composition and master rights.

Evidence:
- [Rights source](https://example.com/rights) — Licensing guidance.

## Decision log

| Asset | Decision | Actor | Recorded | Note |
|---|---|---|---|---|
| Midnight City | escalate_to_legal | demo-reviewer | 2026-08-24T10:02:00+00:00 | Confirm sync and master rights. |

## Permission work

| Asset | Status | Recipient | Due | Subject |
|---|---|---|---|---|
| Midnight City | approved | rights@example.com | 2026-09-01T00:00:00+00:00 | Music rights information request |
"""

    pdf = build_pdf(markdown)

    assert pdf.startswith(b"%PDF-1.4")
    assert b"/Type /Pages" in pdf
    assert b"CLEARCUT" in pdf
    assert b"Midnight City" in pdf
    assert b"Human accountability" in pdf
    assert b"demo-reviewer" in pdf
    assert b"PERMISSION WORK" in pdf
    assert b"rights@example.com" in pdf


def test_report_flattens_multiline_evidence_and_pdf_ignores_embedded_headings() -> None:
    project = Project(
        organization_id="demo-org",
        title="The Last Signal",
        project_type="Feature film",
    )
    asset = Asset(
        id="asset-1",
        organization_id="demo-org",
        project_id="project-1",
        document_id="document-1",
        canonical_name="Midnight City",
        category="music",
        context="A radio plays Midnight City.",
        source_start=0,
        source_end=32,
        extraction_confidence=0.9,
        risk_status="high_risk",
        reason_codes=["music_identified"],
    )
    source = SourceRecord(
        research_run_id="run-1",
        url="https://example.com/rights",
        title="Rights source",
        excerpt="A source.\n### Asset\nThis is an excerpt heading, not another asset.",
        source_quality="fixture",
    )
    card = ClearanceCard(
        organization_id="demo-org",
        asset_id=asset.id,
        research_run_id="run-1",
        generated_by="fixture",
        status="pending_review",
        risk_score=90,
        confidence_score=0.55,
        summary="Evidence-backed music triage.",
        recommendation="Request a synchronization/music license.",
        reason_codes=["music_rights_required"],
        evidence_count=1,
        needs_human_review=True,
    )

    report = build_clearance_report(project, [asset], [card], [source])
    parsed = _parse_report(report)

    assert "A source. ### Asset This is an excerpt heading, not another asset." in report
    assert len(parsed.details) == 1
    assert len(parsed.details[0].evidence) == 1

    legacy_markdown = report.replace(
        "A source. ### Asset This is an excerpt heading, not another asset.",
        "A source.\n### Asset\nThis is an excerpt heading, not another asset.",
    )
    assert len(_parse_report(legacy_markdown).details) == 1


def test_research_run_creates_evidence_backed_clearance_card() -> None:
    database = make_database()
    with database.session_factory() as session:
        project = ProjectRepository(session).create(
            Project(
                organization_id="demo-org", title="The Last Signal", project_type="Feature film"
            )
        )
        asset = Asset(
            organization_id="demo-org",
            project_id=project.id,
            document_id="document-1",
            canonical_name="Midnight City",
            category="music",
            context="A radio plays Midnight City.",
            source_start=0,
            source_end=32,
            extraction_confidence=0.9,
            risk_status="high_risk",
            reason_codes=["music_identified"],
        )
        AssetRepository(session).create_many([asset])
        run = ResearchRunRepository(session).create(
            ResearchRun(
                organization_id="demo-org",
                asset_id=asset.id,
                provider="parallel",
                operation="search",
                objective="Find the rights owner.",
                query="Midnight City licensing",
            )
        )

    asyncio.run(
        process_research_run(
            database,
            run.id,
            "demo-org",
            Settings(parallel_mode="fixture", agent_mode="fixture"),
        )
    )

    with database.session_factory() as session:
        stored_run = ResearchRunRepository(session).get(run.id, "demo-org")
        card = ClearanceCardRepository(session).get_for_run(run.id, "demo-org")
        assert stored_run is not None and stored_run.status == "completed"
        assert card is not None
        assert card.evidence_count == 1
        assert card.status == "pending_review"
        assert card.needs_human_review is True


def test_multi_angle_research_session_aggregates_tasks_and_evidence() -> None:
    database = make_database()
    with database.session_factory() as session:
        project = ProjectRepository(session).create(
            Project(
                organization_id="demo-org", title="The Last Signal", project_type="Feature film"
            )
        )
        asset = Asset(
            organization_id="demo-org",
            project_id=project.id,
            document_id="document-1",
            canonical_name="Midnight City",
            category="music",
            context="A radio plays Midnight City.",
            source_start=0,
            source_end=32,
            extraction_confidence=0.9,
            risk_status="high_risk",
            reason_codes=["music_identified"],
        )
        AssetRepository(session).create_many([asset])
        objective, plans = build_research_plan(asset)
        run = ResearchRunRepository(session).create(
            ResearchRun(
                organization_id="demo-org",
                asset_id=asset.id,
                provider="parallel",
                operation="multi_angle_search",
                objective=objective,
                query="Midnight City music rights clearance research session",
            )
        )
        research_session = ResearchSessionRepository(session).create(
            ResearchSession(
                organization_id="demo-org",
                asset_id=asset.id,
                provider="parallel",
                objective=objective,
                status="planned",
                total_tasks=len(plans),
                completed_tasks=0,
            )
        )
        tasks = ResearchTaskRepository(session).create_many(
            [
                ResearchTask(
                    organization_id="demo-org",
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

    for task in tasks:
        asyncio.run(
            process_research_task(
                database,
                task.id,
                "demo-org",
                Settings(parallel_mode="fixture", agent_mode="fixture"),
            )
        )

    with database.session_factory() as session:
        stored_session = ResearchSessionRepository(session).get(research_session.id, "demo-org")
        stored_tasks = ResearchTaskRepository(session).list_for_session(
            research_session.id, "demo-org"
        )
        stored_run = ResearchRunRepository(session).get(run.id, "demo-org")
        sources = ResearchRunRepository(session).list_sources(run.id)
        card = ClearanceCardRepository(session).get_for_run(run.id, "demo-org")
        assert stored_session is not None and stored_session.status == "completed"
        assert stored_session.completed_tasks == 4
        assert all(task.status == "completed" for task in stored_tasks)
        assert all(task.quality_tier == "demo" for task in stored_tasks)
        assert all(task.findings for task in stored_tasks)
        assert stored_run is not None and stored_run.status == "completed"
        assert len(sources) == 4
        assert {source.task_id for source in sources} == {task.id for task in stored_tasks}
        assert stored_session.findings
        assert card is not None and card.evidence_count == 4
