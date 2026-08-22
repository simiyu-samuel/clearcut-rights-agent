from .config import Settings, settings


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
    return Agent(
        name="clearcut_orchestrator",
        model=runtime_settings.gemini_model,
        instruction=(
            "You are the ClearCut rights-research orchestrator. Work only with registered "
            "application tools and supplied evidence. Produce structured research context "
            "for human review, never legal advice, and never claim that an asset is legally cleared."
        ),
    )
