import os

from .agent_tools import CLEARANCE_AGENT_TOOLS, REGISTERED_AGENT_TOOLS
from .config import Settings, settings


def _configure_vertex_environment(runtime_settings: Settings) -> None:
    """Configure ADK's Google Gen AI client for Vertex AI before app creation."""
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
    if runtime_settings.google_cloud_project:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", runtime_settings.google_cloud_project)
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", runtime_settings.google_cloud_location)


def build_root_agent(agent_settings: Settings | None = None):
    """Build the optional Google ADK/Agent Builder entry point.

    The application workflow remains the source of truth for persistence and approvals;
    this entry point gives a hosted ADK deployment a narrow orchestration shell.
    """
    try:
        from google.adk.agents import Agent
    except ImportError as exc:
        raise RuntimeError(
            "Install services/api with the optional 'agent' extra to use Google ADK"
        ) from exc

    runtime_settings = agent_settings or settings
    _configure_vertex_environment(runtime_settings)
    return Agent(
        name="clearcut_orchestrator",
        model=runtime_settings.gemini_model,
        instruction=(
            "You are the ClearCut rights-research orchestrator. Work only with registered "
            "application tools and supplied evidence. Produce structured research context "
            "for human review, never legal advice, and never claim that an asset is legally cleared."
        ),
        tools=REGISTERED_AGENT_TOOLS,
    )


def build_clearance_agent(agent_settings: Settings | None = None):
    """Build the production clearance-card agent used by the API workflow.

    Parallel research and persistence stay in the authenticated application
    workflow. The ADK agent turns that evidence into a structured explanation,
    while the deterministic risk tool keeps operational triage policy-aware.
    """
    try:
        from google.adk.agents import Agent
        from google.genai.types import GenerateContentConfig
    except ImportError as exc:
        raise RuntimeError(
            "Install services/api with the optional 'agent' extra to use Google ADK"
        ) from exc

    runtime_settings = agent_settings or settings
    _configure_vertex_environment(runtime_settings)
    return Agent(
        name="clearcut_clearance_agent",
        description="Creates evidence-backed, human-reviewable rights triage cards.",
        model=runtime_settings.gemini_model,
        instruction=(
            "You are ClearCut's rights-clearance triage agent. Use only the supplied "
            "asset and evidence. Call calculate_clearance_risk with the asset category, "
            "evidence count, and extraction reason codes before writing the result. "
            "Return only a JSON object with summary, recommendation, risk_score, "
            "confidence_score, reason_codes, and needs_human_review. The latter must "
            "always be true. This is workflow support, not legal advice: never claim "
            "that an asset is legally cleared and never invent an owner, license, or "
            "legal conclusion."
        ),
        tools=CLEARANCE_AGENT_TOOLS,
        generate_content_config=GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0,
        ),
    )


def build_clearance_app(agent_settings: Settings | None = None):
    """Wrap the live clearance agent in the Google Vertex ADK runtime."""
    try:
        from vertexai.agent_engines import AdkApp
    except ImportError as exc:
        raise RuntimeError(
            "Install the optional agent extra to use the Google Vertex ADK runtime"
        ) from exc
    return AdkApp(agent=build_clearance_agent(agent_settings))


def build_agent_engine_app(agent_settings: Settings | None = None):
    """Wrap the ADK root agent for deployment to Vertex AI Agent Engine."""
    try:
        from vertexai.agent_engines import AdkApp
    except ImportError as exc:
        raise RuntimeError(
            "Install the optional agent extra to package an Agent Engine application"
        ) from exc
    return AdkApp(agent=build_root_agent(agent_settings))
