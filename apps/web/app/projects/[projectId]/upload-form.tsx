"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { SourceGlyph } from "@/components/source-glyph";
import { FormEvent, useEffect, useRef, useState } from "react";

type UploadFormProps = { projectId: string };
type SourceKind = "document" | "video" | "audio";
type DocumentStatus = "uploading" | "uploaded" | "processing" | "analyzed" | "failed" | string;
type UploadedSource = {
  id: string;
  original_filename: string;
  mime_type?: string;
  size_bytes?: number;
  source_kind: SourceKind;
  status?: DocumentStatus;
  media_metadata?: Record<string, unknown>;
  version_number?: number;
  created_at?: string;
};

function acceptedFor(kind: SourceKind) {
  if (kind === "video") return ".mp4,.mov,.webm,.mkv,.mpeg,.mpg,video/*";
  if (kind === "audio") return ".mp3,.wav,.m4a,.ogg,audio/*";
  return ".md,.markdown,.txt,text/markdown,text/plain";
}

function sourceKindFor(file: File): SourceKind {
  return file.type.startsWith("video/") || /\.(mp4|mov|webm|mkv|mpeg|mpg)$/i.test(file.name)
    ? "video"
    : file.type.startsWith("audio/") || /\.(mp3|wav|m4a|ogg)$/i.test(file.name)
      ? "audio"
      : "document";
}

function sourceLabel(sourceKind: SourceKind) {
  if (sourceKind === "video") return "Video";
  if (sourceKind === "audio") return "Audio";
  return "Screenplay";
}

function sourceDescription(sourceKind: SourceKind) {
  if (sourceKind === "video") return "MP4, MOV, WebM";
  if (sourceKind === "audio") return "MP3, WAV, M4A";
  return "Markdown, TXT";
}

