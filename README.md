# ClearCut

**AI rights clearance for film and television.**

ClearCut turns a screenplay, shot list, or rough cut into a structured rights-clearance plan. It identifies potentially protected assets, researches likely ownership and licensing signals, ranks risk with explainable evidence, and prepares the next human-approved action.

> ClearCut helps teams prepare and manage rights-clearance work. It does not provide legal advice or declare an asset legally cleared.

## Project status

This repository is in the pre-build planning phase for the Agentic Cinema hackathon. The initial release will target a credible end-to-end vertical slice; the architecture and backlog are intentionally designed to grow into a production-grade, multi-tenant workspace.

The implementation foundation is now in progress. See [CONTRIBUTING.md](CONTRIBUTING.md) for repository conventions and [docs/06-roadmap.md](docs/06-roadmap.md) for the delivery sequence.

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

## License

ClearCut is released under the Apache License 2.0. See [LICENSE](LICENSE).
