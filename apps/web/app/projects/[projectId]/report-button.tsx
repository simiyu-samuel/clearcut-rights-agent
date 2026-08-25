"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import Link from "next/link";
import type { Route } from "next";
import { useEffect, useState } from "react";

export function ReportButton({ projectId }: { projectId: string }) {
  const [hasReport, setHasReport] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    void fetch(`${apiUrl}/v1/projects/${projectId}/reports`, { headers: { "x-organization-id": "demo-org" } })
      .then((response) => (response.ok ? response.json() : []))
      .then((reports: Array<{ id: string }>) => setHasReport(reports.length > 0))
      .catch(() => setHasReport(false));
  }, [projectId]);

  async function generateReport() {
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
      setHasReport(true);
      setMessage("Report ready.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to generate the report.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="report-action">
      <button className="secondary-button" disabled={busy} onClick={() => void generateReport()} type="button">
        {busy ? "Generating…" : hasReport ? "Regenerate report" : "Generate report"}
      </button>
      {hasReport ? <Link className="secondary-button" href={`/reports/${projectId}` as Route}>View report</Link> : null}
      {message ? <span role="status">{message}</span> : null}
    </div>
  );
}
