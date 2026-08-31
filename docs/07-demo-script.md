# ClearCut Hackathon Demo Script

**Target duration:** 3 minutes  
**Demo project:** fictional feature film, *The Last Signal*  
**Audience:** enterprise and engineering judges

## 0:00–0:20 — The problem

“A production can finish a scene and still be unable to distribute it because nobody knows whether the song, logo, artwork, location, or archival reference in that scene is cleared. ClearCut turns that uncertainty into a traceable workflow.”

Show the project dashboard with several unresolved assets.

## 0:20–0:45 — Upload creative material

Upload a short fictional screenplay containing:

- a song reference;
- a branded product;
- a named public location;
- a photograph or artwork reference;
- a sports organization reference.

The checked-in screenplay fixture is synthetic. Do not add real songs, footage, logos, or other third-party media to the demo recording.

Show the analysis job moving from `queued` to `running`.

## 0:45–1:15 — Extract the rights inventory

Show the scene list and asset cards. Open one asset to show the source span and extraction confidence.

Narration:

“ClearCut preserves not only the name of the asset, but where it appears, which document version it came from, and what kind of rights question it creates.”

## 1:15–1:50 — Research with Parallel

Open the research trace for the song or brand. Show the actual Parallel operation in the server-side tool trace, then show normalized sources and excerpts in the UI.

Narration:

“The agent chooses the appropriate research step, calls Parallel from deployed code, and stores the source, retrieval time, excerpt, and confidence. The web content is evidence—not instructions to the agent.”

## 1:50–2:15 — Explainable triage

Open the risk card:

- status: `needs_review`;
- risk score;
- confidence score;
- reason codes;
- source conflict or missing term warning;
- recommended next action.

Show one deliberately ambiguous result to demonstrate that the system does not pretend uncertainty is clearance.

## 2:15–2:40 — Human approval and outreach

Approve “request permission.” Show the generated draft with project, territory, term, medium, and intended use. Do not send it.

Narration:

“ClearCut prepares the work, but a qualified human remains responsible for the decision and any communication.”

## 2:40–3:00 — Report and close

Export the clearance report. Show the audit entry and the Google Cloud deployment.

Closing line:

“ClearCut turns a screenplay into an evidence-backed rights-clearance plan before a single frame reaches distribution.”

## Demo safety checklist

- use only fictional project content;
- do not rely on a live search result that has not been tested;
- keep a fixture mode as a fallback, clearly labelled;
- show the actual live Parallel call at least once;
- keep a pre-generated report ready in case of provider failure;
- demonstrate a human approval boundary;
- show one incomplete or conflicting result.
