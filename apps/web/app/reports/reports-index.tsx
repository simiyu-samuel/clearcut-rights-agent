"use client";

import Link from "next/link";
import type { Route } from "next";
import { useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { authorizedFetch as fetch } from "@/lib/api-client";
import type { Project } from "@/lib/types";
import { ReportButton } from "../projects/[projectId]/report-button";

export function ReportsIndex() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { void fetch("/v1/projects", { cache: "no-store" }).then((response) => response.ok ? response.json() : []).then((items: Project[]) => setProjects(items)).finally(() => setLoading(false)); }, []);
  return <WorkspaceShell active="reports" breadcrumbs={<><Link href="/">Projects</Link><span>/</span><strong>Reports</strong></>}><section className="hero"><div><div className="eyebrow">Clearance reporting</div><h1>Project reports.</h1><p>Generate, view, and download evidence-backed clearance reports for every project.</p></div><Link className="primary-button" href="/projects/new">+ New project</Link></section><section className="panel report-list">{loading ? <div className="loading-panel">Loading reports…</div> : projects.length === 0 ? <div className="review-empty">No projects yet. Create a project to generate a report.</div> : projects.map((project) => <div className="report-row" key={project.id}><div><strong>{project.title}</strong><span>{project.project_type} · {project.status}</span></div><div className="report-row-actions"><Link className="secondary-button" href={`/reports/${project.id}` as Route}>View report</Link><ReportButton projectId={project.id} /></div></div>)}</section></WorkspaceShell>;
}
