# ClearCut Product Brief

**Status:** Pre-build planning  
**Date:** 2026-08-22  
**Primary partner:** Parallel  
**Product category:** Media production operations / rights intelligence

## 1. Vision

ClearCut is the rights-clearance workspace for modern film and television teams. It turns creative material into a traceable inventory of rights questions, research evidence, decisions, and follow-up actions.

The product should make a producer feel that a difficult clearance review has become an organized production task—not an opaque AI answer.

## 2. Problem

Rights work is usually performed late, manually, and across disconnected tools. A production may discover songs, logos, artwork, archival clips, locations, or people in a script or rough cut without having a reliable record of:

- what was found;
- where it appears;
- who may control it;
- what evidence supports that conclusion;
- what territory, medium, or term is affected;
- who owns the next action; and
- whether a human has approved the decision.

The cost of missing one item can include re-editing, delayed distribution, a failed launch window, or legal exposure.

## 3. Product promise

Given a project document or media review input, ClearCut will:

1. find candidate rights-bearing assets;
2. preserve their scene and source context;
3. research public evidence and likely rights contacts;
4. show uncertainty instead of inventing certainty;
5. route decisions to the right human; and
6. maintain an audit trail from source material to final clearance status.

## 4. Target users

### Producer / production manager

Needs a fast project-level view of clearance risk, blockers, owners, and deadlines.

### Clearance coordinator

Needs to review extracted assets, research sources, request permission, and track responses.

### Entertainment lawyer / legal reviewer

Needs evidence, provenance, version history, and an explicit boundary between research and legal judgment.

### Post-production supervisor

Needs to know whether an edit, subtitle, music cue, or graphic can move toward delivery.

### Studio administrator

Needs organization-level access control, retention, audit, and reporting.

## 5. Core use cases

### A. Script intake

Upload a screenplay or treatment. ClearCut identifies possible music, brands, locations, artwork, archival material, named organizations, and people.

### B. Rough-cut review

Create or import timestamped observations from a rough cut. Associate visual or audible observations with scenes and assets.

### C. Research and evidence collection

Search public sources for likely owners, licensing pages, official contacts, territorial information, and relevant usage conditions. Every material finding must retain its source URL, retrieval time, and evidence excerpt.

### D. Risk triage

Assign a status such as `high_risk`, `needs_review`, `likely_clear`, `blocked`, or `insufficient_evidence` using explainable rules and model-supported classification.

### E. Approval workflow

A qualified human reviews the evidence, records a decision, adds notes, and accepts or rejects the proposed next action.

### F. Outreach preparation

Draft a permission request using project details, intended use, territory, term, media, and asset context. Sending remains human-approved.

### G. Delivery report

Export a clearance report for internal review, legal handoff, or distribution delivery.

## 6. Scope by release

### Release 0: planning foundation

- repository standards and documentation;
- product, architecture, and security decisions;
- partner integration contract;
- sample project and synthetic fixtures.

### Release 1: hackathon vertical slice

- project creation;
- screenplay upload;
- text extraction and asset inventory;
- Parallel-backed research for selected asset categories;
- evidence-backed risk board;
- human approval of an asset decision;
- draft outreach email;
- exportable clearance report;
- deployed Google Cloud demo with visible partner runtime calls.

### Release 2: production foundation

- multi-tenant organization model;
- role-based access control;
- asynchronous, resumable research jobs;
- document versioning and diffing;
- source freshness and recheck workflows;
- audit log and approval history;
- email provider integration with outbox and delivery tracking;
- API and webhook surface;
- monitoring, rate limits, backups, and disaster recovery procedures.

### Release 3: production-grade workspace

- rough-cut and subtitle review;
- scene-level visual and audio observations;
- configurable risk policies by territory and distribution medium;
- rights request and response tracking;
- contract and attachment metadata;
- organization-level analytics;
- external review portal;
- localization and internationalization;
- enterprise SSO and policy controls.

## 7. Non-goals and safety boundaries

ClearCut will not:

- provide legal advice;
- state that an asset is legally cleared without an authorized human decision;
- sign contracts or grant rights automatically;
- infer ownership solely from one weak source;
- bypass paywalls, access private systems, or collect personal data unnecessarily;
- send outreach without explicit user approval;
- silently overwrite a previous research result or decision.

## 8. Product principles

1. **Evidence before confidence.** A conclusion without provenance is incomplete.
2. **Uncertainty is a first-class output.** “Unknown” is safer than an invented answer.
3. **Human decisions are explicit.** The system records who decided, when, and based on what.
4. **The workflow is the product.** Chat can accelerate work, but the source of truth is the project workspace.
5. **Async by default.** Research may take time and must survive retries, refreshes, and partial failures.
6. **Least privilege.** Agents receive only the tools and project context required for the current task.

## 9. Success measures

### Hackathon measures

- a reviewer can go from upload to a populated clearance board in one session;
- every displayed research finding has a source and retrieval timestamp;
- the demo visibly executes a real Parallel call from deployed code;
- the agent completes a deterministic multi-step workflow;
- the output is understandable to a producer without technical explanation.

### Production measures

- time from intake to first reviewable asset inventory;
- percentage of assets with usable evidence;
- percentage of decisions with complete audit history;
- research recheck success rate;
- human correction rate for extracted asset categories;
- average time from asset identification to assigned action;
- failure and retry rates for asynchronous jobs;
- user-reported trust and usefulness.

