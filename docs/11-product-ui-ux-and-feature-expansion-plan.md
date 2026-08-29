# ClearCut Product, UI/UX, and Feature Expansion Plan

**Status:** Batch release train implemented locally; staging deployment intentionally deferred until the single release cycle
**Date:** 2026-08-24  
**Purpose:** Turn the working ClearCut backend into a credible production workspace and a stronger hackathon submission.

## 1. Executive assessment

The current ClearCut vertical slice proves the most important technical idea:

1. a screenplay can be ingested;
2. rights-bearing assets can be extracted;
3. Parallel can research evidence;
4. Vertex/Gemini can produce an explainable clearance card;
5. a human can record a decision; and
6. the system can produce a report.

That is a strong foundation. The current weakness is product presentation and workflow depth. The UI still feels like a functional prototype around a sophisticated backend. A producer, clearance coordinator, or lawyer needs more than an AI result: they need a command center, clear ownership, evidence confidence, next actions, history, collaboration, and professional deliverables.

The next goal is not to add random screens. It is to make the core workflow feel inevitable:

> Intake → inventory → research → triage → human decision → permission work → delivery report.

Every screen should help a production answer three questions:

- What needs attention now?
- Why does ClearCut believe that?
- What action should happen next, and who owns it?

## 2. Product positioning

ClearCut should be presented as an **AI-assisted rights operations workspace**, not as a chatbot or a legal-answer generator.

The winning narrative is:

> ClearCut converts creative material into an auditable rights plan. It combines agentic research, evidence provenance, deterministic policy signals, and human approval so productions can move toward distribution with fewer surprises.

This gives us four differentiators:

1. **Evidence-first intelligence:** every meaningful conclusion has sources, excerpts, retrieval time, and confidence.
2. **Human-controlled decisions:** the system recommends; authorized people approve, escalate, reject, or request more research.
3. **Production workflow:** tasks, owners, deadlines, outreach drafts, audit history, and reports live in one workspace.
4. **Agentic research:** the system can decompose a clearance question, search, extract, compare sources, identify gaps, and propose the next research step.

## 3. Current gaps to address

### 3.1 UI and UX gaps

- The dashboard does not yet feel like an operational command center.
- The project page mixes intake, review, inventory, evidence, and activity without a clear hierarchy.
- The next action is not always obvious after analysis or approval.
- Review cards are dense and require too much scrolling.
- Filters, sorting, search, bulk operations, and saved views are missing.
- Status is not sufficiently connected to an explicit workflow explanation.
- The system needs stronger empty, loading, partial, retry, and failure states.
- The organization context is visual only; membership and roles are not yet real.
- Activity and audit history are not yet first-class surfaces.

### 3.2 Reporting gaps

- Markdown is currently rendered as raw text rather than a designed report.
- The PDF needs a branded, print-ready layout rather than a text dump.
- Reports need a cover, executive summary, risk breakdown, asset table, evidence sections, decision history, and disclaimer.
- Users need report version history and a clear generated-at timestamp.
- A user should be able to view a report before downloading it.
- Reports should preserve the exact data snapshot used to generate them.

### 3.3 Workflow gaps

- Project status needs to reflect actual asset and decision state.
- Assets need owners, due dates, priority, and a next-action type.
- Research needs explicit re-run, retry, compare, and stale-source handling.
- Decisions need notes, actor identity, timestamp, and history in the UI.
- Permission requests need a lifecycle: draft, internal review, approved to send, sent, response received, closed.
- There is no delivery-readiness view that summarizes blockers and unresolved risk.

### 3.4 Production-readiness gaps

- Real organization and membership model is still pending.
- Role-based access control is needed for producers, coordinators, legal reviewers, and administrators.
- Jobs need durable state, retry visibility, idempotency, and dead-letter handling.
- Observability needs correlation IDs, structured events, provider latency, and failure dashboards.
- Policy and territory logic need to become configurable rather than embedded in UI assumptions.

## 4. Target information architecture

### Workspace navigation

- **Overview:** operational dashboard for the organization.
- **Projects:** searchable project list with status, deadline, blockers, and last activity.
- **Review queue:** cross-project queue of assets requiring human attention.
- **Research:** provider runs, source quality, stale evidence, failures, and rechecks.
- **Reports:** report history, generated snapshots, downloads, and delivery packages.
- **Activity:** audit trail and decision history.
- **Settings:** organization, members, roles, policies, territories, integrations, and retention.

