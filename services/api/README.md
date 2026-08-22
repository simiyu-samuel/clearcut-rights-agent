# ClearCut API

The API is the server-side foundation for projects, analysis jobs, typed provider tools, and future agent workflows.

## Local development

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e 'services/api[dev]'
uvicorn clearcut_api.main:app --app-dir services/api/src --reload
```

The API will be available at `http://localhost:8000`. OpenAPI documentation is available at `/docs`.

## Current foundation

- `/healthz` and `/readyz` operational endpoints;
- tenant-scoped project creation, listing, and retrieval;
- secure UTF-8 screenplay/Markdown upload endpoint;
- queued analysis-run endpoint with scene-aware deterministic asset extraction;
- project asset inventory endpoint;
- asynchronous research-run endpoint with fixture and live-capable Parallel adapters;
- normalized source records with provider request IDs;
- SQLAlchemy persistence with SQLite development default;
- typed provider protocol and deterministic Parallel fixture provider;
- tests for health, tenant isolation, extraction, analysis, and provider normalization.

Set `PARALLEL_MODE=live` and provide `PARALLEL_API_KEY` to use the documented Parallel v1 Search/Extract API adapter. Fixture mode is the default for local development and demo resilience.
