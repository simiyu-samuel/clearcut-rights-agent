# ADR 0001: Select the Parallel Partner Track

**Status:** Accepted  
**Date:** 2026-08-22

## Context

ClearCut needs a partner integration that is central to a real media workflow, visible in a short demo, and useful beyond a one-off chatbot. The hackathon allows tracks for IBM, Grafana Labs, Parallel, ClickHouse, and Replit.

## Decision

Select **Parallel** as the primary partner track.

ClearCut will use Parallel for rights-related search, source extraction, deep research, and future source monitoring. The integration will be implemented behind a typed provider adapter and exposed to the agent through narrow tools.

## Rationale

- rights clearance is fundamentally an evidence and research workflow;
- Parallel's search and extraction capabilities map directly to the core user problem;
- the value of the partner call is visible in the product output, not hidden in infrastructure;
- the workflow naturally supports citations, freshness, and source conflict handling;
- the track enables a cinematic demo while still solving enterprise friction.

## Alternatives considered

### Grafana Labs

Strong fit for a media delivery incident commander, but the product would lean toward platform operations rather than rights clearance.

### ClickHouse

Strong fit for audience or campaign analytics, but that direction felt less distinctive and less directly connected to the creative production workflow.

### IBM

Strong fit for enterprise orchestration and governance, but the initial product would risk becoming an abstract multi-agent platform instead of a focused media tool.

### Replit

Strong fit for rapidly building and publishing an agent, but the partner could appear to be the development environment rather than the business-critical capability.

## Consequences

### Positive

- clear product narrative;
- natural source-evidence model;
- strong reason to use a research partner;
- easy-to-understand demo artifact;
- extensible toward rights monitoring and outreach.

### Negative

- web research may be incomplete or stale;
- legal ownership is not always discoverable from public sources;
- provider quotas and response latency must be handled;
- the product needs strong disclaimers and human review boundaries.

## Revisit trigger

Reconsider the track only if the required Parallel access or Google Cloud integration path cannot be made functional and demonstrable within the first foundation milestone.

