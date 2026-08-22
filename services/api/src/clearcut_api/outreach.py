from .models import Asset, ClearanceCard, Project


def build_outreach_draft(
    project: Project, asset: Asset, card: ClearanceCard, recipient_hint: str
) -> tuple[str, str]:
    subject = f"Rights inquiry: {asset.canonical_name} — {project.title}"
    body = f"""Hello,

We are preparing the project “{project.title}” and are reviewing the rights position for the following reference:

Asset: {asset.canonical_name}
Category: {asset.category}
Scene/context: {asset.context}
Intended project type: {project.project_type}

Could you please confirm the appropriate rights contact and advise on the permissions or licensing process for this use? We would also appreciate confirmation of any territory, term, media, attribution, or fee requirements.

This is an information request only and is not a representation that the use is cleared. Our production team will review and document any permission before making a final decision.

Thank you,
ClearCut production workspace
"""
    return subject, body
