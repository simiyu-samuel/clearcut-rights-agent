from .config import Settings
from .db import Database
from .extraction import extract_candidate_assets
from .models import Asset, SourceRecord
from .providers import (
    FixtureParallelProvider,
    ParallelApiProvider,
    ParallelProviderError,
    ResearchProvider,
)
from .repositories import AssetRepository, DocumentRepository, JobRepository, ResearchRunRepository
from .storage import LocalObjectStore


def make_research_provider(settings: Settings) -> ResearchProvider:
    if settings.parallel_mode == "live":
        if not settings.parallel_api_key:
            raise ParallelProviderError(
                "parallel_not_configured", "PARALLEL_API_KEY is required for live mode"
            )
        return ParallelApiProvider(settings.parallel_api_key)
    return FixtureParallelProvider()


def process_document_analysis(
    database: Database,
    storage: LocalObjectStore,
    job_id: str,
    document_id: str,
    organization_id: str,
) -> None:
    with database.session_factory() as session:
        documents = DocumentRepository(session)
        jobs = JobRepository(session)
        assets = AssetRepository(session)
        document = documents.get(document_id, organization_id)
        if document is None:
            jobs.update_status(job_id, "failed", error_code="document_not_found")
            return
        documents.update_status(document_id, "processing")
        jobs.update_status(job_id, "running")
        try:
            text = storage.read_text(document.object_key)
            candidates = extract_candidate_assets(text)
            created = [
                Asset(
                    organization_id=organization_id,
                    project_id=document.project_id,
                    document_id=document.id,
                    canonical_name=candidate.canonical_name,
                    category=candidate.category,
                    context=candidate.context,
                    scene_reference=candidate.scene_reference,
                    source_start=candidate.source_start,
                    source_end=candidate.source_end,
                    extraction_confidence=candidate.extraction_confidence,
                    risk_status=candidate.risk_status,
                    reason_codes=candidate.reason_codes,
                )
                for candidate in candidates
            ]
            assets.create_many(created)
            documents.update_status(document_id, "analyzed")
            jobs.update_status(job_id, "awaiting_review")
        except (OSError, UnicodeError, ValueError) as exc:
            documents.update_status(document_id, "failed")
            jobs.update_status(job_id, "failed", error_code=f"analysis_failed:{type(exc).__name__}")


async def process_research_run(
    database: Database, run_id: str, organization_id: str, settings: Settings
) -> None:
    with database.session_factory() as session:
        runs = ResearchRunRepository(session)
        assets = AssetRepository(session)
        run = runs.get(run_id, organization_id)
        if run is None:
            return
        asset = assets.get(run.asset_id, organization_id)
        if asset is None:
            runs.update(run_id, status="failed", error_code="asset_not_found")
            return
        runs.update(run_id, status="running")

    try:
        provider = make_research_provider(settings)
        results = await provider.search(run.query, objective=run.objective)
        with database.session_factory() as session:
            runs = ResearchRunRepository(session)
            sources = [
                SourceRecord(
                    research_run_id=run_id,
                    url=result.url,
                    title=result.title,
                    excerpt=result.excerpt,
                    source_quality=result.source_quality,
                    retrieved_at=result.retrieved_at,
                )
                for result in results
            ]
            if sources:
                runs.add_sources(sources)
            request_id = results[0].request_id if results else None
            runs.update(
                run_id, status="completed" if sources else "partial", provider_request_id=request_id
            )
    except ParallelProviderError as exc:
        with database.session_factory() as session:
            ResearchRunRepository(session).update(run_id, status="failed", error_code=exc.code)
