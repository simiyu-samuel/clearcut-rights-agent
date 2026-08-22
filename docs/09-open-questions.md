# ClearCut Open Questions and Decisions

This document keeps unresolved implementation choices visible before coding starts. Decisions should be recorded here first, then moved into an ADR when they affect the long-term architecture.

## Required before the first application commit

### 1. GitHub remote

Owner: project team  
Status: waiting for repository URL

Create the public repository using the identity in [repository standards](08-repository-standards.md), then share the URL so the local metadata can be connected and the first planning commit can be pushed.

### 2. Parallel access

Owner: project team  
Status: required

Confirm API credentials, rate limits, and whether the hackathon account supports the needed Search and Extract operations. Keep provider configuration server-side.

### 3. Google Cloud project

Owner: project team  
Status: required

Confirm the project, billing setup, allowed regions, Agent Builder / Gemini access, Cloud Run deployment permissions, Cloud SQL, Cloud Storage, Secret Manager, and logging access.

### 4. Agent integration path

Owner: engineering  
Status: validate during foundation

Test the supported path between Google Cloud Agent Builder / ADK and the typed Parallel tools. Prefer the simplest path that produces a real deployed partner call and remains testable locally.

### 5. Authentication for the demo

Owner: product and engineering  
Status: choose during foundation

Default assumption: a minimal authenticated demo account backed by a replaceable identity adapter. Do not design the data model as single-user even if the first demo uses one account.

## Deliberately deferred decisions

### Rough-cut ingestion

The first release may use timestamped review notes instead of direct video ingestion. Direct video and audio analysis should be added only after the document workflow is stable.

### Email delivery provider

The first release drafts messages but does not send them. A provider and outbox model will be selected before production outreach is enabled.

### Contract storage

The product will track contract metadata and attachments later. It will not interpret or sign agreements in the initial release.

### Multi-region deployment

The first deployment will use one region. Data residency and multi-region strategy must be decided before handling real studio data.

## Working assumptions

- the hackathon accepts a direct Parallel API integration or a supported MCP integration;
- synthetic project material will be used for the public demo;
- all research claims are presented with evidence and uncertainty;
- the first production design uses PostgreSQL and object storage, not a spreadsheet or local JSON file;
- the public repository contains source code and documentation but no secrets or private creative material.

