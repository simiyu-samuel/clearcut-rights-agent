from datetime import datetime, timezone

from .base import SourceResult


class FixtureParallelProvider:
    """Deterministic local provider used until live Parallel credentials are configured."""

    async def search(self, query: str, *, objective: str) -> list[SourceResult]:
        now = datetime.now(timezone.utc)
        return [
            SourceResult(
                url="https://example.com/clearcut/fixture-rights-source",
                title=f"Fixture source for {query}",
                excerpt=f"Synthetic evidence for the research objective: {objective}.",
                retrieved_at=now,
                source_quality="fixture",
            )
        ]

    async def extract(self, url: str, *, objective: str) -> SourceResult:
        return SourceResult(
            url=url,
            title="Fixture extracted source",
            excerpt=f"Synthetic extracted evidence for: {objective}.",
            retrieved_at=datetime.now(timezone.utc),
            source_quality="fixture",
        )
