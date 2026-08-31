# ClearCut Tooling, Accounts & Credential Readiness Report

**Date:** 2026-08-31
**Status:** Google Cloud, Parallel, Firebase, and hosted staging integrations are configured and exercised

## Executive answer

Yes, ClearCut follows the hackathon phase brief, but selectively. The brief is a menu of possible tools and implementation paths; we do not need to create accounts for every product listed.

Our chosen path is:

```text
Next.js web workspace
        ↓
FastAPI application API
        ↓
Clearance workflow + typed tools
        ↓
Parallel Search / Extract
        ↓
        Google ADK Agent + Vertex ADK runtime with human approval as the safety boundary
```

The current repository has a hosted staging vertical slice. It can upload scripts and media, extract candidate rights-bearing assets, call live Parallel research, generate evidence-backed clearance cards with Gemini through Google ADK, show citations, and record a human approval. Google Cloud project `clearcut-rights-dev`, Parallel, and Firebase/Identity Platform are configured for staging without committing credentials. Fixture mode remains the local default so development and deterministic tests do not depend on live services.

### Current setup checkpoint

- Google Cloud project: `clearcut-rights-dev`;
- billing: active;
- region: `us-central1`;
- Vertex AI, Cloud Run, Cloud Build, Artifact Registry, Secret Manager, Cloud SQL, Cloud Storage, and related APIs: enabled;
- runtime service account: `clearcut-runtime`;
- deployment service account: `clearcut-deployer`, used through impersonation rather than a JSON key;
- Artifact Registry repository: `clearcut` with vulnerability scanning active;
- Parallel secret: `parallel-api-key`, version 1 stored in Secret Manager;
- container packaging: API and web Dockerfiles plus Cloud Build image publishing configuration implemented and locally built successfully.

## 1. What we are using now

| Capability | Current choice | Status | Repository evidence |
|---|---|---|---|
| Web workspace | Next.js + TypeScript | Implemented | `apps/web` |
| API | FastAPI + Python | Implemented | `services/api/src/clearcut_api/main.py` |
| Local persistence | SQLAlchemy + SQLite | Implemented for development | `services/api/src/clearcut_api/models.py` |
| Local file storage | Filesystem object-store abstraction | Implemented for development | `services/api/src/clearcut_api/storage.py` |
| Script intake | UTF-8 Markdown/plain-text upload | Implemented | Upload and analysis endpoints |
| Asset extraction | Deterministic scene-aware extractor | Implemented | `services/api/src/clearcut_api/extraction.py` |
| Partner research | Typed Parallel adapter | Implemented; fixture by default | `services/api/src/clearcut_api/providers/parallel_api.py` |
| Gemini reasoning | Vertex Gemini through Google ADK | Implemented in hosted runtime | `services/api/src/clearcut_api/agent_runtime.py`, `adk_agent.py` |
| ADK / Agent Builder path | ADK `Agent` + Vertex `AdkApp` | Active in hosted clearance workflow | `services/api/src/clearcut_api/adk_agent.py`, `agent_tools.py` |
| Review safety | Clearance cards, approval decisions, audit events | Implemented | `models.py`, `main.py`, review queue UI |
| Cloud deployment | Cloud Run, Cloud SQL, Cloud Storage, Secret Manager | Implemented and exercised in staging | `infra/`, deployment runbook |

## 2. How this maps to the supplied phase brief

### Phase 1 — Core frameworks and environment

