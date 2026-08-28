from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any

from .agent_runtime import AgentRuntimeError
from .config import Settings
from .extraction import CandidateAsset


@dataclass(frozen=True)
class MediaAnalysisOutput:
    transcript: str
    summary: str
    candidates: list[CandidateAsset]
    metadata: dict[str, object]


class MediaAnalyzer:
    async def analyze(
        self, object_uri: str, mime_type: str, original_filename: str
    ) -> MediaAnalysisOutput:
        raise NotImplementedError


class FixtureMediaAnalyzer(MediaAnalyzer):
    """Deterministic media output for local development and automated tests."""

    async def analyze(
        self, object_uri: str, mime_type: str, original_filename: str
    ) -> MediaAnalysisOutput:
        del object_uri
        transcript = (
            f"Fixture transcript for {original_filename}. "
            "The production media analyzer will transcribe dialogue and identify visible "
            "rights-bearing signals."
        )
        candidates = [
            CandidateAsset(
                canonical_name="Sample music bed",
                category="music",
                context="Fixture media signal: a recorded music bed is audible in the source.",
                scene_reference="00:00:00",
                source_start=0,
                source_end=8,
                extraction_confidence=0.72,
                risk_status="high_risk",
                reason_codes=["fixture_media_signal", "recorded_music_signal"],
            )
        ]
        return MediaAnalysisOutput(
            transcript=transcript,
            summary=f"Fixture media analysis completed for {original_filename}.",
            candidates=candidates,
            metadata={
                "provider": "fixture",
                "mime_type": mime_type,
                "duration_seconds": None,
                "segments": [],
            },
        )


class VertexGeminiMediaAnalyzer(MediaAnalyzer):
    def __init__(self, settings: Settings):
        if not settings.google_cloud_project:
            raise AgentRuntimeError(
                "google_cloud_not_configured",
                "GOOGLE_CLOUD_PROJECT is required when AGENT_MODE=vertex",
            )
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - deployment dependency boundary
            raise AgentRuntimeError(
                "google_genai_not_installed",
                "Install the optional agent dependencies to analyze media with Vertex Gemini",
            ) from exc

        self._types = types
        self._model_name = settings.gemini_model
        self._client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )

    async def analyze(
        self, object_uri: str, mime_type: str, original_filename: str
    ) -> MediaAnalysisOutput:
        prompt = self._build_prompt(original_filename, mime_type)
        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self._model_name,
                contents=[
                    self._types.Part.from_uri(file_uri=object_uri, mime_type=mime_type),
                    prompt,
                ],
                config=self._types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0,
                ),
            )
            return self._parse_output(response.text or "", mime_type, self._model_name)
        except AgentRuntimeError:
            raise
        except (ValueError, TypeError) as exc:
            raise AgentRuntimeError(
                "gemini_invalid_media_output", "Gemini returned an invalid media analysis payload"
            ) from exc
        except Exception as exc:  # pragma: no cover - SDK/network boundary
            raise AgentRuntimeError(
                "gemini_media_request_failed", "Gemini media analysis failed"
            ) from exc

    @staticmethod
    def _build_prompt(original_filename: str, mime_type: str) -> str:
        return json.dumps(
            {
                "task": (
                    "Analyze this audiovisual source for rights-bearing signals that may "
                    "need clearance before film or television distribution."
                ),
                "source": {"filename": original_filename, "mime_type": mime_type},
                "inspect": [
                    "Transcribe spoken dialogue and meaningful audible speech.",
                    "Identify music, lyrics, broadcasts, podcasts, or other recorded audio.",
                    "Identify visible brands, logos, products, packaging, signage, and trademarks.",
                    "Identify artwork, photographs, screens, performances, likenesses, and locations.",
                    "Use timestamps in seconds for every signal and preserve uncertainty.",
                ],
                "safety": [
                    "This is workflow support, not legal advice.",
                    "Never state that an asset is legally cleared.",
                    "Flag ambiguous signals for human review instead of guessing.",
                ],
                "required_json": {
                    "summary": "short string",
                    "transcript": "string, empty only if there is no speech",
                    "duration_seconds": "number or null",
                    "segments": [
                        {
                            "start_seconds": "number",
                            "end_seconds": "number",
                            "description": "what is visible or audible",
                            "dialogue": "transcribed speech for the segment",
                        }
                    ],
                    "assets": [
                        {
                            "name": "canonical rights-bearing name",
                            "category": "music|brand|artwork|location|product|logo|performance|other",
                            "context": "evidence from the segment",
                            "start_seconds": "number",
                            "end_seconds": "number",
                            "confidence": "number from 0 to 1",
                            "risk_status": "high_risk|needs_review|insufficient_evidence",
                            "reason_codes": ["short machine-readable signals"],
                        }
                    ],
                },
            },
            indent=2,
        )

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
            raise ValueError("media analysis must be an object")
        return payload

    @classmethod
    def _parse_output(cls, text: str, mime_type: str, model_name: str) -> MediaAnalysisOutput:
        payload = cls._parse_json(text)
        summary = str(payload.get("summary") or "Media analysis completed.").strip()
        transcript = str(payload.get("transcript") or "").strip()
        duration = payload.get("duration_seconds")
        duration_seconds = None if duration is None else max(0.0, float(duration))
        raw_segments = payload.get("segments")
        segments = raw_segments if isinstance(raw_segments, list) else []
        candidates: list[CandidateAsset] = []
        seen: set[tuple[str, str]] = set()
        for raw_asset in payload.get("assets") or []:
            if not isinstance(raw_asset, dict):
                continue
            name = str(raw_asset.get("name") or "").strip()
            context = str(raw_asset.get("context") or "").strip()
            if len(name) < 2 or not context:
                continue
            category = str(raw_asset.get("category") or "other").strip().lower()
            if category not in {
                "music",
                "brand",
                "artwork",
                "location",
                "product",
                "logo",
                "performance",
                "other",
            }:
                category = "other"
            category = {"logo": "brand", "product": "brand", "performance": "person"}.get(
                category, category
            )
            key = (category, name.casefold())
            if key in seen:
                continue
            seen.add(key)
            start = max(0, int(float(raw_asset.get("start_seconds") or 0)))
            end = max(start, int(float(raw_asset.get("end_seconds") or start)))
            confidence = min(1.0, max(0.0, float(raw_asset.get("confidence") or 0.0)))
            risk_status = str(raw_asset.get("risk_status") or "needs_review")
            if risk_status not in {"high_risk", "needs_review", "insufficient_evidence"}:
                risk_status = "needs_review"
            reason_codes = [str(code) for code in (raw_asset.get("reason_codes") or [])]
            if "video_visual_or_audio_signal" not in reason_codes:
                reason_codes.append("video_visual_or_audio_signal")
            candidates.append(
                CandidateAsset(
                    canonical_name=name[:255],
                    category=category,
                    context=context[:4000],
                    scene_reference=_timestamp(start),
                    source_start=start,
                    source_end=end,
                    extraction_confidence=confidence,
                    risk_status=risk_status,
                    reason_codes=reason_codes[:20],
                )
            )
        return MediaAnalysisOutput(
            transcript=transcript,
            summary=summary,
            candidates=candidates,
            metadata={
                "provider": "vertex_gemini",
                "model_name": model_name,
                "mime_type": mime_type,
                "duration_seconds": duration_seconds,
                "segments": segments[:200],
            },
        )


def _timestamp(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def build_media_analyzer(settings: Settings) -> MediaAnalyzer:
    if settings.agent_mode == "vertex":
        return VertexGeminiMediaAnalyzer(settings)
    return FixtureMediaAnalyzer()
