# ClearCut deployment infrastructure

The repository contains the first production packaging layer:

- `services/api/Dockerfile` builds the FastAPI service as a non-root container;
- `apps/web/Dockerfile` builds the Next.js workspace using standalone output;
- `cloudbuild-images.yaml` builds and pushes both images to Artifact Registry.

The Cloud Build file intentionally stops after image publishing. Cloud SQL and Cloud Storage must be provisioned before Cloud Run is deployed so the service never relies on an ephemeral SQLite filesystem or local uploads in a production environment.

## Build images

From the repository root:

```bash
gcloud builds submit \
  --config=infra/cloudbuild-images.yaml \
  --substitutions=_TAG=manual-$(date +%Y%m%d%H%M%S),_NEXT_PUBLIC_API_URL=http://localhost:8000 \
  . \
  --project=clearcut-rights-dev
```

For a deployed web service, replace `_NEXT_PUBLIC_API_URL` with the public ClearCut API URL before building the web image. The browser API URL is compiled into the Next.js client bundle.

## Runtime contract

Cloud Run will provide these values at deploy time:

- `DATABASE_URL` from the managed PostgreSQL configuration;
- `DATABASE_NAME=clearcut` and `DATABASE_USER=clearcut_app`;
- `DATABASE_PASSWORD` from Secret Manager secret `clearcut-db-password`;
- `CLOUD_SQL_CONNECTION_NAME` for the Cloud SQL Unix socket;
- `PARALLEL_API_KEY` from Secret Manager secret `parallel-api-key`;
- `STORAGE_BACKEND=gcs`;
- `GCS_BUCKET_NAME=clearcut-rights-dev-assets-<project-number>`;
- `PARALLEL_MODE=live`;
- `AGENT_MODE=vertex`;
- `GOOGLE_CLOUD_PROJECT=clearcut-rights-dev`;
- `GOOGLE_CLOUD_LOCATION=us-central1`.

The `clearcut-runtime` service account must remain the runtime identity. No service-account key files belong in the repository or deployment environment.
