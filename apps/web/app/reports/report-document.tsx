"use client";

import type { ClearanceReport } from "@/lib/types";
import { useState } from "react";

export function ReportDocument({ projectId, report }: { projectId: string; report: ClearanceReport }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  function downloadMarkdown() {
    const url = URL.createObjectURL(new Blob([report.content_markdown], { type: "text/markdown" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `clearcut-${projectId}-report.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function downloadPdf() {
    setBusy(true);
    setMessage("");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const response = await fetch(`${apiUrl}/v1/projects/${projectId}/reports/${report.id}/pdf`, { headers: { "x-organization-id": "demo-org" } });
      if (!response.ok) throw new Error("Unable to download the PDF report.");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `clearcut-${projectId}-report.pdf`;
      link.click();
      URL.revokeObjectURL(url);
      setMessage("PDF downloaded.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to download the PDF report.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="report-viewer panel">
      <div className="panel-header"><div><h2>Clearance report</h2><span>Generated {new Date(report.created_at).toLocaleString()}</span></div><div className="report-downloads"><button className="secondary-button" onClick={downloadMarkdown} type="button">Download Markdown</button><button className="primary-button" disabled={busy} onClick={() => void downloadPdf()} type="button">{busy ? "Preparing PDF…" : "Download PDF"}</button></div></div>
      {message ? <div className="report-message" role="status">{message}</div> : null}
      <pre className="report-content">{report.content_markdown}</pre>
    </section>
  );
}
