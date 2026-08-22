import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateAsset:
    canonical_name: str
    category: str
    context: str
    scene_reference: str | None
    source_start: int
    source_end: int
    extraction_confidence: float
    risk_status: str
    reason_codes: list[str]


def _category_for_context(name: str, before: str, after: str) -> tuple[str, str, list[str]]:
    name_lowered = name.lower()
    before_lowered = before.lower()
    after_lowered = after.lower()
    local_context = f"{before_lowered} {name_lowered} {after_lowered}"

    if "radio plays" in before_lowered[-35:] or any(
        token in before_lowered[-45:] for token in ("song", "music", "track")
    ):
        return "music", "high_risk", ["copyrighted_music_signal"]
    if any(
        token in after_lowered[:70] for token in ("menu", "logo", "brand", "signage", "product")
    ):
        return "brand", "needs_review", ["commercial_brand_signal"]
    if "station" in name_lowered or "outside the" in before_lowered[-45:]:
        return "location", "needs_review", ["location_permission_signal"]
    if any(
        token in after_lowered[:70]
        for token in ("poster", "photograph", "painting", "artwork", "wall")
    ):
        return "artwork", "needs_review", ["third_party_artwork_signal"]
    if any(
        token in after_lowered[:70] for token in ("team", "organization", "club", "sports", "won")
    ):
        return "organization", "needs_review", ["organization_reference_signal"]

    context = local_context
    lowered = context.lower()
    if any(token in lowered for token in ("song", "music", "radio", "track", "plays")):
        return "music", "high_risk", ["copyrighted_music_signal"]
    if any(token in lowered for token in ("brand", "logo", "menu", "sign", "product")):
        return "brand", "needs_review", ["commercial_brand_signal"]
    if any(
        token in lowered for token in ("location", "outside", "station", "café", "cafe", "platform")
    ):
        return "location", "needs_review", ["location_permission_signal"]
    if any(token in lowered for token in ("poster", "photograph", "painting", "artwork", "wall")):
        return "artwork", "needs_review", ["third_party_artwork_signal"]
    if any(token in lowered for token in ("team", "organization", "club", "sports", "won")):
        return "organization", "needs_review", ["organization_reference_signal"]
    return "other", "insufficient_evidence", ["unclassified_named_asset"]


def _scene_at(position: int, scene_matches: list[re.Match[str]]) -> str | None:
    current = None
    for match in scene_matches:
        if match.start() <= position:
            current = match.group(1)
        else:
            break
    return current


def extract_candidate_assets(text: str) -> list[CandidateAsset]:
    """Extract explicitly named assets from screenplay-style Markdown or plain text.

    This deterministic extractor is a safe foundation for evaluation and fixtures.
    A future Gemini extractor can produce the same CandidateAsset contract.
    """
    scene_matches = list(re.finditer(r"^##\s+Scene\s+([\w-]+).*?$", text, re.MULTILINE))
    emphasis_matches = list(
        re.finditer(r"\*\*(?P<name>[^*\n]{2,120})\*\*|“(?P<quote>[^”\n]{2,120})”", text)
    )
    candidates: list[CandidateAsset] = []
    seen: set[tuple[str, str]] = set()

    for match in emphasis_matches:
        name = (match.group("name") or match.group("quote") or "").strip()
        if not name:
            continue
        context_start = max(0, match.start() - 100)
        context_end = min(len(text), match.end() + 100)
        before = text[max(0, match.start() - 70) : match.start()]
        after = text[match.end() : min(len(text), match.end() + 70)]
        context = " ".join(text[context_start:context_end].split())
        category, risk_status, reason_codes = _category_for_context(name, before, after)
        key = (category, name.casefold())
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            CandidateAsset(
                canonical_name=name,
                category=category,
                context=context,
                scene_reference=_scene_at(match.start(), scene_matches),
                source_start=match.start(),
                source_end=match.end(),
                extraction_confidence=0.96,
                risk_status=risk_status,
                reason_codes=reason_codes,
            )
        )

    return candidates
