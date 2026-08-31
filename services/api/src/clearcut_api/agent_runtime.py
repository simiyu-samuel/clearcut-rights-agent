import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from .config import Settings
from .models import Asset, SourceRecord
from .risk_policy import calculate_confidence, calculate_risk


class AgentRuntimeError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ClearanceAgentOutput:
    summary: str
    recommendation: str
    risk_score: int
    confidence_score: float
    reason_codes: list[str]
    needs_human_review: bool
    generated_by: str
    model_name: str | None


class ClearanceAgent(Protocol):
    async def create_clearance_card(
        self, asset: Asset, sources: list[SourceRecord]
    ) -> ClearanceAgentOutput: ...


class FixtureClearanceAgent:
    """Deterministic policy-aware output for local development and judging demos."""

    async def create_clearance_card(
        self, asset: Asset, sources: list[SourceRecord]
    ) -> ClearanceAgentOutput:
        evidence_count = len(sources)
        risk = calculate_risk(asset.category, evidence_count, asset.reason_codes)
        return ClearanceAgentOutput(
            summary=(
                f"{asset.canonical_name} is a {asset.category} asset identified in "
                f"scene {asset.scene_reference or 'not specified'}. "
                f"The research run produced {evidence_count} evidence source(s)."
            ),
            recommendation=risk.recommendation,
            risk_score=risk.risk_score,
            confidence_score=calculate_confidence(evidence_count),
            reason_codes=risk.reason_codes,
            needs_human_review=True,
            generated_by="fixture",
            model_name=None,
        )


