from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class SourceResult:
    url: str
    title: str
    excerpt: str
    retrieved_at: datetime
    source_quality: str
    request_id: str | None = None
    session_id: str | None = None


class ResearchProvider(Protocol):
    async def search(
        self, query: str, *, objective: str, session_id: str | None = None
    ) -> list[SourceResult]: ...

    async def extract(
        self, url: str, *, objective: str, session_id: str | None = None
    ) -> SourceResult: ...
