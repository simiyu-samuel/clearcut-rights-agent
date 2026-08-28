"use client";

import Link from "next/link";
import type { Route } from "next";
import { useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { authorizedFetch as fetch } from "@/lib/api-client";
import type { ClearanceReport, Project } from "@/lib/types";
import { ReportButton } from "../../projects/[projectId]/report-button";
import { ReportDocument } from "../report-document";

export default function ReportPage({ params }: { params: Promise<{ projectId: string }> }) {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [reports, setReports] = useState<ClearanceReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  useEffect(() => { void params.then(({ projectId: resolvedProjectId }) => { setProjectId(resolvedProjectId); return Promise.all([fetch(`/v1/projects/${resolvedProjectId}`, { cache: "no-store" }), fetch(`/v1/projects/${resolvedProjectId}/reports`, { cache: "no-store" })]); }).then(async (responses) => { if (!responses) return; const [projectResponse, reportsResponse] = responses; if (!projectResponse.ok) throw new Error("Project not found."); if (!reportsResponse.ok) throw new Error("Unable to load report history."); setProject(await projectResponse.json() as Project); setReports(await reportsResponse.json() as ClearanceReport[]); }).catch((error) => setMessage(error instanceof Error ? error.message : "Unable to load this report.")).finally(() => setLoading(false)); }, [params]);
  return <WorkspaceShell active="reports" breadcrumbs={<><Link href="/reports">Reports</Link><span>/</span><strong>{project?.title ?? "Report"}</strong></>}><section className="hero"><div><div className="eyebrow">{project?.project_type ?? "Project"} · {project?.status ?? "Loading"}</div><h1>{project?.title ?? "Project report"}</h1><p>Review the latest evidence-backed clearance report and download it for production records.</p></div>{projectId ? <ReportButton projectId={projectId} /> : null}</section>{loading ? <div className="loading-panel panel">Loading report…</div> : message || !project ? <section className="panel empty-state"><span className="eyebrow">Report unavailable</span><h2>{message || "Project not found."}</h2><Link className="secondary-button" href="/reports">Back to reports</Link></section> : reports[0] ? <ReportDocument projectId={project.id} project={project} report={reports[0]} reports={reports} /> : <section className="panel report-empty empty-state"><span className="eyebrow">No snapshot yet</span><h2>No report generated yet.</h2><p>Complete the research and approval decisions, then generate a report snapshot for production records.</p><div className="report-empty-actions"><ReportButton projectId={project.id} /><Link className="secondary-button" href={`/projects/${project.id}/review` as Route}>Open review queue</Link><Link className="secondary-button" href={`/projects/${project.id}/source` as Route}>Open source desk</Link></div></section>}</WorkspaceShell>;
}
