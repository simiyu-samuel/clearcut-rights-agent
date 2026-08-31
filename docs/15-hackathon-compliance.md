# Hackathon Compliance Checklist

**Project:** ClearCut — AI Rights Clearance for Film and Television
**Selected partner track:** Parallel
**License:** Apache License 2.0 (OSI-approved)
**Hosted environment:** Google Cloud project `clearcut-rights-dev`, region `us-central1`

This document records how the current repository and hosted staging deployment satisfy the material submission requirements. It is an implementation checklist, not a replacement for the official rules.

## Required implementation evidence

| Requirement | ClearCut evidence |
| --- | --- |
| Gemini and Google Cloud agent runtime | `services/api/src/clearcut_api/adk_agent.py` builds a Google ADK `Agent` and Vertex `AdkApp`; `agent_runtime.py` invokes it for live clearance cards. |
| Selected partner runtime | `providers/parallel_api.py` calls Parallel Search and Extract in live mode; research persists request/session provenance and normalized evidence. |
| Google Cloud deployment | Cloud Run hosts the API and web services; Cloud SQL stores state; Cloud Storage stores source/media objects; Secret Manager holds runtime secrets; Cloud Build publishes Artifact Registry images. |
| Human safety boundary | Model output is validated, deterministic risk policy is applied, and the authenticated approval endpoint is the only path that records a rights decision. |
| Public source repository | The GitHub repository contains application source, infrastructure, migrations, tests, fixtures, documentation, and brand assets. |
| OSI-approved license | The top-level `LICENSE` is Apache License 2.0 and does not restrict commercial use. |

The web application is intentionally public at the Cloud Run edge for judging, but application data is protected by Firebase/Identity Platform bearer tokens and tenant-scoped server-side membership checks.

## AI and partner boundaries

ClearCut uses only Google Cloud AI capabilities for model work: Vertex Gemini through Google ADK for clearance-card reasoning and the Google Gen AI SDK for audiovisual analysis. Parallel is used for rights-source Search and Extract. No OpenAI, Anthropic, AWS, or other prohibited model provider is required by the application.

The fixture provider is available for deterministic local tests and failure-resilient demos. The hosted staging configuration uses `PARALLEL_MODE=live` and `AGENT_MODE=vertex`; the UI and demo narration must identify fixture output as fixture output whenever it is used.

## Demo and submission safety

- Use the synthetic screenplay fixture and fictional project data.
- Use only team-owned or synthetic video/audio in the demo.
- Do not include real songs, third-party footage, advertising, third-party logos, or copyrighted screenshots in the judging video or thumbnail.
- Keep the demo video within the official time limit, public, in English or with English subtitles, and show the working hosted URL.
- Show one live Parallel research trace, one evidence-backed card, and one human approval/escalation boundary.
- Do not claim that ClearCut provides legal advice or declares an asset legally cleared.
- Keep API keys, Firebase service-account files, database passwords, OAuth tokens, and Cloud credentials out of Git and the demo recording.

## Final pre-submission checks

1. Verify the public repository URL and top-level `LICENSE` are reachable.
2. Verify the hosted URL loads in a clean browser session and the evaluator can sign up or use the supplied judging account.
3. Verify a fresh workspace can create a project, ingest a synthetic script and media sample, research an asset, record a human decision, and view/download a styled report.
4. Verify the demo recording contains no third-party media or credentials.
5. Confirm the Devpost track, team size, repository URL, hosted URL, Google Cloud products, Parallel usage, license, and contribution description are consistent with this repository.
