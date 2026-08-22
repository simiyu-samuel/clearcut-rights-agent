"use client";

import { FormEvent, useState } from "react";

type UploadFormProps = { projectId: string };

export function UploadForm({ projectId }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
      setMessage(`${document.original_filename} uploaded. Start analysis to extract assets.`);
      setFile(null);
      event.currentTarget.reset();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setIsUploading(false);
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
      </div>
      {message ? <div className="upload-message" role="status">{message}</div> : null}
    </form>
  );
}
