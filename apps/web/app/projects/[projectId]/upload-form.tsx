"use client";

import { FormEvent, useState } from "react";

type UploadFormProps = { projectId: string };

export function UploadForm({ projectId }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);
  const [message, setMessage] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!file) {
      setMessage("Choose a screenplay first.");
      return;
    }
    setIsUploading(true);
    setMessage("");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const response = await fetch(`${apiUrl}/v1/projects/${projectId}/documents`, {
        method: "POST",
        headers: { "x-organization-id": "demo-org" },
        body: formData,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Upload failed");
      }
      const document = await response.json();
      setDocumentId(document.id);
      setUploadedFilename(document.original_filename);
      setMessage(`${document.original_filename} uploaded. Start analysis to extract assets.`);
      setFile(null);
      form.reset();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  async function startAnalysis() {
    if (!documentId) return;
    setIsAnalyzing(true);
    setMessage("Analysis queued…");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const headers = { "content-type": "application/json", "x-organization-id": "demo-org" };
      const response = await fetch(`${apiUrl}/v1/projects/${projectId}/analysis-runs`, {
        method: "POST",
        headers,
        body: JSON.stringify({ document_id: documentId }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Unable to start analysis.");
      }
      const job = await response.json() as { id: string };
      for (let attempt = 0; attempt < 40; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        const statusResponse = await fetch(`${apiUrl}/v1/jobs/${job.id}`, { headers: { "x-organization-id": "demo-org" } });
        if (!statusResponse.ok) throw new Error("Unable to read analysis status.");
        const status = await statusResponse.json() as { status: string; error_code?: string | null };
        if (status.status === "awaiting_review" || status.status === "completed") {
          setMessage(`${uploadedFilename ?? "Document"} analyzed. Refreshing the rights inventory…`);
          window.setTimeout(() => window.location.reload(), 700);
          return;
        }
        if (status.status === "failed") throw new Error(status.error_code ?? "Document analysis failed.");
      }
      throw new Error("Analysis is taking longer than expected. Refresh this project shortly.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to start analysis.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <form className="upload-panel" onSubmit={submit}>
      <div>
        <div className="upload-title">Add creative material</div>
        <div className="upload-copy">Upload a UTF-8 screenplay or treatment in Markdown or plain text.</div>
      </div>
      <div className="upload-controls">
        <label className="file-picker">
          <span>{file ? file.name : "Choose file"}</span>
          <input accept=".md,.markdown,.txt,text/markdown,text/plain" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        </label>
        <button className="secondary-button" disabled={isUploading} type="submit">{isUploading ? "Uploading…" : "Upload"}</button>
        {documentId ? <button className="primary-button" disabled={isAnalyzing} onClick={() => void startAnalysis()} type="button">{isAnalyzing ? "Analyzing…" : "Start analysis"}</button> : null}
      </div>
      {message ? <div className="upload-message" role="status">{message}</div> : null}
    </form>
  );
}
