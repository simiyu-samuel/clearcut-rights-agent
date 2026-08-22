# ClearCut Tooling, Accounts & Credential Readiness Report

**Date:** 2026-08-22  
**Status:** Ready for account setup; live cloud and partner credentials are not configured yet

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
Gemini on Vertex AI, with human approval as the safety boundary
```

The current repository already has a working fixture-mode vertical slice. It can upload a screenplay, extract candidate rights-bearing assets, run fixture research, create an evidence-backed clearance card, show citations, and record a human approval. The live integrations are deliberately disabled by default so local development and judging do not depend on credentials.

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
| Gemini reasoning | Google Gen AI SDK Vertex path | Implemented as optional runtime path | `services/api/src/clearcut_api/agent_runtime.py` |
| ADK / Agent Builder path | Registered root-agent tools + Agent Engine wrapper | Scaffolded, not deployed | `services/api/src/clearcut_api/adk_agent.py`, `agent_tools.py` |
| Review safety | Clearance cards, approval decisions, audit events | Implemented | `models.py`, `main.py`, review queue UI |
| Cloud deployment | Cloud Run / Agent Engine | Not implemented yet | Next infrastructure milestone |

## 2. How this maps to the supplied phase brief

### Phase 1 — Core frameworks and environment

We selected the custom developer SDK route, not the low-code route. The current `VertexGeminiClearanceAgent` uses `google-genai` with Vertex AI configuration, while the ADK file provides the hosted-agent entry point. Google’s current Agent Engine setup documentation separates the Agent Engine and ADK dependencies from the basic Gemini SDK, so we will add the deployment SDK when we implement hosted deployment. See the [Vertex AI Agent Engine setup guide](https://cloud.google.com/agent-builder/agent-engine/set-up), [Gemini API quickstart](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/quickstart), and [ADK runtime quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime/quickstart-adk).

What is not done yet:

- no Google Cloud project is connected to the application;
- no live Gemini request has been run from this repository;
- registered ADK tools exist, but they are not yet deployed or connected to a hosted Agent Engine runtime;
- no Agent Engine resource has been deployed.

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

Parallel is the selected and implemented partner track. The live adapter calls the documented `/v1/search` and `/v1/extract` endpoints with the server-side `x-api-key` header. The current workflow uses Search; Extract is implemented as an adapter and will be wired into the multi-step research workflow next. See the [Parallel Search quickstart](https://docs.parallel.ai/search/search-quickstart) and [Search API reference](https://docs.parallel.ai/api-reference/search/search).

We are not currently using IBM, Grafana Labs, ClickHouse, or Replit. They are optional hackathon resources, not dependencies of the ClearCut product decision. Replit is only relevant if we choose it as a hosting/development platform; our planned runtime is Google Cloud.

### Phase 4 — Reasoning, state, and logic hosting

We have the beginnings of this phase:

- workflow state is persisted in SQLAlchemy models;
- research runs and source records are persisted;
- clearance cards require human review;
- approval decisions are append-only and auditable;
- fixture mode makes the workflow deterministic.

Still required for the full phase:

- persistence-aware multi-step orchestration around the registered tools;
- an evidence-save tool that writes through the authenticated application workflow;
- `AdkApp` packaging and Agent Engine deployment;
- retryable Cloud Tasks or equivalent worker execution;
- production PostgreSQL and object storage;
- evaluation fixtures for unsupported certainty, source conflict, and prompt injection.

The supplied brief recommends installing `google-cloud-aiplatform[agent_engines,adk]`. The current repository keeps `google-adk` and `google-genai` in an optional local agent extra so the fixture-mode API stays lightweight. Before hosted deployment, we will align the deployment environment with Google’s current Agent Engine SDK guidance rather than treating the local scaffold as deployed infrastructure.

### Phase 5 — Deployment and safety

The safety design is already reflected in the product: research output is evidence, risk is triage, and a human must approve the next action. We also validate Gemini output and reject unsupported claims such as “legally cleared.”

Not yet implemented:

- Cloud Run deployment;
- Secret Manager retrieval;
- Cloud Logging/Trace dashboards and alerting;
- Cloud Storage for source documents;
- Cloud SQL PostgreSQL migrations;
- production identity/RBAC;
- managed safety settings and deployment-level policy configuration.

## 3. Accounts and credentials to prepare

### Required now

#### A. Google Cloud account and project

Please prepare:

- a Google account with permission to create or use a Google Cloud project;
- one Google Cloud project ID for development/staging;
- billing enabled, or approved hackathon credits attached;
- preferred region, with `us-central1` as our current default;
- permission to enable APIs and create service accounts.

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

Please prepare:

- a Parallel Platform account;
- a Parallel API key for the ClearCut application;
- any hackathon partner credits or quota associated with the account.

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

The last two values remain local-development defaults. For staging/production they will become Cloud SQL and Cloud Storage configuration, with credentials supplied through Google Cloud identity and Secret Manager.

## 5. Exact order of setup

1. Create or select the Google Cloud project and attach billing/credits.
2. Enable Vertex AI API and complete local ADC authentication.
3. Create the Parallel account and API key.
4. Put the values into a local ignored `.env` file; do not send the secret values in chat.
5. We install the hosted Agent Engine dependencies and connect the registered ClearCut ADK tools to the persistence-aware workflow.
6. We run a live Gemini + Parallel smoke test while retaining fixture fallback.
7. We provision Cloud Storage, Cloud SQL, Secret Manager, Cloud Run, and a staging service account.
8. We deploy the full workflow and run the production-shaped demo.

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

Once the project ID, region, and credential readiness are confirmed, we can make the live integrations active and move into Agent Engine deployment.
