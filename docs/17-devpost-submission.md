# Devpost submission draft

This is the copy-ready submission draft for ClearCut. Replace the bracketed personal fields before submitting.

## General information

### Project name

ClearCut

### Elevator pitch

ClearCut turns scripts and rough cuts into evidence-backed rights intelligence—finding protected assets, researching ownership with Parallel, and routing every decision to a human reviewer.

### Project status

ClearCut is a new project created for the hackathon and was not an existing project before July 27, 2026.

### Partner track

Parallel

### Team size

[Enter the actual total number of team members.]

## About the project

## Inspiration

Rights clearance is often handled too late and too manually. A producer may discover a song, brand, location, artwork, or other protected element only after it is already embedded in a script, rough cut, or delivery package. The result is a trail of spreadsheets, browser tabs, emails, and uncertainty—exactly when the production needs a confident answer.

We built ClearCut to move that work upstream. It gives production teams a shared workspace where source material becomes a rights-bearing asset inventory, research becomes evidence, and evidence becomes a reviewable next action.

## What it does

ClearCut accepts screenplays, source documents, video, and audio. It extracts candidate rights signals, analyzes media with Gemini on Vertex AI, researches likely ownership and licensing signals through Parallel, and produces an evidence-backed clearance card with risk, confidence, reason codes, sources, and recommended next steps.

The system keeps the consequential decision with a human. A producer, coordinator, or legal reviewer can inspect the evidence, approve or escalate an item, request more research, draft a permission request, and generate a report or branded PDF. Every important action is scoped to the production workspace and recorded in the activity history.

## How we built it

The web workspace is built with Next.js, React, and TypeScript. The API is a Python FastAPI service backed by PostgreSQL through SQLAlchemy and Alembic. Firebase/Google Identity Platform provides sign-in, while the API enforces workspace membership and role-based access.

Parallel powers rights-source discovery and extraction. Google ADK and Vertex Gemini power the clearance-card agent and audiovisual analysis. Cloud Run hosts the web and API services, Cloud SQL stores application state, Cloud Storage stores source documents and media, Secret Manager protects runtime credentials, and Cloud Build publishes versioned images to Artifact Registry.

The hosted workflow is:

```text
Source material → rights-bearing asset inventory → Parallel evidence research
               → Gemini risk and recommendation → human review → report and outreach
```

## What we learned

We learned that useful AI workflow design is as much about boundaries and recovery as it is about model output. Gemini responses need an explicit structured schema, validation, and safe handling when a model response is incomplete. Research needs source provenance, quality signals, retryable failures, and a visible fallback that preserves evidence instead of hiding a failed generation step.

We also learned that production workflows depend on details outside the model: Firebase token verification, tenant-scoped authorization, resumable browser uploads, Cloud Storage CORS, database migrations, PDF rendering, and consistent loading and error states across the UI.

## Challenges we faced

The largest challenge was making a multi-stage research workflow understandable and recoverable. Parallel could return useful evidence even when the downstream model stage failed, so we separated evidence collection from clearance-card generation and introduced a human-review fallback.

Media ingestion introduced a second class of problems: large browser uploads require resumable Cloud Storage sessions, correct CORS configuration, finalization checks, and a workflow that can represent timestamped signals. We also had to make the interface communicate what is ready for action rather than presenting a long, flat page of controls.

## Outcome

ClearCut now supports an authenticated end-to-end workflow: workspace creation, invitations, role-based access, project setup, script and media ingestion, asset analysis, live Parallel research, Gemini clearance cards, human decisions, permission-request drafts, activity history, and styled report/PDF export.

ClearCut is a rights-workflow assistant, not legal advice and not a declaration that an asset is legally cleared. Final clearance remains the responsibility of the production and legal teams.

## Links

- Source repository: https://github.com/simiyu-samuel/clearcut-rights-agent
- Hosted project: https://clearcut-web-lqty2et3xq-uc.a.run.app
- Release: `v1.0.0-hackathon`

## Built with

Google Cloud Run, Google Cloud SQL, Google Cloud Storage, Google Secret Manager, Google Cloud Build, Artifact Registry, Vertex AI, Gemini, Google ADK, Firebase Authentication, Identity Platform, Parallel Search, Parallel Extract, Next.js, React, TypeScript, Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Docker, GitHub, Apache License 2.0.

## Google Cloud products used

- Vertex AI / Gemini for media understanding and clearance-card generation.
- Google ADK and Vertex `AdkApp` for the hosted agent runtime.
- Cloud Run for the web service, API service, and database migration job.
- Cloud SQL for PostgreSQL application state.
- Cloud Storage for private source documents, video, audio, and derived media objects.
- Secret Manager for the database password and Parallel API key reference.
- Cloud Build for reproducible image builds.
- Artifact Registry for versioned container images.
- Firebase Authentication / Google Identity Platform for user authentication.

## Other tools and products used

Parallel Search and Extract, Next.js, React, TypeScript, Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Docker, GitHub, npm, and Ruff.

## Hosted judge walkthrough

1. Open https://clearcut-web-lqty2et3xq-uc.a.run.app.
2. Sign in with Google or email/password.
3. Create or join a workspace.
4. Create a project such as “The Last Signal”.
5. Upload the synthetic screenplay fixture or a team-owned media sample.
6. Start analysis and wait for the review state.
7. Open an extracted asset and run research.
8. Inspect the Parallel evidence and Gemini clearance card.
9. Approve or escalate the item with a human note.
10. Draft a permission request, generate the report, and download the branded PDF.

Use only synthetic or team-owned media during judging. Do not upload real confidential scripts, contracts, credentials, third-party music, or copyrighted footage.

## Submission assets

- Primary logo: `assets/brand/clearcut-logo.png`
- Favicon/app mark: `assets/brand/clearcut-favicon.png`
- Devpost thumbnail: `assets/brand/clearcut-devpost-thumbnail.png`
- Demo script: `docs/07-demo-script.md`
- Compliance checklist: `docs/15-hackathon-compliance.md`
- Open-source license: `LICENSE` (Apache License 2.0)

## Personal form answers

These should be selected truthfully by the submitter:

- First time using IBM tools: [Select the truthful answer]
- First time using Grafana tools: [Select the truthful answer]
- First time using Parallel tools: [Select the truthful answer]
- First time using ClickHouse tools: [Select the truthful answer]
- First time using Replit tools: [Select the truthful answer]

## Contribution description

I designed and built ClearCut end to end, including the product workflow, FastAPI backend, data model and migrations, Google Cloud deployment, Vertex Gemini and Google ADK integration, Parallel research integration, Firebase authentication and workspace RBAC, media ingestion, evidence and review workflow, report/PDF generation, frontend experience, testing, documentation, and hackathon submission materials.
