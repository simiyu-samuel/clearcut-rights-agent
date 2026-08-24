from dataclasses import dataclass

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
    ResearchSessionRepository,
    ResearchTaskRepository,
)
from .storage import ObjectStore


@dataclass(frozen=True)
class ResearchTaskPlan:
    angle: str
    title: str
    objective: str
    query: str


def build_research_plan(asset: Asset, objective: str | None = None) -> tuple[str, list[ResearchTaskPlan]]:
    """Return a category-aware, inspectable plan before any provider calls start."""

    rights_subject = {
        "music": "composition, master recording, publisher, label, and sync rights",
        "brand": "trademark owner, brand usage, sponsorship, and publicity restrictions",
        "location": "location owner, filming permission, releases, and site restrictions",
        "artwork": "artist, copyright owner, reproduction, and exhibition permissions",
        "person": "likeness, publicity, performance, and release requirements",
        "sports": "league, team, athlete, broadcast, and clip licensing requirements",
    }.get(asset.category, "ownership, permission, and usage restrictions")
    shared = objective or (
        f'Build an evidence-backed clearance plan for "{asset.canonical_name}" in a film or '
        "television production. Identify rights holders, permission paths, territory limits, "
        f"and conflicts across {rights_subject}."
    )
    subject = f'"{asset.canonical_name}" {asset.category}'
    plans = [
        ResearchTaskPlan(
            angle="rights_owner",
            title="Owner & control",
            objective=f"Identify the likely rights owner or controlling party for {subject}. {shared}",
            query=f"{subject} rights owner copyright holder official",
        ),
        ResearchTaskPlan(
            angle="licensing_path",
            title="Licensing path",
            objective=f"Find the official licensing, permissions, or clearance route for {subject}. {shared}",
            query=f"{subject} licensing permissions clearance contact official",
        ),
        ResearchTaskPlan(
            angle="territory_scope",
            title="Territory & usage",
            objective=f"Find territory, media, duration, or usage restrictions that affect {subject}. {shared}",
            query=f"{subject} film television usage territory restrictions license",
        ),
        ResearchTaskPlan(
            angle="conflicts_and_exclusions",
            title="Conflicts & exclusions",
            objective=f"Look for exclusions, approval conditions, conflicts, or evidence gaps for {subject}. {shared}",
            query=f"{subject} usage restrictions exclusions conflict clearance",
        ),
    ]
    return shared, plans


def source_quality_tier(sources: list[SourceRecord]) -> str:
    qualities = {source.source_quality for source in sources}
    if not qualities:
        return "none"
    if "parallel_extract" in qualities:
        return "strong"
    if "parallel_search" in qualities:
        return "moderate"
    if "fixture" in qualities:
        return "demo"
    return "unrated"


def research_gaps(sources: list[SourceRecord]) -> list[str]:
    if not sources:
        return ["no_evidence", "insufficient_evidence"]
    gaps: list[str] = []
    if source_quality_tier(sources) not in {"strong", "demo"}:
        gaps.append("source_quality_unverified")
    if len(sources) == 1:
        gaps.append("single_source_confirmation")
    gaps.append("human_rights_verification_required")
    return gaps


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


async def finalize_research_session(
    database: Database, session_id: str, organization_id: str, settings: Settings
) -> None:
    with database.session_factory() as session:
        research_session = ResearchSessionRepository(session).get(session_id, organization_id)
        if research_session is None:
            return
        tasks = ResearchTaskRepository(session).list_for_session(session_id, organization_id)
        if not tasks or any(task.status in {"queued", "running"} for task in tasks):
            return
        run = ResearchRunRepository(session).get(tasks[0].research_run_id, organization_id)
        asset = AssetRepository(session).get(research_session.asset_id, organization_id)
        if run is None or asset is None:
            ResearchSessionRepository(session).update(
                session_id, status="failed", completed_tasks=len(tasks)
            )
            return
        stored_sources = ResearchRunRepository(session).list_sources(run.id)
        existing_card = ClearanceCardRepository(session).get_for_run(run.id, organization_id)
        session_status = (
            "partial"
            if any(task.status in {"partial", "failed"} for task in tasks) or not stored_sources
            else "completed"
        )
        completed_tasks = sum(
            task.status in {"completed", "partial", "failed"} for task in tasks
        )

    if existing_card is None:
        try:
            card_output = await build_clearance_agent(settings).create_clearance_card(
                asset, stored_sources
            )
        except AgentRuntimeError as exc:
            with database.session_factory() as session:
                ResearchSessionRepository(session).update(
                    session_id, status="failed", completed_tasks=completed_tasks
                )
                ResearchRunRepository(session).update(run.id, status="failed", error_code=exc.code)
            return

        with database.session_factory() as session:
            cards = ClearanceCardRepository(session)
            if cards.get_for_run(run.id, organization_id) is None:
                cards.create(
                    ClearanceCard(
                        organization_id=organization_id,
                        asset_id=asset.id,
                        research_run_id=run.id,
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

    with database.session_factory() as session:
        ResearchSessionRepository(session).update(
            session_id, status=session_status, completed_tasks=completed_tasks
        )
        ResearchRunRepository(session).update(run.id, status=session_status)


async def process_research_task(
    database: Database, task_id: str, organization_id: str, settings: Settings
) -> None:
    with database.session_factory() as session:
        tasks = ResearchTaskRepository(session)
        task = tasks.get(task_id, organization_id)
        if task is None or task.status in {"completed", "partial"}:
            return
        research_session = ResearchSessionRepository(session).get(task.session_id, organization_id)
        run = ResearchRunRepository(session).get(task.research_run_id, organization_id)
        if research_session is None or run is None:
            tasks.update(task_id, status="failed", error_code="research_session_not_found")
            return
        asset = AssetRepository(session).get(research_session.asset_id, organization_id)
        if asset is None:
            tasks.update(task_id, status="failed", error_code="asset_not_found")
            return
        tasks.update(task_id, status="running", error_code=None)
        ResearchSessionRepository(session).update(task.session_id, status="running")
        ResearchRunRepository(session).update(run.id, status="running", error_code=None)
        query = task.query
        objective = task.objective
        session_id = task.session_id
        run_id = run.id

    try:
        provider = make_research_provider(settings)
        provider_session_id = f"clearcut:{session_id}"
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
            runs.update(run_id, provider_request_id=request_id)
            ResearchTaskRepository(session).update(
                task_id,
                status="completed" if sources else "partial",
                source_count=len(sources),
                quality_tier=source_quality_tier(sources),
                gap_codes=research_gaps(sources),
                error_code=None,
            )
            tasks = ResearchTaskRepository(session).list_for_session(session_id, organization_id)
            completed_tasks = sum(
                item.status in {"completed", "partial", "failed"} for item in tasks
            )
            ResearchSessionRepository(session).update(
                session_id, completed_tasks=completed_tasks
            )
        await finalize_research_session(database, session_id, organization_id, settings)
    except ParallelProviderError as exc:
        with database.session_factory() as session:
            ResearchTaskRepository(session).update(
                task_id,
                status="failed",
                error_code=exc.code,
                gap_codes=["provider_error", "retry_recommended"],
            )
            tasks = ResearchTaskRepository(session).list_for_session(session_id, organization_id)
            ResearchSessionRepository(session).update(
                session_id,
                completed_tasks=sum(
                    item.status in {"completed", "partial", "failed"} for item in tasks
                ),
            )
        await finalize_research_session(database, session_id, organization_id, settings)


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
