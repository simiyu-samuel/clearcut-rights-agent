"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { FormEvent, useState } from "react";

type UploadFormProps = { projectId: string };
type SourceKind = "document" | "video" | "audio";
type UploadedSource = { id: string; original_filename: string; source_kind: SourceKind };

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

export function UploadForm({ projectId }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState<UploadedSource | null>(null);
  const [message, setMessage] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

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
    const session = await sessionResponse.json() as {
      document_id: string;
      upload_url: string;
    };
    const uploadResponse = await window.fetch(session.upload_url, {
      method: "PUT",
      headers: {
        "Content-Type": selectedFile.type || "application/octet-stream",
        "Content-Range": `bytes 0-${selectedFile.size - 1}/${selectedFile.size}`,
      },
      body: selectedFile,
    });
    if (!uploadResponse.ok) throw new Error("Cloud Storage rejected the media upload.");

    const completeResponse = await fetch(`/v1/documents/${session.document_id}/complete-upload`, {
      method: "POST",
    });
    if (!completeResponse.ok) {
      const payload = await completeResponse.json().catch(() => ({}));
      throw new Error(payload.detail ?? "Unable to finalize the media upload.");
    }
    return await completeResponse.json() as UploadedSource;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!file) {
      setMessage("Choose a screenplay, video, or audio source first.");
      return;
    }
    setIsUploading(true);
    setMessage("");
    try {
      const uploaded = sourceKindFor(file) === "document"
        ? await uploadDocument(file)
        : await uploadMedia(file);
      setSource(uploaded);
      setMessage(`${uploaded.original_filename} uploaded. Start analysis to extract rights signals.`);
      setFile(null);
      form.reset();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  async function uploadDocument(selectedFile: File): Promise<UploadedSource> {
    const formData = new FormData();
    formData.append("file", selectedFile);
    const response = await fetch(`/v1/projects/${projectId}/documents`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail ?? "Upload failed.");
    }
    return await response.json() as UploadedSource;
  }

  async function startAnalysis() {
    if (!source) return;
    setIsAnalyzing(true);
    setMessage(`${sourceLabel(source.source_kind)} analysis queued…`);
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
          setMessage(`${source.original_filename} analyzed. Refreshing the rights inventory…`);
          window.setTimeout(() => window.location.reload(), 700);
          return;
        }
        if (status.status === "failed") throw new Error(status.error_code ?? "Media analysis failed.");
      }
      throw new Error("Analysis is taking longer than expected. Refresh this project shortly.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to start analysis.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  const selectedKind = file ? sourceKindFor(file) : "document";

  return (
    <form className="upload-panel" onSubmit={submit}>
      <div>
        <div className="upload-title">Add creative material</div>
        <div className="upload-copy">Upload a screenplay, video, or audio source. ClearCut will transcribe media and flag visible or audible rights signals.</div>
      </div>
      <div className="upload-controls">
        <label className="file-picker">
          <span>{file ? `${sourceLabel(selectedKind)} · ${file.name}` : "Choose source"}</span>
          <input accept=".md,.markdown,.txt,.mp4,.mov,.webm,.mkv,.mpeg,.mpg,.mp3,.wav,.m4a,.ogg,text/markdown,text/plain,video/*,audio/*" type="file" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setSource(null); setMessage(""); }} />
        </label>
        <button className="secondary-button" disabled={isUploading} type="submit">{isUploading ? "Uploading…" : "Upload source"}</button>
        {source ? <button className="primary-button" disabled={isAnalyzing} onClick={() => void startAnalysis()} type="button">{isAnalyzing ? "Analyzing…" : `Analyze ${sourceLabel(source.source_kind).toLowerCase()}`}</button> : null}
      </div>
      {message ? <div className="upload-message" role="status">{message}</div> : null}
    </form>
  );
}
