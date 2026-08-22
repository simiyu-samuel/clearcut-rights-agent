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


class ResearchProvider(Protocol):
    async def search(self, query: str, *, objective: str) -> list[SourceResult]: ...

    async def extract(self, url: str, *, objective: str) -> SourceResult: ...
