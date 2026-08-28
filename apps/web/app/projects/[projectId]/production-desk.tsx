"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { useEffect, useRef, useState } from "react";

type ProductionDeskProps = { projectId: string };
type DocumentVersion = { id: string; original_filename: string; source_kind: "document" | "video" | "audio"; version_number: number; parent_document_id: string | null; status: string; created_at: string };
type Attachment = { id: string; original_filename: string; mime_type: string; size_bytes: number; attachment_type: string; created_by: string; created_at: string };
type ReviewShare = { id: string; label: string; expires_at: string | null; revoked_at: string | null; created_by: string; created_at: string; share_token?: string | null };
type DocumentDiff = { from_document_id: string; to_document_id: string; added_lines: number; removed_lines: number; changed_lines: number; added_assets: string[]; removed_assets: string[] };

const headers = { "x-organization-id": "demo-org", "x-actor-id": "demo-user" };

function dateLabel(value: string) {
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function fileSize(value: number) {
  if (value < 1024) return value + " B";
  if (value < 1024 * 1024) return Math.round(value / 1024) + " KB";
  return (value / (1024 * 1024)).toFixed(1) + " MB";
}

function sourceLabel(sourceKind: DocumentVersion["source_kind"]) {
  if (sourceKind === "video") return "Video";
  if (sourceKind === "audio") return "Audio";
  return "Screenplay";
}

export function ProductionDesk({ projectId }: ProductionDeskProps) {
  const [documents, setDocuments] = useState<DocumentVersion[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [shares, setShares] = useState<ReviewShare[]>([]);
  const [diff, setDiff] = useState<DocumentDiff | null>(null);
  const [shareLabel, setShareLabel] = useState("Legal review");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  async function load() {
    const [documentsResponse, attachmentsResponse, sharesResponse] = await Promise.all([
      fetch(apiUrl + "/v1/projects/" + projectId + "/documents", { headers, cache: "no-store" }),
      fetch(apiUrl + "/v1/projects/" + projectId + "/attachments", { headers, cache: "no-store" }),
      fetch(apiUrl + "/v1/projects/" + projectId + "/review-shares", { headers, cache: "no-store" }),
    ]);
    if (!documentsResponse.ok || !attachmentsResponse.ok || !sharesResponse.ok) throw new Error("Production desk data is not available yet.");
    setDocuments(await documentsResponse.json() as DocumentVersion[]);
    setAttachments(await attachmentsResponse.json() as Attachment[]);
    setShares(await sharesResponse.json() as ReviewShare[]);
  }

  useEffect(() => { void load().catch((error) => setMessage(error instanceof Error ? error.message : "Unable to load production desk.")); }, [projectId]);

  async function compareVersions() {
    if (documents.length < 2) return;
    setBusy(true);
    try {
      const ordered = [...documents].sort((a, b) => a.version_number - b.version_number);
      const from = ordered[ordered.length - 2];
      const to = ordered[ordered.length - 1];
      const response = await fetch(apiUrl + "/v1/projects/" + projectId + "/documents/" + from.id + "/diff/" + to.id, { headers, cache: "no-store" });
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
      const response = await fetch(apiUrl + "/v1/projects/" + projectId + "/attachments", { method: "POST", headers, body: form });
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
      const response = await fetch(apiUrl + "/v1/projects/" + projectId + "/review-shares", { method: "POST", headers: { ...headers, "content-type": "application/json" }, body: JSON.stringify({ label: shareLabel }) });
      if (!response.ok) throw new Error("Unable to create the external review link.");
      const created = await response.json() as ReviewShare;
      setShares((current) => [created, ...current]);
      setMessage("External review link created. Copy it before leaving this page.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to create the external review link.");
    } finally { setBusy(false); }
  }

  async function revokeShare(share: ReviewShare) {
    const response = await fetch(apiUrl + "/v1/projects/" + projectId + "/review-shares/" + share.id + "/revoke", { method: "POST", headers });
    if (!response.ok) { setMessage("Unable to revoke the review link."); return; }
    const updated = await response.json() as ReviewShare;
    setShares((current) => current.map((item) => item.id === updated.id ? updated : item));
  }

  return (
    <section className="panel production-desk">
      <div className="panel-header"><div><h2>Production desk</h2><p className="panel-subtitle">Versions, delivery evidence, and scoped external review</p></div><button className="table-action" disabled={busy} onClick={() => void load()} type="button">Refresh</button></div>
      {message ? <div className="review-message" role="status">{message}</div> : null}
      <div className="desk-grid">
        <div className="desk-section"><div className="operations-section-heading"><span>Source versions</span><small>{documents.length} versions</small></div>{documents.map((document) => <div className="desk-row" key={document.id}><div><strong>v{document.version_number} · {sourceLabel(document.source_kind)} · {document.original_filename}</strong><small>{document.status} · {dateLabel(document.created_at)}</small></div><span className="table-status approved">{document.parent_document_id ? "Revision" : "Original"}</span></div>)}{documents.length > 1 ? <button className="secondary-button desk-action" disabled={busy} onClick={() => void compareVersions()} type="button">Compare latest screenplay versions</button> : <p className="operations-empty">Upload a new screenplay version to see a source diff.</p>}{diff ? <div className="diff-callout"><strong>Latest version diff</strong><span>{diff.added_lines} added · {diff.removed_lines} removed · {diff.changed_lines} changed lines</span>{diff.added_assets.length ? <small>New asset signals: {diff.added_assets.join(", ")}</small> : null}{diff.removed_assets.length ? <small>Removed asset signals: {diff.removed_assets.join(", ")}</small> : null}</div> : null}</div>
        <div className="desk-section"><div className="operations-section-heading"><span>Supporting evidence</span><small>{attachments.length} files</small></div>{attachments.map((attachment) => <div className="desk-row" key={attachment.id}><div><strong>{attachment.original_filename}</strong><small>{fileSize(attachment.size_bytes)} · {attachment.created_by} · {dateLabel(attachment.created_at)}</small></div><span className="table-status approved">{attachment.attachment_type.replaceAll("_", " ")}</span></div>)}{!attachments.length ? <p className="operations-empty">Attach releases, contracts, or rights correspondence to this project.</p> : null}<div className="desk-upload"><input ref={fileRef} type="file" /><button className="secondary-button" disabled={busy} onClick={() => void uploadAttachment()} type="button">Upload attachment</button></div></div>
        <div className="desk-section"><div className="operations-section-heading"><span>External review links</span><small>{shares.filter((share) => !share.revoked_at).length} active</small></div>{shares.map((share) => <div className="desk-row" key={share.id}><div><strong>{share.label}</strong><small>{share.revoked_at ? "Revoked" : "Created by " + share.created_by + " · " + dateLabel(share.created_at)}</small>{share.share_token ? <code className="share-token">/review/{share.share_token}</code> : null}</div>{share.revoked_at ? <span className="table-status rejected">Revoked</span> : <button className="table-action" onClick={() => void revokeShare(share)} type="button">Revoke</button>}</div>)}<div className="desk-upload"><input onChange={(event) => setShareLabel(event.target.value)} placeholder="Review link label" value={shareLabel} /><button className="secondary-button" disabled={busy || !shareLabel.trim()} onClick={() => void createShare()} type="button">Create scoped link</button></div></div>
      </div>
    </section>
  );
}
