from collections import defaultdict
from datetime import UTC, datetime

from .models import Asset, ClearanceCard, Project, SourceRecord


def build_clearance_report(
    project: Project,
    assets: list[Asset],
    cards: list[ClearanceCard],
    sources: list[SourceRecord],
) -> str:
    cards_by_asset: dict[str, ClearanceCard] = {}
    for card in cards:
        cards_by_asset.setdefault(card.asset_id, card)
    sources_by_run: dict[str, list[SourceRecord]] = defaultdict(list)
    for source in sources:
        sources_by_run[source.research_run_id].append(source)

    lines = [
        f"# ClearCut clearance report — {project.title}",
        "",
        f"- Project type: {project.project_type}",
        f"- Generated: {datetime.now(UTC).isoformat()}",
        f"- Assets reviewed: {len(assets)}",
        "",
        "> ClearCut provides research and workflow support. This report is not legal advice and does not declare any asset legally cleared.",
        "",
        "## Asset summary",
        "",
        "| Asset | Category | Status | Risk | Confidence | Evidence |",
        "|---|---|---|---:|---:|---:|",
    ]
    for asset in assets:
        card = cards_by_asset.get(asset.id)
        if card is None:
            lines.append(
                f"| {asset.canonical_name} | {asset.category} | {asset.risk_status} | — | — | 0 |"
            )
            continue
        lines.append(
            f"| {asset.canonical_name} | {asset.category} | {card.status} | "
            f"{card.risk_score}/100 | {card.confidence_score:.0%} | {card.evidence_count} |"
        )

    lines.extend(["", "## Detailed review", ""])
    for asset in assets:
        card = cards_by_asset.get(asset.id)
        lines.extend([f"### {asset.canonical_name}", "", f"- Category: {asset.category}"])
        if asset.scene_reference:
            lines.append(f"- Scene: {asset.scene_reference}")
        lines.append(f"- Context: {asset.context}")
        if card is None:
            lines.extend([f"- Current asset status: `{asset.risk_status}`", ""])
            continue
        lines.extend(
            [
                f"- Clearance card status: `{card.status}`",
                f"- Risk score: `{card.risk_score}/100`",
                f"- Confidence: `{card.confidence_score:.0%}`",
                f"- Summary: {card.summary}",
                f"- Recommended next action: {card.recommendation}",
                f"- Reason codes: {', '.join(card.reason_codes) or 'none'}",
                "",
                "Evidence:",
            ]
        )
        for source in sources_by_run.get(card.research_run_id, []):
            lines.append(f"- [{source.title}]({source.url}) — {source.excerpt}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"
