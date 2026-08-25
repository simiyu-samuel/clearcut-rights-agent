# ClearCut Operations Runbook

This runbook covers the batch release and the first production-shaped operating procedures. ClearCut is an AI-assisted rights operations system; a human decision remains the release gate for every asset.

## Runtime checks

Use the deployed API URL and verify:

    curl -fsS "$API_URL/health"
    curl -fsS "$API_URL/readyz"
    curl -fsS -H "Authorization: Bearer $ID_TOKEN" -H "X-Organization-ID: $ORGANIZATION_ID" "$API_URL/v1/workspace/overview"

"/health" confirms the process is serving. "/readyz" confirms the database connection is usable. A response header named "x-correlation-id" is returned for every request and should be included when escalating an incident.

## Research recovery

1. Open the project Research panel and inspect the failed angle and its provider request trace.
2. Use **Re-run session** for a complete retry or **Start focused follow-up** for one missing evidence angle.
3. If evidence is stale, open the asset drawer and update its recheck schedule.
4. The due-recheck endpoint can be invoked by a scheduler or operator:

    curl -X POST "$API_URL/v1/research-rechecks/run-due" \
      -H "Authorization: Bearer $ID_TOKEN" \
      -H "X-Organization-ID: $ORGANIZATION_ID"

The endpoint limits one pass to 25 schedules and advances each schedule before work begins, preventing duplicate launches.

## Release and rollback

1. Keep the image tag, Cloud Build ID, migration execution ID, API revision, and web revision together in the release record.
2. Run the database migration job before routing traffic to a new application image.
3. Verify health, readiness, project creation, upload, research, approval, report view, and PDF download.
4. If the new revision is unhealthy, route traffic back to the previous Cloud Run revision. Do not roll back the database without a reviewed reverse migration plan.

## Data protection

- Secrets remain in Secret Manager or local ignored environment files; never commit them.
- Source files and attachments are stored through the object-store abstraction and are not exposed by public review links.
- Review links are hashed at rest, scoped to one project, revocable, and optionally expiring.
- API key secret material is returned only on creation; later list responses expose a prefix and status.
- Report versions are append-only snapshots with a content hash, policy version, and evidence timestamp.
- Identity Platform mode is required for shared environments; demo headers are local-only compatibility behavior.

## Incident record

Record the UTC timestamp, organization, affected project, correlation ID, Cloud Run revision, provider request ID, observed status, action taken, and whether human review was paused. Preserve the relevant report version and research session instead of overwriting evidence.