function fileSize(value: number | undefined) {
  if (!value) return "Size pending";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

function statusLabel(status: DocumentStatus | undefined) {
  if (status === "uploaded") return "Ready to analyze";
  if (status === "processing") return "Analysis in progress";
  if (status === "analyzed") return "Analysis complete";
  if (status === "uploading") return "Finishing upload";
  if (status === "failed") return "Analysis needs retry";
  return "Source received";
}

function canAnalyze(source: UploadedSource | null) {
  return Boolean(source && ["uploaded", "failed"].includes(source.status ?? "uploaded"));
}

export function UploadForm({ projectId }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState<UploadedSource | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [message, setMessage] = useState<string>("");
  const [isLoadingSource, setIsLoadingSource] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [pickerKind, setPickerKind] = useState<SourceKind>("document");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    setIsLoadingSource(true);
    void fetch(`/v1/projects/${projectId}/documents`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Unable to load source material.");
        const documents = await response.json() as UploadedSource[];
        const latest = [...documents].sort((a, b) => {
          if ((b.version_number ?? 0) !== (a.version_number ?? 0)) {
            return (b.version_number ?? 0) - (a.version_number ?? 0);
          }
          return String(b.created_at ?? "").localeCompare(String(a.created_at ?? ""));
        })[0];
        if (active && latest) setSource(latest);
      })
      .catch(() => undefined)
      .finally(() => { if (active) setIsLoadingSource(false); });
    return () => { active = false; };
  }, [projectId]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  function chooseSource(kind: SourceKind) {
    setPickerKind(kind);
    window.setTimeout(() => fileRef.current?.click(), 0);
  }

  function handleFileChange(selectedFile: File | null) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(selectedFile);
    setMessage("");
    if (selectedFile && sourceKindFor(selectedFile) !== "document") {
      setPreviewUrl(URL.createObjectURL(selectedFile));
    } else {
      setPreviewUrl(null);
    }
  }

  async function uploadMedia(selectedFile: File): Promise<UploadedSource> {
    const sessionResponse = await fetch(`/v1/projects/${projectId}/media-uploads`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        filename: selectedFile.name,
        mime_type: selectedFile.type || "application/octet-stream",
        size_bytes: selectedFile.size,
      }),
    });

    if (sessionResponse.status === 501) {
      const formData = new FormData();
      formData.append("file", selectedFile);
      const fallbackResponse = await fetch(`/v1/projects/${projectId}/media`, {
        method: "POST",
        body: formData,
      });
      if (!fallbackResponse.ok) {
        const payload = await fallbackResponse.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Media upload failed.");
      }
      return await fallbackResponse.json() as UploadedSource;
    }

    if (!sessionResponse.ok) {
      const payload = await sessionResponse.json().catch(() => ({}));
      throw new Error(payload.detail ?? "Unable to start the media upload.");
    }
    const session = await sessionResponse.json() as { document_id: string; upload_url: string };
    const uploadResponse = await window.fetch(session.upload_url, {
      method: "PUT",
      headers: {
        "Content-Type": selectedFile.type || "application/octet-stream",
        "Content-Range": `bytes 0-${selectedFile.size - 1}/${selectedFile.size}`,
      },
      body: selectedFile,
    });
    if (!uploadResponse.ok) throw new Error("Cloud Storage rejected the media upload.");

    const completeResponse = await fetch(`/v1/documents/${session.document_id}/complete-upload`, { method: "POST" });
    if (!completeResponse.ok) {
      const payload = await completeResponse.json().catch(() => ({}));
      throw new Error(payload.detail ?? "Unable to finalize the media upload.");
    }
    return await completeResponse.json() as UploadedSource;
  }

  async function uploadDocument(selectedFile: File): Promise<UploadedSource> {
    const formData = new FormData();
    formData.append("file", selectedFile);
    const response = await fetch(`/v1/projects/${projectId}/documents`, { method: "POST", body: formData });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail ?? "Upload failed.");
    }
    return await response.json() as UploadedSource;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setMessage("Choose a screenplay, video, or audio source first.");
      return;
    }
    setIsUploading(true);
    setMessage("");
    try {
      const uploaded = sourceKindFor(file) === "document" ? await uploadDocument(file) : await uploadMedia(file);
      setSource(uploaded);
      setMessage(`${uploaded.original_filename} is ready. Start analysis when you are ready.`);
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      window.dispatchEvent(new CustomEvent("clearcut:source-uploaded"));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  async function startAnalysis() {
    if (!source || !canAnalyze(source)) return;
    setIsAnalyzing(true);
    setSource((current) => current ? { ...current, status: "processing" } : current);
    setMessage(`${sourceLabel(source.source_kind)} analysis queued. ClearCut is extracting rights signals…`);
    try {
      const response = await fetch(`/v1/projects/${projectId}/analysis-runs`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ document_id: source.id }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Unable to start analysis.");
      }
      const job = await response.json() as { id: string };
      for (let attempt = 0; attempt < 80; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        const statusResponse = await fetch(`/v1/jobs/${job.id}`, { cache: "no-store" });
        if (!statusResponse.ok) throw new Error("Unable to read analysis status.");
        const status = await statusResponse.json() as { status: string; error_code?: string | null };
        if (status.status === "awaiting_review" || status.status === "completed") {
          setSource((current) => current ? { ...current, status: "analyzed" } : current);
          setMessage(`${source.original_filename} analyzed. The inventory and review queue are ready.`);
          window.dispatchEvent(new CustomEvent("clearcut:source-analyzed"));
          return;
        }
        if (status.status === "failed") throw new Error(status.error_code ?? "Media analysis failed.");
      }
      throw new Error("Analysis is taking longer than expected. Refresh this project shortly.");
    } catch (error) {
      setSource((current) => current ? { ...current, status: "failed" } : current);
      setMessage(error instanceof Error ? error.message : "Unable to start analysis.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  const selectedKind = file ? sourceKindFor(file) : pickerKind;
  const sourceForPreview = file ? {
    original_filename: file.name,
    source_kind: selectedKind,
    size_bytes: file.size,
    status: "uploading" as DocumentStatus,
  } : source;
  const sourceStatus = source?.status ?? "uploaded";

  return (
    <section className="source-material-page" aria-label="Source material">
      <div className="source-page-heading">
        <div><span className="eyebrow">Project source desk</span><h2>Source material</h2><p>Manage screenplay versions and audiovisual source files before rights analysis begins.</p></div>
        <span className="source-sync-state"><span className="env-dot" /> {isLoadingSource ? "Checking source desk" : "Source desk synced"}</span>
      </div>

      <form className="source-upload-form" onSubmit={submit}>
        <input ref={fileRef} accept={acceptedFor(pickerKind)} className="visually-hidden" type="file" onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)} />
        <div className="source-upload-grid">
          {(["document", "video", "audio"] as SourceKind[]).map((kind) => (
            <button className={`source-upload-choice ${selectedKind === kind && file ? "selected" : ""}`} key={kind} onClick={() => chooseSource(kind)} type="button">
              <span className="source-choice-icon"><SourceGlyph kind={kind} /></span>
              <strong>Upload {sourceLabel(kind).toLowerCase()}</strong>
              <small>{sourceDescription(kind)}</small>
              <span className="source-choice-action">Choose file <b>→</b></span>
            </button>
          ))}
        </div>

        {sourceForPreview ? (
          <div className={`source-selected-card ${sourceForPreview.source_kind}`}>
            <div className="source-file-icon"><SourceGlyph kind={sourceForPreview.source_kind} /></div>
            <div className="source-selected-info">
              <div className="source-selected-topline"><strong>{sourceForPreview.original_filename}</strong><span>{fileSize(sourceForPreview.size_bytes)}</span></div>
              <div className="source-selected-meta"><span>{sourceLabel(sourceForPreview.source_kind)} {source?.version_number ? `· v${source.version_number}` : ""}</span><span>{file ? "Ready to upload" : statusLabel(sourceStatus)}</span></div>
              {file && sourceForPreview.source_kind !== "document" ? <div className="source-preview-inline">{sourceForPreview.source_kind === "video" ? <video controls muted preload="metadata" src={previewUrl ?? undefined} /> : <audio controls src={previewUrl ?? undefined} />}</div> : null}
              {file && sourceForPreview.source_kind === "document" ? <div className="source-text-preview">Text and Markdown files are stored as a versioned screenplay source.</div> : null}
            </div>
            {file ? <button className="secondary-button source-upload-action" disabled={isUploading} type="submit">{isUploading ? "Uploading…" : "Upload source"}</button> : null}
            {!file && canAnalyze(source) ? <button className="primary-button source-upload-action" disabled={isAnalyzing} onClick={() => void startAnalysis()} type="button">{isAnalyzing ? "Analyzing…" : `Analyze ${sourceLabel(source!.source_kind).toLowerCase()}`}</button> : null}
            {!file && sourceStatus === "processing" ? <span className="source-status-pill processing">Analysis in progress</span> : null}
            {!file && sourceStatus === "analyzed" ? <span className="source-status-pill analyzed">Analysis complete</span> : null}
          </div>
        ) : (
          <div className="source-empty-state"><span className="source-empty-icon">＋</span><div><strong>No source uploaded yet</strong><p>Choose a screenplay, video, or audio file above to begin the clearance workflow.</p></div></div>
        )}
        {message ? <div className={`source-message ${sourceStatus === "failed" ? "error" : ""}`} role="status">{message}</div> : null}
      </form>

      <div className="source-help-strip"><div><strong>How this works</strong><span>Upload → analyze → research extracted rights signals → record human decisions.</span></div><span>Supported sources stay linked to the project record.</span></div>
    </section>
  );
}
