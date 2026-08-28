"use client";

import Link from "next/link";
import type { Route } from "next";
import { useCallback, useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { authorizedFetch as fetch } from "@/lib/api-client";
import type { ClearanceReport, Project } from "@/lib/types";
import { ReportButton } from "../projects/[projectId]/report-button";

type ReportProject = { project: Project; reports: ClearanceReport[] };

function statusLabel(status: string) {
  return status === "complete" ? "Delivery ready" : status === "review" ? "Needs review" : status[0].toUpperCase() + status.slice(1);
}

export function ReportsIndex() {
  const [items, setItems] = useState<ReportProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const loadReports = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      const projectsResponse = await fetch("/v1/projects", { cache: "no-store" });
      if (!projectsResponse.ok) throw new Error("Unable to load projects for reporting.");
      const projects = await projectsResponse.json() as Project[];
      const nextItems = await Promise.all(projects.map(async (project) => {
        const response = await fetch(`/v1/projects/${project.id}/reports`, { cache: "no-store" });
        if (!response.ok) throw new Error("Unable to load report history.");
        return { project, reports: await response.json() as ClearanceReport[] };
      }));
      setItems(nextItems);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load reports.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadReports(); }, [loadReports]);

  return (
    <WorkspaceShell active="reports" breadcrumbs={<><Link href="/">Projects</Link><span>/</span><strong>Reports</strong></>}>
      <section className="hero"><div><div className="eyebrow">Clearance reporting</div><h1>Project reports.</h1><p>Generate, view, and download evidence-backed clearance reports for every project.</p></div><Link className="primary-button" href="/projects/new">+ New project</Link></section>
      {message ? <div className="dashboard-error" role="alert"><div><strong>Reports could not be loaded</strong><p>{message}</p></div><button className="secondary-button" disabled={loading} onClick={() => void loadReports()} type="button">{loading ? "Refreshing…" : "Retry"}</button></div> : null}
      <section className="panel report-list">
        <div className="report-list-header"><div><span className="eyebrow">Workspace archive</span><h2>Reports by project</h2></div><span className="section-heading-meta">{loading ? "Refreshing" : `${items.length} ${items.length === 1 ? "project" : "projects"}`}</span></div>
        {loading ? <div className="report-loading-list">{["one", "two", "three"].map((key) => <div className="report-row skeleton-row" key={key}><span className="skeleton-block skeleton-row-title" /><span className="skeleton-block skeleton-row-actions" /></div>)}</div> : items.length === 0 ? <div className="empty-state report-empty-state"><span className="eyebrow">No projects</span><h2>Nothing to report yet.</h2><p>Create a project, upload source material, and complete its first analysis to generate an auditable clearance report.</p><Link className="primary-button" href="/projects/new">Create a project</Link></div> : items.map(({ project, reports }) => { const latest = reports[0]; return <div className="report-row" key={project.id}><div className="report-row-title"><strong>{project.title}</strong><span>{project.project_type} · <span className={`status-text ${project.status}`}>{statusLabel(project.status)}</span></span></div><div className="report-row-status"><span className={`report-availability ${latest ? "ready" : "pending"}`}>{latest ? `Version ${latest.version_number} ready` : "No report yet"}</span>{latest ? <small>Generated {new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(latest.created_at))}</small> : <small>Generate after review decisions</small>}</div><div className="report-row-actions">{latest ? <Link className="secondary-button" href={`/reports/${project.id}` as Route}>View report</Link> : null}<ReportButton projectId={project.id} /></div></div>; })}
      </section>
    </WorkspaceShell>
  );
}
