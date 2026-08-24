from .agent_runtime import AgentRuntimeError, build_clearance_agent
from .config import Settings
from .db import Database
from .extraction import extract_candidate_assets
from .models import Asset, ClearanceCard, SourceRecord
from .providers import (
    FixtureParallelProvider,
    ParallelApiProvider,
    ParallelProviderError,
    ResearchProvider,
)
from .repositories import (
    AssetRepository,
    ClearanceCardRepository,
    DocumentRepository,
    JobRepository,
    ResearchRunRepository,
)
from .storage import ObjectStore


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
    storage: ObjectStore,
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
        query = run.query
        objective = run.objective
        asset_id = asset.id

    try:
        provider = make_research_provider(settings)
        provider_session_id = f"clearcut:{run_id}"
        search_results = await provider.search(
            query, objective=objective, session_id=provider_session_id
        )
        results = []
        for result in search_results[:3]:
            try:
                extracted = await provider.extract(
                    result.url, objective=objective, session_id=provider_session_id
                )
            except ParallelProviderError:
                extracted = result
            results.append(extracted if extracted.excerpt else result)
        with database.session_factory() as session:
            runs = ResearchRunRepository(session)
            sources = [
                SourceRecord(
                    research_run_id=run_id,
                    url=result.url,
                    title=result.title,
                    excerpt=result.excerpt,
                    source_quality=result.source_quality,
                    provider_session_id=result.session_id,
                    retrieved_at=result.retrieved_at,
                )
                for result in results
            ]
            if sources:
                runs.add_sources(sources)
            request_id = search_results[0].request_id if search_results else None
            # Keep the run in `running` until its clearance card is persisted. The
            # review UI uses the run status as its signal to refresh cards, so
            # publishing completion before card generation creates a race where
            # the first refresh sees sources but no clearance card.
            runs.update(run_id, provider_request_id=request_id)
            asset = AssetRepository(session).get(asset_id, organization_id)
            stored_sources = runs.list_sources(run_id)
        if asset is None:
            return

        try:
            card_output = await build_clearance_agent(settings).create_clearance_card(
                asset, stored_sources
            )
        except AgentRuntimeError as exc:
            with database.session_factory() as session:
                ResearchRunRepository(session).update(run_id, status="failed", error_code=exc.code)
            return

        with database.session_factory() as session:
            cards = ClearanceCardRepository(session)
            if cards.get_for_run(run_id, organization_id) is None:
                cards.create(
                    ClearanceCard(
                        organization_id=organization_id,
                        asset_id=asset_id,
                        research_run_id=run_id,
                        generated_by=card_output.generated_by,
                        model_name=card_output.model_name,
                        status="pending_review" if stored_sources else "needs_more_research",
                        risk_score=card_output.risk_score,
                        confidence_score=card_output.confidence_score,
                        summary=card_output.summary,
                        recommendation=card_output.recommendation,
                        reason_codes=card_output.reason_codes,
                        evidence_count=len(stored_sources),
                        needs_human_review=card_output.needs_human_review,
                    )
                )
            ResearchRunRepository(session).update(
                run_id,
                status="completed" if stored_sources else "partial",
                provider_request_id=request_id,
            )
    except ParallelProviderError as exc:
        with database.session_factory() as session:
            ResearchRunRepository(session).update(run_id, status="failed", error_code=exc.code)
