# ClearCut Roadmap and Backlog

## 1. Delivery strategy

We will build one polished vertical slice first, then expand around stable domain boundaries. The hackathon release must be real and demonstrable; it should not create architectural debt that makes production hardening impossible.

## 2. Release plan

### Phase 0 — foundation

- repository and branch conventions;
- application skeleton;
- environment configuration;
- database migration baseline;
- CI checks;
- design tokens and navigation shell;
- sample project fixtures;
- provider adapter contract.

### Phase 1 — hackathon vertical slice

- create project;
- upload screenplay;
- parse and store document version;
- extract candidate assets;
- research music, brand, location, and artwork examples;
- display evidence-backed asset board;
- calculate deterministic triage status;
- record human approval;
- draft permission request;
- export clearance report;
- deploy to Google Cloud;
- record the live Parallel call for the demo.

### Phase 2 — production foundation

- organization and membership model;
- RBAC enforcement;
- resumable jobs and retry visibility;
- document and research version history;
- source freshness and recheck;
- audit event browsing;
- object retention and deletion workflow;
- outbound email outbox;
- health checks and dashboards;
- staging and production deployment pipelines.

### Phase 3 — production workspace

- rough-cut timeline and timestamped observations;
- subtitle and localization review;
- configurable policy engine;
- rights request and response tracking;
- attachments and contract metadata;
- external reviewer portal;
- API keys and webhooks;
- enterprise SSO;
- organization analytics.

## 3. Prioritized backlog

### Foundation

- `FOUND-001` Add application monorepo structure.
- `FOUND-002` Add environment schema and validation.
- `FOUND-003` Add CI for formatting, linting, tests, and dependency checks.
- `FOUND-004` Add PostgreSQL migration tooling.
- `FOUND-005` Add Cloud Storage abstraction.
- `FOUND-006` Add correlation ID and structured logging.

### Projects and documents

- `DOC-001` Create project and project settings.
- `DOC-002` Upload and version a source document.
- `DOC-003` Parse supported screenplay formats.
- `DOC-004` Store scenes and source spans.
- `DOC-005` Reject unsafe or unsupported uploads.

### Asset intelligence

- `ASSET-001` Define asset categories and normalization.
- `ASSET-002` Extract candidate rights-bearing assets.
- `ASSET-003` Deduplicate mentions across document versions.
- `ASSET-004` Support user correction of extracted assets.

### Parallel integration

- `PAR-001` Define typed provider adapter interface.
- `PAR-002` Implement live Search operation.
- `PAR-003` Implement live Extract operation.
- `PAR-004` Implement research task with timeout and retry.
- `PAR-005` Normalize citations and evidence.
- `PAR-006` Add fixture provider for local development.
- `PAR-007` Add live smoke test and documented credentials setup.

### Risk and review

- `RISK-001` Implement policy versioning.
- `RISK-002` Implement deterministic risk and confidence calculation.
- `RISK-003` Display reason codes and source evidence.
- `REVIEW-001` Add approval task and decision history.
- `REVIEW-002` Prevent unauthorized status changes.

### Outreach and reporting

- `OUT-001` Draft permission request from approved facts.
- `OUT-002` Add human approval before sending.
- `REPORT-001` Generate clearance report.
- `REPORT-002` Add report download and immutable report metadata.

### Hardening

- `HARD-001` Add tenant isolation tests.
- `HARD-002` Add prompt-injection fixtures.
- `HARD-003` Add retry and dead-letter handling.
- `HARD-004` Add audit event viewer.
- `HARD-005` Add health, readiness, and provider dependency checks.
- `HARD-006` Add backup, restore, and incident runbooks.

## 4. Hackathon execution window

The brief shows 19 days to the deadline. A practical sequence is:

- Days 1–2: foundation, schema, design shell;
- Days 3–5: document intake and extraction;
- Days 6–8: Parallel adapter and evidence model;
- Days 9–11: risk board and review flow;
- Days 12–13: report and outreach draft;
- Days 14–15: deployment and runtime integration proof;
- Days 16–17: testing, polish, and failure states;
- Day 18: record demo and write submission;
- Day 19: buffer for fixes and final verification.

## 5. Definition of done

A feature is done only when:

- the happy path works through the UI and API;
- authorization and tenant scope are enforced;
- errors are visible and recoverable;
- structured logs and correlation IDs exist;
- tests cover business rules and failure paths;
- documentation explains local and hosted behavior;
- no secrets or generated artifacts are committed;
- the feature is demonstrated in the deployed environment when applicable.

