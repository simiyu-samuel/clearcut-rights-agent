import asyncio
from datetime import UTC

from clearcut_api.agent_runtime import FixtureClearanceAgent
from clearcut_api.config import Settings
from clearcut_api.extraction import extract_candidate_assets
from clearcut_api.models import Asset, Document, Job, Project, ResearchRun, SourceRecord
from clearcut_api.providers.parallel_api import ParallelApiProvider
from clearcut_api.repositories import (
    AssetRepository,
    ClearanceCardRepository,
    DocumentRepository,
    JobRepository,
    ProjectRepository,
    ResearchRunRepository,
)
from clearcut_api.storage import LocalObjectStore
from clearcut_api.workflows import process_document_analysis, process_research_run

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
