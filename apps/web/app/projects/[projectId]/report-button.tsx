"use client";

import { useState } from "react";

export function ReportButton({ projectId }: { projectId: string }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function downloadReport() {
    setBusy(true);
    setMessage("");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const response = await fetch(`${apiUrl}/v1/projects/${projectId}/reports`, {
        method: "POST",
        headers: { "x-organization-id": "demo-org", "x-actor-id": "demo-producer" },
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Unable to generate the report.");
      }
      const report = await response.json();
      const download = document.createElement("a");
      download.href = URL.createObjectURL(new Blob([report.content_markdown], { type: "text/markdown" }));
      download.download = `clearcut-${projectId}-report.md`;
      download.click();
      URL.revokeObjectURL(download.href);
      setMessage("Report downloaded.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to generate the report.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="report-action">
      <button className="secondary-button" disabled={busy} onClick={() => void downloadReport()} type="button">
        {busy ? "Generating…" : "Export report"}
      </button>
      {message ? <span role="status">{message}</span> : null}
    </div>
  );
}