### Project navigation

- **Command center:** project health, deadlines, blockers, recent activity, and next actions.
- **Script and versions:** uploaded documents, versions, diffs, source spans, and analysis jobs.
- **Rights inventory:** all extracted assets with filtering and bulk actions.
- **Review queue:** cards needing human decisions.
- **Research:** research runs, source comparison, gaps, and re-run controls.
- **Requests:** permission requests, contacts, drafts, status, and responses.
- **Reports:** report versions and delivery exports.
- **Audit:** immutable project activity and decision log.

## 5. UI/UX redesign direction

### 5.1 Design language

Use a bright editorial/production aesthetic with strong structure and restrained decoration:

- strong typographic hierarchy;
- larger, more useful data density;
- restrained color semantics;
- consistent status tokens;
- clear primary action per screen;
- responsive layouts for laptop and tablet;
- accessible contrast and keyboard focus states;
- fewer placeholder numbers and decorative activity entries.

Status colors should have stable meaning:

| State | Meaning | Suggested treatment |
|---|---|---|
| Draft | Setup incomplete | Neutral gray |
| Active | Processing or research underway | Blue |
| Review | Human action required | Gold |
| Blocked | Cannot move forward | Red |
| Complete | Current review scope resolved | Green |
| Stale | Evidence needs recheck | Purple/blue |

### 5.2 Overview dashboard

Replace the current static stat grid with an operational dashboard containing:

- projects by status;
- assets requiring attention;
- high-risk and blocked counts;
- evidence coverage;
- overdue actions;
- research failures and stale sources;
- recent decisions;
- recent project activity;
- “Continue where you left off” project cards;
- a prominent **Start review** or **Open queue** action.

The first viewport should answer the producer’s question: “What can stop distribution this week?”

### 5.3 Project command center

Redesign the project page into a clear three-level hierarchy:

1. **Project header:** title, format, territories, distribution modes, release target, status, and primary action.
2. **Health strip:** total assets, unresolved assets, high-risk assets, evidence coverage, overdue tasks, and report readiness.
3. **Work area:** queue, inventory, research activity, requests, and timeline.

Add a project-level action rail:

- Upload new version
- Start or resume analysis
- Run research
- Assign review
- Generate report
- Mark delivery review complete

### 5.4 Rights inventory

Add a data-table view alongside the current cards:

- asset name;
- category;
- scene or timestamp;
- risk status;
- confidence;
- evidence count;
- owner;
- due date;
- next action;
- last researched;
- review status.

Required interactions:

- search by asset, scene, source text, or category;
- filter by risk, status, owner, territory, and evidence state;
- sort by risk, due date, confidence, or latest activity;
- bulk assign, bulk research, bulk export, and bulk status action;
- open a right-side detail drawer without losing table context.

### 5.5 Asset detail drawer

Every asset should have a dedicated detail experience with tabs or sections:

- **Context:** exact script excerpt, scene, document version, and extraction confidence.
- **Risk:** deterministic signals, model explanation, policy version, and unresolved questions.
- **Evidence:** source cards, excerpts, source quality, retrieval date, and conflicts.
- **Research:** run history, query, objective, provider status, retry, re-run, and compare.
- **Decision:** current status, prior decisions, notes, actor, timestamp, and next action.
- **Requests:** permission drafts, contacts, responses, and attachments.

The primary action should be contextual: **Research again**, **Request permission**, **Escalate to legal**, **Approve next action**, or **Resolve as not applicable**.

### 5.6 Review queue

The review queue should behave like a focused work inbox:

- “Needs my decision” as the default view;
- queue count and estimated effort;
- keyboard-friendly next/previous navigation;
- sticky evidence panel;
- clear decision buttons with consequences;
- required note for escalation or rejection;
- next card action after saving;
- bulk low-risk approvals only when policy permits;
- explicit “not legal advice” boundary near the decision control.

### 5.7 Activity and audit

Add an activity timeline with human-readable events:

- document uploaded;
- analysis completed;
- asset extracted or corrected;
- research started, completed, failed, or retried;
- evidence changed;
- decision recorded;
- permission request drafted, approved, sent, or responded to;
- report generated and downloaded.

Each event should link to the affected object and preserve actor, timestamp, and correlation ID.

## 6. Report experience plan

### 6.1 Styled web report

The report viewer should be a designed document, not a raw Markdown block.

