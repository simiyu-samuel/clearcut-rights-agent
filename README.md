# ClearCut

**AI rights clearance for film and television.**

<p align="center">
  <img src="assets/brand/clearcut-logo.png" alt="ClearCut logo" width="620">
</p>

<p align="center"><em>Turn scripts and rough cuts into evidence-backed rights plans.</em></p>

![ClearCut Devpost thumbnail](assets/brand/clearcut-devpost-thumbnail.png)

ClearCut turns a screenplay, shot list, or rough cut into a structured rights-clearance plan. It identifies potentially protected assets, researches likely ownership and licensing signals, ranks risk with explainable evidence, and prepares the next human-approved action.

> ClearCut helps teams prepare and manage rights-clearance work. It does not provide legal advice or declare an asset legally cleared.

## Project status

This repository contains a deployed staging vertical slice for the Agentic Cinema hackathon. The Google Cloud and Parallel integrations are connected, and the production-shaped research, review, permission-work, audit, and reporting flows have been exercised end to end.

The latest local changes include styled report/PDF rendering fixes and submission brand assets. Real user authentication, the tabbed project workspace, and video-analysis ingestion are the next development tracks; deployment is intentionally paused until the video milestone is complete. See [CONTRIBUTING.md](CONTRIBUTING.md) for repository conventions, [docs/12-batch-release-plan.md](docs/12-batch-release-plan.md) for the release gate, and [docs/13-operations-runbook.md](docs/13-operations-runbook.md) for operating procedures.

## Primary partner track

**Parallel** — used for web search, content extraction, deep research, and monitoring of rights-related sources. See the [partner-track decision record](docs/decisions/0001-partner-track.md).

## Product flow

```text
Script / shot list / rough cut
          ↓
Rights-bearing asset inventory
          ↓
Evidence-backed research
          ↓
Risk and confidence assessment
          ↓
Human review and approval
          ↓
Clearance report + outreach actions
```

## Planning documents

- [Product brief](docs/01-product-brief.md)
- [Technical brief](docs/02-technical-brief.md)
- [Architecture](docs/03-architecture.md)
- [Data model](docs/04-data-model.md)
- [Security and privacy](docs/05-security-privacy.md)
- [Roadmap and backlog](docs/06-roadmap.md)
- [Hackathon demo script](docs/07-demo-script.md)
- [Repository standards](docs/08-repository-standards.md)
- [Open questions and decisions](docs/09-open-questions.md)
- [Partner-track decision](docs/decisions/0001-partner-track.md)
- [Tooling, accounts, and credential readiness report](docs/10-tooling-and-credentials-report.md)
- [Deployment infrastructure](infra/README.md)
- [Batch release plan](docs/12-batch-release-plan.md)
- [Operations runbook](docs/13-operations-runbook.md)

## Brand assets

- [Primary logo](assets/brand/clearcut-logo.png)
- [Favicon and app mark](assets/brand/clearcut-favicon.png)
- [Devpost submission thumbnail](assets/brand/clearcut-devpost-thumbnail.png)

## License

ClearCut is released under the Apache License 2.0. See [LICENSE](LICENSE).