We use the Google ADK developer path: the API creates an ADK `Agent`, wraps it in Vertex `AdkApp`, and streams the structured clearance-card response from the hosted Cloud Run service. This satisfies the Google agent runtime requirement without requiring a separately managed Agent Engine resource for the hackathon deployment. Media analysis continues to use the Google Gen AI SDK directly on Vertex because it passes video/audio parts to Gemini. See the [Vertex AI Agent Engine setup guide](https://cloud.google.com/agent-builder/agent-engine/set-up), [Gemini API quickstart](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/quickstart), and [ADK runtime quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime/quickstart-adk).

### Phase 2 — Action mechanisms and data connectivity

We are intentionally not using every GenMedia capability in the brief. ClearCut’s initial problem is rights research, not video generation, music generation, speech generation, or storyboard generation.

Already relevant:

- screenplay/document intake;
- structured source evidence;
- future Gemini document/PDF analysis boundary.

Not required for the current product slice:

- BigQuery Vector Search and LangChain RAG;
- Vertex AI Search data stores;
- Imagen/VFX generation;
- Lyria music generation;
- Gemini TTS;
- video transcription and captioning.

We should only add these if ClearCut expands from screenplay rights review into rough-cut, audio, or visual-asset analysis.

### Phase 3 — Partner integration and infrastructure

Parallel is the selected and implemented partner track. The live adapter calls the documented `/v1/search` and `/v1/extract` endpoints with the server-side `x-api-key` header. The research workflow uses Search to discover leads and Extract to normalize selected sources into persisted evidence. See the [Parallel Search quickstart](https://docs.parallel.ai/search/search-quickstart) and [Search API reference](https://docs.parallel.ai/api-reference/search/search).

We are not currently using IBM, Grafana Labs, ClickHouse, or Replit. They are optional hackathon resources, not dependencies of the ClearCut product decision. Replit is only relevant if we choose it as a hosting/development platform; our planned runtime is Google Cloud.

### Phase 4 — Reasoning, state, and logic hosting

This phase is implemented for the hosted vertical slice:

- workflow state is persisted in SQLAlchemy models;
- research runs and source records are persisted;
- clearance cards require human review;
- approval decisions are append-only and auditable;
- fixture mode makes the workflow deterministic;
- the live clearance-card path uses ADK `Agent` + `AdkApp` and a deterministic risk tool;
- the authenticated workflow owns persistence, Parallel research, and human approval.

Remaining production hardening, outside the hackathon proof, includes:

- persistence-aware multi-step orchestration around the registered tools;
- an evidence-save tool that writes through the authenticated application workflow;
- retryable Cloud Tasks or equivalent worker execution;
- evaluation fixtures for unsupported certainty, source conflict, and prompt injection.

The supplied brief recommends installing `google-cloud-aiplatform[agent_engines,adk]`. The repository installs that optional agent extra in the production API image; fixture mode remains the lightweight local default.

### Phase 5 — Deployment and safety

The safety design is already reflected in the product: research output is evidence, risk is triage, and a human must approve the next action. We also validate Gemini output and reject unsupported claims such as “legally cleared.”

Implemented for staging:

- Cloud Run deployment for the web, API, and migration job;
- Secret Manager references for the database password and Parallel API key;
- Cloud Storage for source documents and media;
- Cloud SQL PostgreSQL migrations;
- Firebase/Identity Platform authentication and tenant-scoped RBAC;
- CORS, correlation IDs, health/readiness endpoints, and human-review safety controls.

Still required before a real production launch: centralized alerting dashboards, durable worker retries/dead letters, rate limits, backup-restore drills, retention policies, and deployment-level policy configuration.

## 3. Accounts and credentials to prepare

### Configured for staging

#### A. Google Cloud account and project

Configured:

- Google Cloud project `clearcut-rights-dev`;
- active billing;
- `us-central1` as the deployment region;
- service accounts and least-privilege deployment bindings;
- no long-lived JSON service-account key.

For the first live Gemini test, enable:

- Vertex AI API: `aiplatform.googleapis.com`;
- Service Usage API: `serviceusage.googleapis.com`;
- IAM Service Account Credentials API: `iamcredentials.googleapis.com`.

For the planned hosted environment, also enable:

- Cloud Run API: `run.googleapis.com`;
- Artifact Registry API: `artifactregistry.googleapis.com`;
- Cloud Build API: `cloudbuild.googleapis.com`;
- Secret Manager API: `secretmanager.googleapis.com`;
- Cloud Storage API: `storage.googleapis.com`;
- Cloud SQL Admin API: `sqladmin.googleapis.com`.

Google’s Agent Runtime quickstart identifies the Agent Platform User role and staging-bucket access as prerequisites. We will use least-privilege bucket/service-account permissions for the actual deployment instead of sharing owner credentials. See [Google’s Agent Runtime quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime/quickstart-adk).

Local authentication should use:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

Do not create or send a long-lived JSON service-account key unless there is no alternative. For Cloud Run, the runtime service account should receive permissions directly and secrets should come from Secret Manager.

#### B. Parallel account and API key

Configured:

- a Parallel Platform account;
- a Parallel API key stored as Secret Manager secret `parallel-api-key`, version 1;
- the API key is not present in the repository or chat.

We will configure:

```bash
PARALLEL_MODE=live
PARALLEL_API_KEY=REDACTED_LOCAL_SECRET
```

The key belongs only on the API/worker side. It must never be sent to the browser, committed to Git, or pasted into chat. Parallel’s documentation explicitly treats the key as a secret and supports creating it from the platform account.

### Already handled

#### C. GitHub

The repository is already available at:

`https://github.com/simiyu-samuel/clearcut-rights-agent`

No additional GitHub credential is needed for the next implementation step unless we add CI/CD deployment workflows.

### Optional later

These are not needed to continue the current ClearCut build:

- Replit account or credits;
- Grafana Cloud account;
- ClickHouse Cloud account;
- IBM Cloud account;
- BigQuery dataset;
- custom domain and TLS certificate;
- Google Workspace/SSO identity provider.

## 4. Configuration we will use after credentials are ready

The local `.env` values will look like this, with secrets kept out of Git:

```dotenv
AGENT_MODE=vertex
GEMINI_MODEL=gemini-2.5-flash
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=us-central1

PARALLEL_MODE=live
PARALLEL_API_KEY=YOUR_PARALLEL_KEY

DATABASE_URL=sqlite:///./.data/clearcut.db
STORAGE_ROOT=.data/uploads
```

For the web app, keep the browser-safe API URL in `apps/web/.env.local`:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_AUTH_MODE=demo
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_FIREBASE_APP_ID=
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=
```

For the shared deployment, switch both API and web auth modes to `identity_platform`, enable the Identity Platform API, configure the Google and Email/Password sign-in providers, and pass the Firebase Web app values through the Cloud Build substitutions documented in [`infra/README.md`](../infra/README.md). The web client supports Google popup sign-in, email/password registration and sign-in, and password reset. Firebase Web app configuration is browser-visible by design; no service-account JSON or refresh token belongs in `.env` or the repository. Firebase's built-in provider is email/password rather than username-only authentication; a separate username mapping can be added later if product requirements call for it.

The last two values remain local-development defaults. For staging/production they will become Cloud SQL and Cloud Storage configuration, with credentials supplied through Google Cloud identity and Secret Manager.

## 5. Exact order of setup

1. Complete container and Cloud Build validation.
2. Provision Cloud Storage and Cloud SQL PostgreSQL.
3. Add migrations and the managed object-store adapter.
4. Deploy the API and web services to Cloud Run with the existing runtime identity and Secret Manager reference.
5. Run a live ADK/Gemini + Parallel smoke test while retaining fixture fallback.
6. Deploy the production-shaped demo and exercise the approval/audit path.

## 6. What you should send back

Safe to share in chat:

- Google Cloud project ID;
- preferred Google Cloud region;
- confirmation that billing or hackathon credits are active;
- confirmation that the Vertex AI API is enabled;
- confirmation that you have a Parallel API key ready.

Do not send:

- Google passwords;
- service-account JSON files;
- `PARALLEL_API_KEY` values;
- OAuth refresh tokens;
- Secret Manager values.

The live integrations are active in staging. A separately managed Agent Engine resource is optional for a later scale-out; the hackathon deployment uses the supported ADK-on-Cloud-Run path.
