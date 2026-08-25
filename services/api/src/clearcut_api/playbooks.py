from typing import TypedDict


class RightsPlaybook(TypedDict):
    rights_questions: list[str]
    required_evidence: list[str]
    recommended_actions: list[str]
    escalation_signals: list[str]


PLAYBOOKS: dict[str, RightsPlaybook] = {
    "music": {
        "rights_questions": [
            "Who controls the composition and publishing rights?",
            "Who controls the master recording?",
            "Does the intended use require sync, master, performance, or lyric permissions?",
        ],
        "required_evidence": [
            "Composition or publisher identity",
            "Master recording or label identity",
            "Licensing/contact path",
            "Territory, media, term, and usage scope",
        ],
        "recommended_actions": [
            "Confirm composition and master rights holders",
            "Prepare a sync and master-use permission request",
            "Escalate lyrics or performance rights questions to legal",
        ],
        "escalation_signals": [
            "Multiple rights holders likely",
            "Commercial recording used in a prominent scene",
            "Territory or term restrictions are unclear",
        ],
    },
    "brand": {
        "rights_questions": [
            "Is the mark or trade dress identifiable?",
            "Could the use imply sponsorship or endorsement?",
            "Is the appearance editorial, incidental, or commercial?",
        ],
        "required_evidence": [
            "Trademark or brand owner",
            "Usage context and prominence",
            "Permission or editorial-use rationale",
            "Territory and distribution scope",
        ],
        "recommended_actions": [
            "Document context and prominence",
            "Request brand review where endorsement risk exists",
            "Escalate prominent or negative portrayals to legal",
        ],
        "escalation_signals": [
            "Implied endorsement",
            "Negative or controversial portrayal",
            "Logo is central to the scene",
        ],
    },
    "location": {
        "rights_questions": [
            "Who controls the property or filming location?",
            "Is a property release or filming permit required?",
            "Are visible third-party works or marks included?",
        ],
        "required_evidence": [
            "Owner or location authority",
            "Filming permission or property release",
            "Production dates and territory",
            "Third-party works visible in frame",
        ],
        "recommended_actions": [
            "Confirm the property release and permit",
            "Log visible works as separate assets",
            "Escalate restrictions on commercial or public locations",
        ],
        "escalation_signals": [
            "Private property",
            "Controlled venue or public landmark",
            "Release terms do not cover intended distribution",
        ],
    },
    "artwork": {
        "rights_questions": [
            "Who created or publishes the artwork?",
            "Is the work incidental, displayed, reproduced, or featured?",
            "Does the intended use exceed an existing display permission?",
        ],
        "required_evidence": [
            "Creator or copyright owner",
            "Publisher, gallery, or collection record",
            "Display/reproduction permission path",
            "Scene prominence and framing",
        ],
        "recommended_actions": [
            "Confirm display and reproduction scope",
            "Request permission or replace the artwork",
            "Separate featured artwork from incidental background use",
        ],
        "escalation_signals": [
            "Artwork is featured or reproduced",
            "Ownership is disputed",
            "Commercial or promotional use is planned",
        ],
    },
    "person": {
        "rights_questions": [
            "Is a real person identifiable?",
            "Does the use involve likeness, name, voice, or archival material?",
            "Is a release or consent already available?",
        ],
        "required_evidence": [
            "Identity and source context",
            "Release or consent record",
            "Likeness/name/voice usage scope",
            "Territory and media coverage",
        ],
        "recommended_actions": [
            "Confirm release status",
            "Attach the signed release metadata",
            "Escalate publicity or defamation concerns",
        ],
        "escalation_signals": [
            "Person is identifiable",
            "Portrayal is sensitive or negative",
            "Archival footage or voice is used",
        ],
    },
}


def playbook_for(category: str) -> RightsPlaybook:
    return PLAYBOOKS.get(
        category,
        {
            "rights_questions": ["Who controls the asset and what permission covers the intended use?"],
            "required_evidence": ["Rights holder", "Permission path", "Territory and usage scope"],
            "recommended_actions": ["Confirm the rights position with the relevant rights holder"],
            "escalation_signals": ["Ownership or permission is unclear"],
        },
    )