Recommended structure:

1. **Cover:** ClearCut branding, project title, project type, territories, distribution modes, release target, report version, and generated timestamp.
2. **Executive summary:** readiness, unresolved blockers, high-risk count, evidence coverage, and recommended next actions.
3. **Risk overview:** visual counts by risk/status category.
4. **Asset register:** sortable table with asset, category, scene, risk, confidence, evidence, owner, and decision.
5. **Detailed clearance cards:** summary, recommendation, reason codes, evidence excerpts, and source links.
6. **Permission work:** open requests, drafts, owners, and response status.
7. **Decision log:** who decided what, when, and with which note.
8. **Method and limitations:** research providers, policy version, evidence timestamp, and human-review disclaimer.

The web view should support:

- print preview;
- expand/collapse asset details;
- risk filters;
- evidence link validation indicators;
- report version selector;
- “download PDF” and “download Markdown” actions.

### 6.2 Production PDF

The PDF should use a dedicated document template:

- branded cover page;
- page numbers and project title in the header/footer;
- consistent typography and spacing;
- risk badges and tables;
- repeated table headers across pages;
- evidence URLs wrapped safely;
- no raw Markdown syntax;
- generated timestamp and report ID;
- disclaimer on the cover or final page;
- accessible text rather than a screenshot of the web page.

The PDF must represent an immutable report snapshot. Regenerating should create a new report version rather than silently replacing the old one.

### 6.3 Report data model additions

Plan for:

- report version number;
- generated-by actor;
- policy version;
- source snapshot timestamp;
- content hash;
- report status;
- download audit events;
- optional delivery package containing PDF, Markdown, evidence manifest, and decision log.

## 7. Agentic and Parallel expansion

We should use more of the research workflow, but only where it creates visible product value. The goal is not to make more calls; it is to produce better, traceable clearance work.

### Current foundation

- typed provider adapter;
- live Parallel search;
- extract/normalize source evidence;
- provider request IDs;
- source records stored in the database;
- fixture provider for deterministic development.

### Next Parallel-backed capabilities

#### A. Research plan generation

Before searching, create a structured plan:

- rights question;
- asset category;
- likely rights types;
- territories;
- distribution modes;
- required evidence;
- stopping conditions;
- escalation conditions.

#### B. Multi-angle search

For one asset, run separate research angles such as:

- official owner or publisher;
- licensing or permissions page;
- territory-specific rights information;
- contact or request channel;
- usage restrictions;
- conflicting ownership signals.

Store each angle as a child research task under one research session.

#### C. Source quality and conflict detection

Classify sources by quality and detect when:

- official and third-party sources disagree;
- evidence is about a similar name rather than the exact asset;
- a page is editorial, historical, or informational rather than a permission source;
- the source is stale;
- ownership is inferred but not confirmed.

#### D. Research gaps and rechecks

The agent should return explicit gaps such as:

- composition owner unknown;
- master recording owner unknown;
- physical location not identified;
- territory not covered;
- source does not establish permission;
- evidence older than the configured freshness window.

The UI should offer **Re-run missing evidence** rather than forcing a full restart.

#### E. Rights-specific playbooks

Add playbooks for:

- music: composition, master, sync, performance, lyrics;
- brands: trademark, logo, trade dress, implied endorsement;
- locations: filming permission, property release, visible third-party works;
- artwork: creator, publisher, display, reproduction, background use;
- people: likeness, publicity, name use, archival footage;
- sports and organizations: marks, league rights, association risk.

Each playbook should define required evidence and recommended next actions.

#### F. Scheduled source rechecks

For active projects, allow a user to recheck sources before delivery. A recheck should show what changed rather than overwriting the original evidence.

### Important boundary

We should not claim unsupported Parallel capabilities in the product. The provider adapter should expose only verified operations and keep a fixture implementation for demos and tests. Any new capability must have:

- typed request and response contracts;
- timeout and retry behavior;
- provider request ID;
- stored evidence;
- failure state;
- user-visible explanation.

## 8. Collaboration and organization features

These features make ClearCut worth using beyond a demo:

- organization and project membership;
- roles: producer, coordinator, legal reviewer, post supervisor, administrator;
- assignment and due dates;
- comments and mentions on assets;
- internal notes separated from report-facing notes;
- approval gates;
- saved filters and personal queues;
- notification center;
- external legal-review link with scoped access;
- immutable audit log;
- data retention and project archive controls.

