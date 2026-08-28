# Video and audio ingestion

## Purpose

ClearCut treats audiovisual media as a source version alongside screenplays. The first media
vertical slice uploads video or audio to the project, extracts a transcript and timestamped
segments with Vertex Gemini, identifies potential rights-bearing signals, and sends those
signals through the existing Parallel research and human approval workflow.

## Supported sources

- Video: MP4, QuickTime/MOV, WebM, Matroska, MPEG/MPG.
- Audio: MP3, WAV, M4A, and OGG.
- Screenplays remain supported as UTF-8 Markdown or plain text.

## Upload lifecycle

```text
choose media
    ↓
create resumable Cloud Storage session
    ↓
browser uploads directly to the asset bucket
    ↓
finalize and verify object size/type
    ↓
queued media_analysis job
    ↓
Vertex Gemini transcript + timestamped signal extraction
    ↓
existing rights inventory → Parallel research → human review
```

The API retains a bounded multipart fallback for local development and small samples. Production
media should use the resumable session because large binaries must not pass through the API
request body. The browser needs the bucket policy in `infra/gcs-media-cors.json` applied to the
asset bucket.

## Analysis contract

The media analyzer returns:

- a transcript, preserving meaningful dialogue and speech;
- a summary and duration when the model can determine them;
- timestamped segments with visible/audible context;
- normalized candidate assets with category, time span, confidence, risk signal, and reason codes.

Gemini output is treated as an extraction signal, never a legal conclusion. All candidates retain
the existing human-review boundary and can be researched, escalated, approved, rejected, or
included in the report like screenplay-derived assets.

## Operational limits

`MAX_MEDIA_UPLOAD_BYTES` limits the local/small multipart fallback to 25 MiB by default.
`MAX_MEDIA_SIZE_BYTES` limits resumable media objects to 5 GiB by default. These are upload
limits, not a guarantee that every duration or codec is supported by the selected model. A later
hardening pass should add duration/codec probing, shot thumbnails, resumable job execution via
Cloud Tasks or Cloud Run Jobs, and retention/deletion controls for source media.
