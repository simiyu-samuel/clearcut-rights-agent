import asyncio
import json
from dataclasses import dataclass
from typing import Any, Protocol

from .config import Settings
from .models import Asset, SourceRecord


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

    _GUIDANCE = {
        "music": (
            90,
            "music_rights_required",
            "Request a synchronization/music license and confirm territory, term, media, and usage scope.",
        ),
        "brand": (
            65,
            "trademark_usage_review",
            "Confirm trademark or appearance permission and document the intended commercial context.",
        ),
        "location": (
            55,
            "location_release_required",
            "Confirm the filming permit and location release for the territory and production dates.",
        ),
        "artwork": (
            60,
            "artwork_license_review",
            "Confirm an artwork license or replace the asset with a production-cleared alternative.",
        ),
        "organization": (
            50,
            "name_or_logo_review",
            "Confirm name/logo/reference usage and retain the supporting permission or editorial rationale.",
        ),
    }

    async def create_clearance_card(
        self, asset: Asset, sources: list[SourceRecord]
    ) -> ClearanceAgentOutput:
        risk_score, reason_code, recommendation = self._GUIDANCE.get(
            asset.category,
            (
                50,
                "category_specific_review",
                "Confirm the rights position with the relevant rights holder.",
            ),
        )
        evidence_count = len(sources)
        confidence = min(0.95, 0.35 + (0.2 * evidence_count)) if evidence_count else 0.2
        return ClearanceAgentOutput(
            summary=(
                f"{asset.canonical_name} is a {asset.category} asset identified in "
                f"scene {asset.scene_reference or 'not specified'}. "
                f"The research run produced {evidence_count} evidence source(s)."
            ),
            recommendation=recommendation,
            risk_score=risk_score,
            confidence_score=confidence,
            reason_codes=[reason_code, *asset.reason_codes],
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
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise AgentRuntimeError(
                "google_genai_not_installed",
                "Install the optional agent dependencies to use Vertex Gemini",
            ) from exc

        self._types = types
        self._model_name = settings.gemini_model
        self._client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )

    async def create_clearance_card(
        self, asset: Asset, sources: list[SourceRecord]
    ) -> ClearanceAgentOutput:
        prompt = self._build_prompt(asset, sources)
        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self._model_name,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0,
                ),
            )
            payload = json.loads(response.text or "")
            return self._parse_output(payload)
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
            generated_by="vertex_gemini",
            model_name=self._model_name,
        )


def build_clearance_agent(settings: Settings) -> ClearanceAgent:
    if settings.agent_mode == "vertex":
        return VertexGeminiClearanceAgent(settings)
    return FixtureClearanceAgent()
