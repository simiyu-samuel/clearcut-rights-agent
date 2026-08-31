"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { SourceGlyph } from "@/components/source-glyph";
import { useAuth } from "@/lib/auth-context";
import { useEffect, useRef, useState } from "react";

type ProductionDeskProps = { projectId: string };
type SourceKind = "document" | "video" | "audio";
type DocumentVersion = { id: string; original_filename: string; mime_type: string; size_bytes: number; source_kind: SourceKind; version_number: number; parent_document_id: string | null; status: string; media_metadata?: Record<string, unknown>; created_at: string };
type Attachment = { id: string; original_filename: string; mime_type: string; size_bytes: number; attachment_type: string; created_by: string; created_at: string };
type ReviewShare = { id: string; label: string; expires_at: string | null; revoked_at: string | null; created_by: string; created_at: string; share_token?: string | null };
type DocumentDiff = { from_document_id: string; to_document_id: string; added_lines: number; removed_lines: number; changed_lines: number; added_assets: string[]; removed_assets: string[] };

function dateLabel(value: string) {
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function fileSize(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

function sourceLabel(sourceKind: SourceKind) {
  if (sourceKind === "video") return "Video";
  if (sourceKind === "audio") return "Audio";
  return "Screenplay";
}

function statusClass(status: string) {
  if (status === "analyzed") return "analyzed";
  if (status === "processing") return "processing";
  if (status === "failed") return "failed";
  return "uploaded";
}

export function ProductionDesk({ projectId }: ProductionDeskProps) {
  const auth = useAuth();
  const [documents, setDocuments] = useState<DocumentVersion[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [shares, setShares] = useState<ReviewShare[]>([]);
  const [diff, setDiff] = useState<DocumentDiff | null>(null);
  const [shareLabel, setShareLabel] = useState("Legal review");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  function actorLabel(actorId: string) {
    if (actorId === auth.user?.actorId) return auth.user.displayName;
    if (actorId.startsWith("system")) return "ClearCut";
    if (actorId.startsWith("demo-")) return "Studio team";
    return "Workspace member";
  }

  async function load() {
    const [documentsResponse, attachmentsResponse, sharesResponse] = await Promise.all([
      fetch(`/v1/projects/${projectId}/documents`, { cache: "no-store" }),
      fetch(`/v1/projects/${projectId}/attachments`, { cache: "no-store" }),
      fetch(`/v1/projects/${projectId}/review-shares`, { cache: "no-store" }),
    ]);
    if (!documentsResponse.ok || !attachmentsResponse.ok || !sharesResponse.ok) throw new Error("Production desk data is not available yet.");
    setDocuments(await documentsResponse.json() as DocumentVersion[]);
    setAttachments(await attachmentsResponse.json() as Attachment[]);
    setShares(await sharesResponse.json() as ReviewShare[]);
  }

  useEffect(() => {
    void load().catch((error) => setMessage(error instanceof Error ? error.message : "Unable to load production desk."));
    const refresh = () => void load().catch(() => undefined);
    window.addEventListener("clearcut:source-uploaded", refresh);
    window.addEventListener("clearcut:source-analyzed", refresh);
    return () => {
      window.removeEventListener("clearcut:source-uploaded", refresh);
      window.removeEventListener("clearcut:source-analyzed", refresh);
    };
  }, [projectId]);

  async function compareVersions() {
    if (documents.length < 2) return;
    setBusy(true);
    try {
      const ordered = [...documents].sort((a, b) => a.version_number - b.version_number);
      const from = ordered[ordered.length - 2];
      const to = ordered[ordered.length - 1];
      const response = await fetch(`/v1/projects/${projectId}/documents/${from.id}/diff/${to.id}`, { cache: "no-store" });
      if (!response.ok) throw new Error("Unable to compare screenplay versions.");
      setDiff(await response.json() as DocumentDiff);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to compare versions.");
    } finally { setBusy(false); }
  }

  async function uploadAttachment() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("attachment_type", "supporting_document");
      const response = await fetch(`/v1/projects/${projectId}/attachments`, { method: "POST", body: form });
      if (!response.ok) throw new Error("Unable to upload the attachment.");
      const created = await response.json() as Attachment;
      setAttachments((current) => [created, ...current]);
      if (fileRef.current) fileRef.current.value = "";
      setMessage("Supporting document uploaded.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to upload the attachment.");
    } finally { setBusy(false); }
  }

  async function createShare() {
    setBusy(true);
    try {
      const response = await fetch(`/v1/projects/${projectId}/review-shares`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ label: shareLabel }) });
      if (!response.ok) throw new Error("Unable to create the external review link.");
      const created = await response.json() as ReviewShare;
      setShares((current) => [created, ...current]);
      setMessage("External review link created. Copy it before leaving this page.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to create the external review link.");
    } finally { setBusy(false); }
  }

  async function revokeShare(share: ReviewShare) {
    const response = await fetch(`/v1/projects/${projectId}/review-shares/${share.id}/revoke`, { method: "POST" });
    if (!response.ok) { setMessage("Unable to revoke the review link."); return; }
    const updated = await response.json() as ReviewShare;
    setShares((current) => current.map((item) => item.id === updated.id ? updated : item));
  }

  return (
    <section className="production-desk panel" aria-label="Production desk">
      <div className="panel-header"><div><span className="eyebrow">Project operations</span><h2>Production desk</h2><p className="panel-subtitle">Versions, delivery evidence, and scoped external review.</p></div><button className="table-action" disabled={busy} onClick={() => void load()} type="button">{busy ? "Working…" : "Refresh"}</button></div>
      {message ? <div className="review-message" role="status">{message}</div> : null}
      <div className="desk-grid">
        <div className="desk-section source-history-section">
          <div className="operations-section-heading"><span>Source versions</span><small>{documents.length} {documents.length === 1 ? "version" : "versions"}</small></div>
          <div className="source-history-list">
            {documents.map((document) => <div className="source-history-card" key={document.id}><div className={`source-history-icon ${document.source_kind}`}><SourceGlyph kind={document.source_kind} /></div><div className="source-history-copy"><div><strong>{document.original_filename}</strong><span className={`source-status-pill ${statusClass(document.status)}`}>{document.status}</span></div><small>v{document.version_number} · {sourceLabel(document.source_kind)} · {fileSize(document.size_bytes)}</small><small>{dateLabel(document.created_at)}{document.parent_document_id ? " · Revision" : " · Original source"}</small></div></div>)}
          </div>
          {documents.length > 1 ? <button className="secondary-button desk-action" disabled={busy} onClick={() => void compareVersions()} type="button">Compare latest versions</button> : <p className="operations-empty desk-note">Upload a new screenplay version to compare changes over time.</p>}
          {diff ? <div className="diff-callout"><strong>Latest version diff</strong><span>{diff.added_lines} added · {diff.removed_lines} removed · {diff.changed_lines} changed lines</span>{diff.added_assets.length ? <small>New asset signals: {diff.added_assets.join(", ")}</small> : null}{diff.removed_assets.length ? <small>Removed asset signals: {diff.removed_assets.join(", ")}</small> : null}</div> : null}
        </div>
        <div className="desk-section evidence-section">
          <div className="operations-section-heading"><span>Supporting evidence</span><small>{attachments.length} files</small></div>
          <div className="desk-card-list">{attachments.map((attachment) => <div className="desk-file-card" key={attachment.id}><div className="desk-file-icon">↗</div><div><strong>{attachment.original_filename}</strong><small>{fileSize(attachment.size_bytes)} · {actorLabel(attachment.created_by)}</small><small>{dateLabel(attachment.created_at)}</small></div></div>)}</div>
          {!attachments.length ? <p className="operations-empty desk-note">Attach releases, contracts, or rights correspondence to this project.</p> : null}
          <div className="desk-upload"><input ref={fileRef} aria-label="Supporting evidence file" type="file" /><button className="secondary-button" disabled={busy} onClick={() => void uploadAttachment()} type="button">Upload evidence</button></div>
        </div>
        <div className="desk-section review-link-section">
          <div className="operations-section-heading"><span>External review</span><small>{shares.filter((share) => !share.revoked_at).length} active</small></div>
          <div className="desk-card-list">{shares.map((share) => <div className="desk-share-card" key={share.id}><div><strong>{share.label}</strong><small>{share.revoked_at ? "Revoked" : `Created by ${actorLabel(share.created_by)}`}</small>{share.share_token ? <code className="share-token">/review/{share.share_token}</code> : null}</div>{share.revoked_at ? <span className="table-status rejected">Revoked</span> : <button className="table-action" onClick={() => void revokeShare(share)} type="button">Revoke</button>}</div>)}</div>
          {!shares.length ? <p className="operations-empty desk-note">Create a scoped link when an external legal or production reviewer needs access.</p> : null}
          <div className="desk-upload"><input aria-label="Review link label" onChange={(event) => setShareLabel(event.target.value)} placeholder="Review link label" value={shareLabel} /><button className="secondary-button" disabled={busy || !shareLabel.trim()} onClick={() => void createShare()} type="button">Create link</button></div>
        </div>
      </div>
    </section>
  );
}
