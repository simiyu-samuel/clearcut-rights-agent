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

For a real staging build, also pass the Firebase/Identity Platform browser configuration. These values are public client configuration, not service-account secrets:

```bash
gcloud builds submit \
  --config=infra/cloudbuild-images.yaml \
  --substitutions="_TAG=${BUILD_TAG},_NEXT_PUBLIC_API_URL=${API_URL},_NEXT_PUBLIC_AUTH_MODE=identity_platform,_NEXT_PUBLIC_FIREBASE_API_KEY=${FIREBASE_API_KEY},_NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=${FIREBASE_AUTH_DOMAIN},_NEXT_PUBLIC_FIREBASE_PROJECT_ID=${PROJECT_ID},_NEXT_PUBLIC_FIREBASE_APP_ID=${FIREBASE_APP_ID},_NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=${FIREBASE_MESSAGING_SENDER_ID}" \
  . \
  --project=${PROJECT_ID}
```

## Runtime contract

Cloud Run will provide these values at deploy time:

- `DATABASE_NAME=clearcut` and `DATABASE_USER=clearcut_app`;
- `DATABASE_PASSWORD` from Secret Manager secret `clearcut-db-password`;
- `CLOUD_SQL_CONNECTION_NAME` for the Cloud SQL Unix socket;
- Do not set `DATABASE_URL` in the Cloud Run API image; when the Cloud SQL variables are present, the API resolves the PostgreSQL Unix-socket URL automatically. The SQLite fallback is for local development only.
- `PARALLEL_API_KEY` from Secret Manager secret `parallel-api-key`;
- `STORAGE_BACKEND=gcs`;
- `GCS_BUCKET_NAME=clearcut-rights-dev-assets-<project-number>`;
- `PARALLEL_MODE=live`;
- `AGENT_MODE=vertex`;
- `GOOGLE_CLOUD_PROJECT=clearcut-rights-dev`;
- `GOOGLE_CLOUD_LOCATION=us-central1`.
- `AUTH_MODE=identity_platform`;
- `AUTH_AUDIENCE=clearcut-rights-dev` (or the configured Firebase project audience).

The `clearcut-runtime` service account must remain the runtime identity. No service-account key files belong in the repository or deployment environment.

## Authentication and workspace access

ClearCut verifies Firebase/Identity Platform ID tokens at the API boundary. The token subject is the actor identity; `X-Actor-ID` is ignored in Identity Platform mode. `X-Organization-ID` is only a workspace selector and is accepted only when the verified actor has an active membership in that organization.

Before a real deployment, enable Identity Platform and configure the Google and Email/Password providers in the Firebase/Google Cloud console. The web sign-in screen supports Google popup sign-in, email/password registration and sign-in, and password reset. Firebase's built-in Email/Password provider uses an email address; username-only login would require a separate account-mapping feature.

```bash
gcloud services enable identitytoolkit.googleapis.com --project=${PROJECT_ID}
```

Create a Web app in the Firebase project and copy its public `apiKey`, `authDomain`, `projectId`, `appId`, and (if shown) `messagingSenderId` into the `_NEXT_PUBLIC_FIREBASE_*` Cloud Build substitutions. These values are safe to expose in a browser bundle; server credentials and refresh tokens are not.

The first authenticated user can create an organization from the web onboarding screen and is made its `admin`. Administrators invite teammates from Workspace settings by email and role; when the invited person signs in with that email, ClearCut automatically activates the membership. Firebase actor IDs remain an internal implementation detail and are never required in the UI. The local development contract remains explicit demo mode (`AUTH_MODE=demo` and `NEXT_PUBLIC_AUTH_MODE=demo`); do not use that mode for a shared or production deployment.

## Database migrations

The schema is versioned with Alembic. Run migrations only against an explicitly selected environment:

```bash
alembic -c services/api/alembic.ini upgrade head
```

The command reads the effective database configuration from the environment, including the Cloud SQL Unix-socket settings used by Cloud Run.
