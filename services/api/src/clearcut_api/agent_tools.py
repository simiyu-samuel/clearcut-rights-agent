from typing import Any

from .config import Settings, settings
from .providers import (
    FixtureParallelProvider,
    ParallelApiProvider,
    ParallelProviderError,
    ResearchProvider,
)
from .risk_policy import calculate_risk


def _make_provider(runtime_settings: Settings) -> ResearchProvider:
    if runtime_settings.parallel_mode == "live":
        if not runtime_settings.parallel_api_key:
            raise ParallelProviderError(
                "parallel_not_configured", "PARALLEL_API_KEY is required for live mode"
            )
        return ParallelApiProvider(runtime_settings.parallel_api_key)
    return FixtureParallelProvider()


def _source_payload(result: Any) -> dict[str, Any]:
    return {
        "url": result.url,
        "title": result.title,
        "excerpt": result.excerpt,
        "source_quality": result.source_quality,
        "request_id": result.request_id,
        "session_id": result.session_id,
        "retrieved_at": result.retrieved_at.isoformat(),
    }


async def search_rights_sources(
    query: str, objective: str, session_id: str | None = None
) -> dict[str, Any]:
    """Search for rights ownership and licensing evidence through the configured provider."""
    try:
        results = await _make_provider(settings).search(
            query, objective=objective, session_id=session_id
        )
    except ParallelProviderError as exc:
        return {"status": "failed", "error_code": exc.code, "sources": []}
    return {
        "status": "completed" if results else "partial",
        "sources": [_source_payload(result) for result in results],
    }


async def extract_rights_source(
    url: str, objective: str, session_id: str | None = None
) -> dict[str, Any]:
    """Extract readable evidence from a selected rights source URL."""
    try:
        result = await _make_provider(settings).extract(
            url, objective=objective, session_id=session_id
        )
    except ParallelProviderError as exc:
        return {"status": "failed", "error_code": exc.code, "source": None}
    return {"status": "completed", "source": _source_payload(result)}


def calculate_clearance_risk(
    category: str, evidence_count: int, reason_codes: list[str] | None = None
) -> dict[str, Any]:
    """Calculate deterministic operational triage; this never declares legal clearance."""
    result = calculate_risk(category, evidence_count, reason_codes)
    return {
        "risk_score": result.risk_score,
        "reason_codes": result.reason_codes,
        "recommendation": result.recommendation,
        "needs_human_review": True,
    }


def request_human_approval(
    asset_id: str, recommendation: str, reason_codes: list[str] | None = None
) -> dict[str, Any]:
    """Create a review intent; only an authenticated human can record an approval decision."""
    return {
        "status": "pending_review",
        "asset_id": asset_id,
        "recommendation": recommendation,
        "reason_codes": reason_codes or [],
        "requires_human_action": True,
    }


REGISTERED_AGENT_TOOLS = [
    search_rights_sources,
    extract_rights_source,
    calculate_clearance_risk,
    request_human_approval,
]

# The clearance-card agent receives the deterministic policy tool only. Research
# is performed by the authenticated workflow before this agent is invoked, while
# the broader registry remains available to an orchestration/Agent Engine entrypoint.
CLEARANCE_AGENT_TOOLS = [calculate_clearance_risk]
