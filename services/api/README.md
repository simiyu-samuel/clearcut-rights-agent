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
- queued analysis-run endpoint;
- SQLAlchemy persistence with SQLite development default;
- typed provider protocol and deterministic Parallel fixture provider;
- tests for health, tenant isolation, and job creation.

The live Parallel adapter and document-analysis worker are intentionally the next implementation milestone.
