from datetime import UTC, datetime

import httpx

from .base import SourceResult


class ParallelProviderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class ParallelApiProvider:
    """Typed adapter for Parallel's v1 Search and Extract APIs."""

    def __init__(self, api_key: str, base_url: str = "https://api.parallel.ai"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def _post(self, path: str, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{self.base_url}{path}",
                    headers={"x-api-key": self.api_key, "content-type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise ParallelProviderError(
                f"parallel_http_{exc.response.status_code}", "Parallel returned an error"
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ParallelProviderError(
                "parallel_request_failed", "Parallel request failed"
            ) from exc

    async def search(
        self, query: str, *, objective: str, session_id: str | None = None
    ) -> list[SourceResult]:
        payload = {"search_queries": [query], "objective": objective, "max_chars_total": 12000}
        if session_id:
            payload["session_id"] = session_id
        response = await self._post("/v1/search", payload)
        request_id = response.get("search_id")
        response_session_id = response.get("session_id") or session_id
        retrieved_at = datetime.now(UTC)
        return [
            SourceResult(
                url=result.get("url", ""),
                title=result.get("title") or result.get("url", "Untitled source"),
                excerpt="\n\n".join(result.get("excerpts") or []),
                retrieved_at=retrieved_at,
                source_quality="parallel_search",
                request_id=request_id,
                session_id=response_session_id,
            )
            for result in response.get("results", [])
            if result.get("url")
        ]

    async def extract(
        self, url: str, *, objective: str, session_id: str | None = None
    ) -> SourceResult:
        payload = {"urls": [url], "objective": objective, "max_chars_total": 12000}
        if session_id:
            payload["session_id"] = session_id
        response = await self._post("/v1/extract", payload)
        result = (response.get("results") or [{}])[0]
        excerpt = "\n\n".join(result.get("excerpts") or [])
        if result.get("full_content"):
            excerpt = result["full_content"]
        return SourceResult(
            url=result.get("url", url),
            title=result.get("title") or url,
            excerpt=excerpt,
            retrieved_at=datetime.now(UTC),
            source_quality="parallel_extract",
            request_id=response.get("extract_id"),
            session_id=response.get("session_id") or session_id,
        )
