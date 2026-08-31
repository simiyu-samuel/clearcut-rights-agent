"use client";

import Link from "next/link";
import type { Route } from "next";
import { useCallback, useEffect, useMemo, useState } from "react";
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
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"all" | "ready" | "pending">("all");
  const [preview, setPreview] = useState<ReportProject | null>(null);
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

  useEffect(() => {
    if (!preview) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setPreview(null); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [preview]);

  const filteredItems = useMemo(() => items.filter(({ project, reports }) => {
    const normalizedQuery = query.trim().toLowerCase();
    const matchesQuery = !normalizedQuery || [project.title, project.project_type, ...project.territories].join(" ").toLowerCase().includes(normalizedQuery);
    const matchesStatus = status === "all" || (status === "ready" ? reports.length > 0 : reports.length === 0);
    return matchesQuery && matchesStatus;
  }), [items, query, status]);

  return (
    <WorkspaceShell active="reports" breadcrumbs={<><Link href="/">Projects</Link><span>/</span><strong>Reports</strong></>}>
      <section className="hero"><div><div className="eyebrow">Clearance reporting</div><h1>Project reports.</h1><p>Generate, view, and download evidence-backed clearance reports for every project.</p></div><Link className="primary-button" href="/projects/new">+ New project</Link></section>
      {message ? <div className="dashboard-error" role="alert"><div><strong>Reports could not be loaded</strong><p>{message}</p></div><button className="secondary-button" disabled={loading} onClick={() => void loadReports()} type="button">{loading ? "Refreshing…" : "Retry"}</button></div> : null}
      <section className="report-library-toolbar panel"><div className="directory-search"><span aria-hidden="true">⌕</span><input aria-label="Search reports" onChange={(event) => setQuery(event.target.value)} placeholder="Search reports, formats, territories…" value={query} /></div><div className="directory-filters" role="group" aria-label="Report filters"><button className={`filter-chip ${status === "all" ? "active" : ""}`} onClick={() => setStatus("all")} type="button">All projects</button><button className={`filter-chip ${status === "ready" ? "active" : ""}`} onClick={() => setStatus("ready")} type="button">Reports ready</button><button className={`filter-chip ${status === "pending" ? "active" : ""}`} onClick={() => setStatus("pending")} type="button">Needs snapshot</button></div></section>
      <section className="panel report-list">
        <div className="report-list-header"><div><span className="eyebrow">Workspace archive</span><h2>Reports by project</h2></div><span className="section-heading-meta">{loading ? "Refreshing" : `${filteredItems.length} of ${items.length} ${items.length === 1 ? "project" : "projects"}`}</span></div>
        {loading ? <div className="report-loading-list">{["one", "two", "three"].map((key) => <div className="report-row skeleton-row" key={key}><span className="skeleton-block skeleton-row-title" /><span className="skeleton-block skeleton-row-actions" /></div>)}</div> : filteredItems.length === 0 ? <div className="empty-state report-empty-state"><span className="eyebrow">No matches</span><h2>No projects match this view.</h2><p>Try a different search or filter to find a report snapshot.</p><button className="secondary-button" onClick={() => { setQuery(""); setStatus("all"); }} type="button">Clear filters</button></div> : filteredItems.map(({ project, reports }) => { const latest = reports[0]; return <div className="report-row" key={project.id}><div className="report-row-title"><strong>{project.title}</strong><span>{project.project_type} · <span className={`status-text ${project.status}`}>{statusLabel(project.status)}</span></span></div><div className="report-row-status"><span className={`report-availability ${latest ? "ready" : "pending"}`}>{latest ? `Version ${latest.version_number} ready` : "No report yet"}</span>{latest ? <small>Generated {new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(latest.created_at))}</small> : <small>Generate after review decisions</small>}</div><div className="report-row-actions">{latest ? <button className="table-action" onClick={() => setPreview({ project, reports })} type="button">Preview</button> : null}{latest ? <Link className="secondary-button" href={`/reports/${project.id}` as Route}>Open report</Link> : null}<ReportButton projectId={project.id} /></div></div>; })}
      </section>
      {preview ? <div className="drawer-layer" onClick={() => setPreview(null)}><aside aria-label="Report preview" className="report-preview-drawer" onClick={(event) => event.stopPropagation()}><div className="drawer-header"><div><span className="eyebrow">Report snapshot</span><h2>{preview.project.title}</h2></div><button aria-label="Close report preview" className="icon-button" onClick={() => setPreview(null)} type="button">×</button></div><div className="report-preview-cover"><img className="report-preview-logo" src="/clearcut-logo.png" alt="ClearCut" /><strong>Evidence-backed clearance report</strong><small>Version {preview.reports[0]?.version_number} · {preview.reports[0] ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(new Date(preview.reports[0].created_at)) : ""}</small></div><div className="report-preview-details"><div><span>Project type</span><strong>{preview.project.project_type}</strong></div><div><span>Territories</span><strong>{preview.project.territories.join(" · ") || "Not set"}</strong></div><div><span>Distribution</span><strong>{preview.project.distribution_modes.join(" · ") || "Not set"}</strong></div><div><span>Record</span><strong>Human review required</strong></div></div><p className="report-preview-note">Open the full report to inspect asset-level evidence, decisions, permission work, and the styled PDF export.</p><div className="report-preview-actions"><Link className="primary-button" href={`/reports/${preview.project.id}` as Route}>Open full report</Link><button className="secondary-button" onClick={() => setPreview(null)} type="button">Close preview</button></div></aside></div> : null}
    </WorkspaceShell>
  );
}
