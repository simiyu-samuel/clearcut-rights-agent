from dataclasses import dataclass


@dataclass(frozen=True)
class RiskPolicyResult:
    risk_score: int
    reason_codes: list[str]
    recommendation: str


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


def calculate_risk(
    category: str, evidence_count: int, extraction_reason_codes: list[str] | None = None
) -> RiskPolicyResult:
    risk_score, reason_code, recommendation = _GUIDANCE.get(
        category,
        (
            50,
            "category_specific_review",
            "Confirm the rights position with the relevant rights holder.",
        ),
    )
    if evidence_count == 0:
        reason_code = "insufficient_evidence"
    return RiskPolicyResult(
        risk_score=risk_score,
        reason_codes=[reason_code, *(extraction_reason_codes or [])],
        recommendation=recommendation,
    )


def calculate_confidence(evidence_count: int) -> float:
    return min(0.95, 0.35 + (0.2 * evidence_count)) if evidence_count else 0.2
