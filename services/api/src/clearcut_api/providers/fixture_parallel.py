from datetime import UTC, datetime

from .base import SourceResult


class FixtureParallelProvider:
    """Deterministic local provider used until live Parallel credentials are configured."""

    async def search(
        self, query: str, *, objective: str, session_id: str | None = None
    ) -> list[SourceResult]:
        now = datetime.now(UTC)
        return [
            SourceResult(
                url="https://example.com/clearcut/fixture-rights-source",
                title=f"Fixture source for {query}",
                excerpt=f"Synthetic evidence for the research objective: {objective}.",
                retrieved_at=now,
                source_quality="fixture",
                request_id="fixture-search-001",
                session_id=session_id or "fixture-session-001",
            )
        ]

    async def extract(
        self, url: str, *, objective: str, session_id: str | None = None
    ) -> SourceResult:
        return SourceResult(
            url=url,
            title="Fixture extracted source",
            excerpt=f"Synthetic extracted evidence for: {objective}.",
            retrieved_at=datetime.now(UTC),
            source_quality="fixture",
            request_id="fixture-extract-001",
            session_id=session_id or "fixture-session-001",
        )
