# ClearCut Security and Privacy Plan

## 1. Security posture

ClearCut processes unpublished creative material and potentially sensitive business information. The default posture is private, tenant-isolated, least-privilege, auditable, and conservative about uncertainty.

## 2. Threat model

### Untrusted documents

Uploaded files may contain malicious payloads, macros, embedded scripts, oversized content, or prompt-injection text.

Controls:

- MIME and extension validation;
- file size and page limits;
- malware scanning before processing;
- sandboxed parsing workers;
- no execution of embedded document content;
- content treated as data, never as system instructions;
- source document hash and version tracking.

### Untrusted web content

Web pages may contain prompt injection, misleading claims, malicious links, or stale information.

Controls:

- retrieve only through the server-side provider adapter;
- separate retrieved content from agent instructions;
- never execute instructions found in source content;
- allowlist action tools independently of research content;
- store URLs and excerpts for human verification;
- flag source conflicts and weak evidence.

### SSRF and unsafe URLs

The application must not allow arbitrary server-side fetching outside the approved research provider. If user-supplied URLs are supported later, validate schemes, block private address ranges, enforce egress policy, and use an isolated fetcher.

### Credential exposure

- keep all credentials in Secret Manager;
- never send provider keys to the browser or model context;
- redact secrets from logs and error messages;
- rotate keys and support revocation;
- use separate credentials per environment.

### Tenant data leakage

- organization ID required in every repository query;
- authorization checked before object access;
- signed, short-lived download URLs;
- no cross-tenant analytics by default;
- tenant-isolation tests in CI.

### Unauthorized action

Sending an email, changing an approval, deleting a document, or modifying a policy requires an authenticated user and explicit authorization. The agent may prepare an action but cannot silently execute it.

## 3. Identity and access

Initial roles:

- `owner`: organization and billing configuration;
- `producer`: project and workflow management;
- `clearance_coordinator`: research, asset review, and outreach drafts;
- `legal_reviewer`: approval and policy review;
- `viewer`: read-only access.

The architecture should be compatible with OIDC and enterprise SSO even if the hackathon demo uses a simpler sign-in flow.

## 4. Data classification

### Confidential

Scripts, treatments, rough-cut notes, contracts, unreleased titles, and internal project plans.

### Restricted

Credentials, access tokens, private contact details, and legal correspondence.

### Public or externally sourced

Public source URLs and publicly available evidence excerpts, subject to provider and source terms.

Logs must never contain full scripts, full model prompts containing confidential content, credentials, or unnecessary personal data.

## 5. Human and legal boundaries

The UI must visibly label the product as a research and workflow assistant. Risk labels describe operational triage, not legal status. Final clearance decisions and contractual interpretation remain with an authorized human or legal advisor.

## 6. Operational controls

- structured audit events for access, research, decisions, exports, and outreach;
- rate limiting per organization and provider;
- retries with bounded backoff;
- dead-letter queue for failed jobs;
- backups and restore testing;
- dependency, secret, and container scanning;
- incident response runbook;
- documented retention and deletion processes.