class VertexGeminiClearanceAgent:
    def __init__(self, settings: Settings):
        if not settings.google_cloud_project:
            raise AgentRuntimeError(
                "google_cloud_not_configured",
                "GOOGLE_CLOUD_PROJECT is required when AGENT_MODE=vertex",
            )
        try:
            from .adk_agent import build_clearance_app
        except ImportError as exc:
            raise AgentRuntimeError(
                "google_adk_not_installed",
                "Install the optional agent dependencies to use Vertex ADK with Gemini",
            ) from exc

        self._model_name = settings.gemini_model
        try:
            self._app = build_clearance_app(settings)
        except RuntimeError as exc:
            raise AgentRuntimeError("google_adk_not_configured", str(exc)) from exc

    async def create_clearance_card(
        self, asset: Asset, sources: list[SourceRecord]
    ) -> ClearanceAgentOutput:
        prompt = self._build_prompt(asset, sources)
        try:
            response_text = ""
            complete_payload_text: str | None = None
            event_count = 0
            text_event_count = 0
            async for event in self._app.async_stream_query(
                user_id=f"clearcut-asset-{asset.id}",
                message=prompt,
            ):
                event_count += 1
                event_text = self._extract_event_text(event)
                if not event_text or complete_payload_text is not None:
                    continue
                text_event_count += 1
                if self._is_complete_payload(event_text):
                    # A non-partial ADK event can be a cumulative snapshot. Keep
                    # the complete payload rather than duplicating snapshots.
                    complete_payload_text = event_text
                    continue
                # Other SDK versions emit JSON fragments without setting `partial`.
                # Accumulate those fragments until the required payload is complete.
                response_text += event_text
                if self._is_complete_payload(response_text):
                    complete_payload_text = response_text
            if not (complete_payload_text or response_text.strip()):
                raise AgentRuntimeError(
                    "gemini_empty_output",
                    f"Gemini emitted no usable text in {event_count} ADK event(s) "
                    f"({text_event_count} text event(s))",
                )
            payload = self._parse_json(complete_payload_text or response_text)
            output = self._parse_output(payload)
            policy = calculate_risk(asset.category, len(sources), asset.reason_codes)
            return ClearanceAgentOutput(
                summary=output.summary,
                recommendation=output.recommendation,
                risk_score=policy.risk_score,
                confidence_score=calculate_confidence(len(sources)),
                reason_codes=policy.reason_codes,
                needs_human_review=True,
                generated_by=output.generated_by,
                model_name=output.model_name,
            )
        except AgentRuntimeError:
            raise
        except (ValueError, TypeError) as exc:
            raise AgentRuntimeError(
                "gemini_invalid_output", "Gemini returned an invalid clearance-card payload"
            ) from exc
        except Exception as exc:  # pragma: no cover - SDK/network boundary
            raise AgentRuntimeError(
                "gemini_request_failed", "Gemini clearance-card generation failed"
            ) from exc

    @staticmethod
    def _extract_event_text(event: Any) -> str:
        """Extract model text from an ADK JSON event without depending on SDK models."""
        if isinstance(event, dict):
            content = event.get("content")
            direct_text = event.get("text") or event.get("output")
        else:
            content = getattr(event, "content", None)
            direct_text = getattr(event, "text", None) or getattr(event, "output", None)
        if isinstance(direct_text, str) and direct_text.strip():
            return direct_text.strip()
        if isinstance(content, dict):
            parts = content.get("parts") or []
        else:
            parts = getattr(content, "parts", None) or []
        texts: list[str] = []
        for part in parts:
            if isinstance(part, dict):
                text = part.get("text")
            else:
                text = getattr(part, "text", None)
            if isinstance(text, str) and text.strip():
                texts.append(text)
        return "".join(texts).strip()

    @classmethod
    def _is_complete_payload(cls, text: str) -> bool:
        try:
            payload = cls._parse_json(text)
        except (json.JSONDecodeError, ValueError, TypeError):
            return False
        return all(
            field in payload
            for field in (
                "summary",
                "recommendation",
                "risk_score",
                "confidence_score",
                "reason_codes",
                "needs_human_review",
            )
        )

    @staticmethod
    def _event_is_final(event: Any) -> bool:
        if isinstance(event, dict):
            return bool(event.get("turn_complete") or event.get("is_final_response"))
        return bool(getattr(event, "turn_complete", False))

    @staticmethod
    def _event_is_partial(event: Any) -> bool:
        if isinstance(event, dict):
            return bool(event.get("partial"))
        return bool(getattr(event, "partial", False))

    @staticmethod
    def _looks_like_json(text: str) -> bool:
        return "{" in text and "}" in text

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if match is None:
                raise
            payload = json.loads(match.group(0))
        if not isinstance(payload, dict):
            raise ValueError("clearance card must be an object")
        return payload

    @staticmethod
    def _build_prompt(asset: Asset, sources: list[SourceRecord]) -> str:
        evidence = [
            {
                "title": source.title,
                "url": source.url,
                "excerpt": source.excerpt,
                "source_quality": source.source_quality,
            }
            for source in sources
        ]
        return json.dumps(
            {
                "task": "Create an evidence-backed rights-clearance triage card.",
                "safety": [
                    "This is workflow support, not legal advice.",
                    "Use only the supplied asset and evidence.",
                    "Never state that an asset is legally cleared.",
                    "Always require human review before a downstream delivery decision.",
                ],
                "required_json": {
                    "summary": "string",
                    "recommendation": "string",
                    "risk_score": "integer from 0 to 100",
                    "confidence_score": "number from 0 to 1",
                    "reason_codes": "array of short strings",
                    "needs_human_review": "boolean, always true",
                },
                "asset": {
                    "canonical_name": asset.canonical_name,
                    "category": asset.category,
                    "context": asset.context,
                    "scene_reference": asset.scene_reference,
                    "extraction_reason_codes": asset.reason_codes,
                },
                "evidence": evidence,
            },
            indent=2,
        )

    def _parse_output(self, payload: Any) -> ClearanceAgentOutput:
        if not isinstance(payload, dict):
            raise AgentRuntimeError("gemini_invalid_output", "Clearance card must be a JSON object")
        try:
            risk_score = int(payload["risk_score"])
            confidence_score = float(payload["confidence_score"])
            raw_reason_codes = payload["reason_codes"]
            needs_human_review = payload["needs_human_review"]
            summary = str(payload["summary"])
            recommendation = str(payload["recommendation"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AgentRuntimeError(
                "gemini_invalid_output", "Clearance card is missing required fields"
            ) from exc
        if not isinstance(raw_reason_codes, list) or not isinstance(needs_human_review, bool):
            raise AgentRuntimeError(
                "gemini_invalid_output", "Clearance card fields have invalid types"
            )
        reason_codes = [str(code) for code in raw_reason_codes]
        if not 0 <= risk_score <= 100 or not 0 <= confidence_score <= 1:
            raise AgentRuntimeError(
                "gemini_invalid_output", "Clearance card scores are outside the allowed range"
            )
        if not needs_human_review:
            raise AgentRuntimeError(
                "gemini_invalid_output", "Clearance cards must require human review"
            )
        prohibited_claims = ("legally cleared", "fully cleared", "no license is required")
        if any(claim in f"{summary} {recommendation}".lower() for claim in prohibited_claims):
            raise AgentRuntimeError(
                "gemini_unsafe_output", "Clearance card contains an unsupported legal conclusion"
            )
        return ClearanceAgentOutput(
            summary=summary,
            recommendation=recommendation,
            risk_score=risk_score,
            confidence_score=confidence_score,
            reason_codes=reason_codes,
            needs_human_review=True,
            generated_by="vertex_adk_gemini",
            model_name=self._model_name,
        )


def build_clearance_agent(settings: Settings) -> ClearanceAgent:
    if settings.agent_mode == "vertex":
        return VertexGeminiClearanceAgent(settings)
    return FixtureClearanceAgent()
