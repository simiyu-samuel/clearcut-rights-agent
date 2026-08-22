# ClearCut Repository Standards

## 1. Proposed repository identity

**Repository name:** `clearcut-rights-agent`  
**Description:** `Production-ready AI rights clearance workspace for film and TV: extract rights-bearing assets from scripts and cuts, research ownership and licensing signals with Parallel, manage risk, evidence, approvals, and outreach.`

## 2. Proposed structure

```text
clearcut-rights-agent/
├── apps/
│   ├── web/                 # Next.js user workspace
│   └── api/                 # FastAPI and agent entrypoint
├── packages/
│   ├── contracts/           # Shared schemas and API contracts
│   ├── ui/                  # Shared UI components
│   └── config/              # Shared lint and TypeScript configuration
├── services/
│   └── workers/             # Async jobs and provider tasks
├── infra/                   # Cloud Run, Cloud SQL, storage, and CI definitions
├── migrations/              # Database migrations
├── fixtures/                # Synthetic scripts, sources, and evaluation cases
├── docs/                    # Product and technical documentation
├── scripts/                 # Safe developer and release utilities
├── .env.example
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## 3. Branches and commits

- default branch: `main`;
- short-lived branches: `feat/`, `fix/`, `docs/`, `chore/`;
- commit messages should be imperative and scoped where useful;
- one coherent change per commit;
- never commit secrets, customer content, or generated build output.

Suggested format:

```text
feat(research): add Parallel evidence normalization
fix(review): prevent cross-tenant approval lookup
docs(architecture): record async job state machine
```

## 4. Pull request expectations

Every pull request should include:

- problem and intended behavior;
- screenshots or a short recording for UI changes;
- tests added or the reason no test is needed;
- migration and rollback notes;
- security and privacy impact;
- documentation updates;
- confirmation that fixture mode and live mode are not confused.

## 5. Required checks

- formatting;
- linting;
- type checking;
- unit and workflow tests;
- dependency audit;
- secret scanning;
- container scan;
- migration validation;
- build verification.

## 6. Environment policy

All runtime configuration must be supplied by environment variables or managed secret references. `.env.example` may document variable names and safe placeholders only.

## 7. Documentation policy

Architectural decisions belong in `docs/decisions/`. Product behavior belongs in the product brief. Operational procedures belong in runbooks. If code behavior changes, update the relevant document in the same pull request.