## 9. Production workflow features

### Document and versioning

- multiple screenplay versions;
- diff assets across versions;
- preserve source spans and line references;
- identify new, removed, changed, and resolved assets;
- re-run only affected research.

### Permission requests

- contact records;
- request templates by asset category;
- territory, term, media, and usage fields;
- attachments;
- internal approval before sending;
- outbound email outbox;
- response tracking;
- reminders and expiry dates.

### Delivery readiness

Provide a production-facing readiness view:

- clear for delivery;
- approved with conditions;
- pending permission;
- legal escalation;
- unresolved evidence;
- stale research;
- missing releases;
- owner and deadline for every blocker.

## 10. Prioritized execution plan

### Wave 1 — Product polish and reporting foundation

Highest value for the next demo and immediate credibility.

- redesign dashboard around real operational metrics;
- add project health strip and explicit next-action banner;
- redesign review cards and asset detail drawer;
- add inventory table, filters, and search;
- build styled web report viewer;
- build branded PDF template;
- add report version history;
- eliminate all hardcoded placeholder activity and metrics;
- add loading, empty, error, retry, and provider-failure states.

**Exit criteria:** a judge can understand the project state, inspect evidence, make a decision, and download a professional report without explanation from the presenter.

### Wave 2 — Research depth and agent transparency

- [x] research sessions and multi-angle tasks;
- [x] research plan visible before execution;
- [x] source quality and evidence-gap indicators;
- [x] re-run/recheck control for a new research pass;
- [x] structured conflict signals and focused missing-evidence follow-ups;
- [ ] scheduled source rechecks;
- right-sized category playbooks;
- provider trace panel for demo mode and admin mode.

**Exit criteria:** the system visibly demonstrates agentic research rather than a single opaque search request.

### Wave 3 — Collaboration and accountability

- organizations and members;
- roles and permissions;
- owners, due dates, comments, and mentions;
- review inbox and notifications;
- audit event viewer;
- approval gates and delivery readiness.

**Exit criteria:** a real production team can divide work and prove who made each decision.

### Wave 4 — Production depth

- screenplay version diffing;
- rough-cut timestamp observations;
- permission request lifecycle;
- contract and attachment metadata;
- scheduled evidence rechecks;
- external legal-review portal;
- webhooks, API keys, and integrations;
- observability, rate limits, backups, and incident workflows.

**Exit criteria:** ClearCut supports recurring production operations rather than a one-time analysis demo.

## 11. Recommended immediate build slice

For the next implementation cycle, build one polished vertical slice in this order:

1. **Project command center:** health strip, status explanation, blockers, and primary next action.
2. **Inventory table and asset drawer:** filters, search, source context, and decision history.
3. **Review workspace:** compact cards, evidence panel, decision controls, and next-card navigation.
4. **Styled report viewer:** executive summary, risk matrix, asset table, evidence, and decision log.
5. **Branded PDF:** matching the report viewer with page layout and stable snapshot metadata.
6. **Research session panel:** show Parallel query angles, status, sources, gaps, and re-run action.
7. **Demo polish:** loading states, failure recovery, accessibility, responsive behavior, and no placeholder values.

This slice directly improves judging impact while strengthening the architecture for the larger production roadmap.

## 12. Definition of done for the UI/UX expansion

A feature is complete only when:

- the user can discover the next action without narration;
- all numbers are real or explicitly marked unavailable;
- the happy path and provider failure path are designed;
- evidence is visible next to the decision it supports;
- the UI distinguishes recommendation from human approval;
- report output is professional in both web and PDF forms;
- report versions are reproducible and traceable;
- keyboard, responsive, and accessibility basics are covered;
- API, frontend, and contracts are tested;
- the feature works against the deployed staging environment;
- no generated data or fake activity is presented as production truth.

## 13. Winning demo story after this plan

The final experience should demonstrate a producer opening ClearCut and seeing:

1. a project health score with real blockers;
2. a prioritized queue of rights issues;
3. an asset opened with script context and evidence side by side;
4. Parallel research decomposed into visible evidence tasks;
5. a clear uncertainty or conflict instead of false confidence;
6. a human approval and permission-request workflow;
7. a polished delivery report and PDF;
8. an audit trail showing how the decision was reached.

That story makes the backend, agent, partner integration, and product design reinforce each other. It is much stronger than showing isolated API calls or a plain text export.
