# ClearCut Batch Release Plan

**Status:** local implementation complete; awaiting one release cycle

This release train intentionally keeps staging unchanged while the remaining product waves are implemented and validated together. The release gate is one push, one container build, one database migration, one Cloud Run deployment, and one end-to-end staging journey.

## Release train scope

### Wave 2 — research depth

- category-specific rights playbooks;
- scheduled evidence rechecks with explicit freshness state;
- re-run and focused follow-up controls;
- provider request/session provenance;
- source quality, conflict, and evidence-gap signals;
- recoverable provider failure states.

### Wave 3 — team accountability

- organization and membership records;
- producer, coordinator, legal reviewer, post supervisor, viewer, and admin roles;
- tenant-scoped role enforcement on mutations;
- asset owners, priorities, due dates, and next actions;
- internal comments and mentions;
- notifications;
- activity/audit viewer;
- delivery-readiness gate.

### Wave 4 — recurring production operations

- screenplay version numbers and source-span diffing;
- permission-request lifecycle and response metadata;
- project and asset attachments;
- scoped external review links;
- API-key and webhook endpoint primitives;
- correlation IDs and operational request tracing;
- immutable report metadata, decision log, and evidence snapshot.

## Release gate

Before the single deployment cycle:

1. run Alembic from the current deployed revision to head against a clean PostgreSQL-compatible test database;
2. run API linting and all workflow/authorization tests;
3. run the TypeScript check and optimized Next.js build;
4. run the deployed-journey smoke test using a fresh project and fixture screenplay;
5. verify CORS retains both Cloud Run web origins;
6. verify `/health`, `/readyz`, workspace overview, delivery readiness, review history, reports, and PDF download;
7. push once and record the release commit, build ID, image tag, migration execution, API revision, and web revision.

## Product boundary

ClearCut remains an AI-assisted rights operations workspace. Recommendations, evidence, and workflow state do not constitute legal advice or a legal clearance decision. Human approval and source rechecks remain explicit release gates.
