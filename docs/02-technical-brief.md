# ClearCut Technical Brief

**Status:** Implementation baseline with production hardening in progress
**Primary requirement:** Gemini + Google Cloud Agent Builder + Parallel runtime integration

## 1. Technical goals

The system must be:

- demonstrably functional in a hosted environment;
- deterministic enough for a high-stakes research workflow;
- asynchronous and resumable for production workloads;
- tenant-aware from the first persistence model;
- observable at the job, tool, and agent-step level;
- safe around untrusted documents and web content;
- replaceable at the integration boundaries.

## 2. Recommended stack

### Web application

- Next.js and TypeScript;
- accessible component system;
- server-side session enforcement;
- responsive project workspace UI;
- no secrets or partner credentials in the browser.

### API and agent runtime

- Python service using FastAPI;
- Google Agent Development Kit / Google Cloud Agent Builder integration;
- Gemini model calls through the approved Google Cloud runtime;
- deterministic fixture agent for local development and judging resilience;
- explicit workflow state machine around agent steps;
- typed tool contracts using Pydantic models.

The current research workflow persists Parallel evidence, creates a clearance card, and pauses at `pending_review`. `AGENT_MODE=vertex` routes card generation through the Google Gen AI SDK on Vertex AI; `adk_agent.py` provides the optional Google ADK hosted-agent entry point. Neither mode can mark an asset as legally cleared. A human approval endpoint records the decision, transitions the internal workflow state, and writes an audit event.

### Persistence

- Cloud SQL for PostgreSQL for transactional application data;
- Cloud Storage for original documents, derived artifacts, and reports;
- optional PostgreSQL full-text or vector retrieval only where it materially improves document navigation;
- no source document content stored in logs.

### Async execution

- Cloud Tasks for bounded, retryable work;
- Pub/Sub for domain events and future integrations;
- job records in PostgreSQL as the source of truth;
- idempotency keys on every external research operation.

### Hosting and operations

- Cloud Run for the web and API services;
- Secret Manager for credentials;
- Cloud Logging, Error Reporting, and Trace-compatible correlation IDs;
- CI checks on every pull request;
- separate development, staging, and production configuration.

## 3. Partner integration strategy

Parallel is the core external research capability. Its documented platform includes Search, Extract, Task, and Monitor-style workflows. The application should hide the provider behind a typed adapter so the product workflow does not depend on raw SDK response shapes.

### Integration modes

1. **Primary judging path:** a typed Parallel client invoked by the deployed agent tools.
2. **MCP path:** use the supported Parallel remote MCP integration when it is compatible with the selected Google Cloud agent runtime.
3. **Local development fallback:** a recorded fixture mode that makes the UI and workflow testable without live credentials. Fixture mode must be visibly labelled and must never be presented as a live partner call.

The repository must include an integration test or smoke command that proves the live path is imported and called in code.

### Tool surface

The agent should have narrow tools rather than unrestricted internet access:

- `search_rights_sources`
- `extract_rights_source`
- `run_rights_research_task`
- `create_source_monitor`
- `save_research_evidence`
- `calculate_clearance_risk`
- `draft_permission_request`
- `request_human_approval`

Only the first four call Parallel. The remaining tools are internal, deterministic application tools.

## 4. Agent design

### Orchestrator

The orchestrator receives a user goal and a project context, then runs an allowed workflow. It may choose among typed tools, but it cannot invent an unregistered action.

### Asset extraction specialist

Finds candidate rights-bearing entities and records their source span, scene, category, and extraction confidence.

### Research specialist

Chooses an appropriate Parallel operation, gathers source material, and returns structured evidence rather than a free-form answer.

### Risk specialist

Applies policy rules to the structured asset and evidence records. Gemini may explain the result, but the status is calculated from explicit rules.

### Outreach specialist

Drafts a permission request from approved project facts. It cannot send messages or alter clearance status.

### Review coordinator

Creates approval tasks, tracks human decisions, and prevents downstream actions when required review is incomplete.

## 5. Deterministic risk model

Each asset receives:

- `risk_status`;
- `risk_score` from 0 to 100;
- `confidence_score` from 0 to 1;
- `reason_codes`;
- evidence references;
- required next action.

Initial rules should consider:

- asset category;
- whether an owner is identified;
- whether a source is official or authoritative;
- number and agreement of sources;
- intended territory;
- intended distribution medium;
- duration and prominence of use;
- commercial versus editorial context;
- source freshness;
- unresolved conflicting evidence.

Example policy:

```text
high_risk = protected_category AND owner_unknown
high_risk = commercial_brand AND prominent_use
needs_review = owner_found AND licensing_terms_unclear
likely_clear = public_domain_signal AND authoritative_evidence AND human_approved
insufficient_evidence = evidence_count == 0 OR source_conflict == true
```

These are triage rules, not legal conclusions.

## 6. API boundaries

The first API should expose resource-oriented endpoints:

```text
POST   /v1/projects
GET    /v1/projects/{project_id}
POST   /v1/projects/{project_id}/documents
POST   /v1/projects/{project_id}/analysis-runs
GET    /v1/projects/{project_id}/assets
GET    /v1/projects/{project_id}/clearance-cards
GET    /v1/assets/{asset_id}
GET    /v1/assets/{asset_id}/clearance-card
POST   /v1/assets/{asset_id}/research-runs
POST   /v1/assets/{asset_id}/approvals
POST   /v1/assets/{asset_id}/outreach-drafts
GET    /v1/projects/{project_id}/reports/{report_id}
GET    /v1/jobs/{job_id}
```

All mutating endpoints must be authenticated, tenant-scoped, idempotent where retries are possible, and recorded in the audit log.

## 7. Job state machine

```text
queued → running → awaiting_review → completed
                  ↘ failed → retryable / abandoned
```

Research jobs may have child tasks. A parent job cannot be marked complete until required child tasks have either completed or been explicitly waived by an authorized user.

## 8. Testing strategy

### Unit tests

- parsers and asset normalization;
- risk rules;
- source quality and confidence calculations;
- permission request templates;
- access-control policies.

### Contract tests

- Parallel adapter request and response schemas;
- Google agent tool schemas;
- storage and queue boundaries;
- webhook signatures.

### Workflow tests

- upload to asset inventory;
- research retry and partial failure;
- conflicting sources;
- human rejection and re-review;
- report generation.

### Evaluation tests

Maintain a labelled fixture set of scripts and expected asset categories. Track extraction precision, recall, unsupported certainty, citation coverage, and human correction rate.

## 9. Production-readiness requirements

- structured logs with `tenant_id`, `project_id`, `job_id`, `run_id`, and `trace_id`;
- retry budgets and dead-letter handling;
- request timeouts and provider rate-limit handling;
- encrypted storage and transport;
- database migrations with rollback notes;
- backups and restore verification;
- dependency and container scanning;
- feature flags for provider and model changes;
- redacted observability payloads;
- an incident runbook;
- clear retention and deletion behavior.
