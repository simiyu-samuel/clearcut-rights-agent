"use client";

import Link from "next/link";
import type { Route } from "next";
import { useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { authorizedFetch as fetch } from "@/lib/api-client";
import type { Project, WorkspaceOverview } from "@/lib/types";

function statusLabel(status: string) {
  return status === "review" ? "Needs review" : status[0].toUpperCase() + status.slice(1);
}

export function WorkspaceHome() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [overview, setOverview] = useState<WorkspaceOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  useEffect(() => {
    void Promise.all([fetch("/v1/projects", { cache: "no-store" }), fetch("/v1/workspace/overview", { cache: "no-store" })])
      .then(async ([projectsResponse, overviewResponse]) => {
        if (!projectsResponse.ok || !overviewResponse.ok) throw new Error("Unable to load the live workspace.");
        setProjects(await projectsResponse.json() as Project[]);
        setOverview(await overviewResponse.json() as WorkspaceOverview);
      })
      .catch((error) => setMessage(error instanceof Error ? error.message : "Unable to load the live workspace."))
      .finally(() => setLoading(false));
  }, []);
  const reviewProject = projects.find((project) => project.status === "review") ?? projects[0];
  return <WorkspaceShell active="projects" breadcrumbs={<><span>Workspace</span><span>/</span><strong>Projects</strong></>}><section className="hero"><div><div className="eyebrow">Production workspace · {projects.length} {projects.length === 1 ? "project" : "projects"}</div><h1>Keep the story moving.</h1><p>ClearCut turns scripts and cuts into evidence-backed rights work, so your production team can see what needs attention before distribution.</p></div><Link className="primary-button" href="/projects/new">+ New project</Link></section>{message ? <div className="overview-unavailable" role="status">{message}</div> : null}<section><div className="section-heading"><h2>Active projects</h2><Link href="/">View all →</Link></div>{loading ? <div className="loading-panel panel">Loading live project data…</div> : projects.length ? <div className="project-grid">{projects.map((project) => <Link className="project-card" href={`/projects/${project.id}` as Route} key={project.id}><div className="project-card-top"><div><h3>{project.title}</h3><div className="project-type">{project.project_type}</div></div><span className={`status-chip ${project.status}`}>{statusLabel(project.status)}</span></div><div className="project-card-footer"><div className="card-meta">{project.territories.join(" · ") || "Territories not set"}<br />Updated {new Date(project.updated_at).toLocaleDateString()}</div><div className="risk-count">{project.status === "review" ? "Human review" : project.status === "complete" ? "Delivery ready" : "In progress"}</div></div></Link>)}</div> : <section className="panel empty-state"><span className="eyebrow">First production</span><h2>No projects yet.</h2><p>Create a project to define the production context, upload source material, and start the evidence workflow.</p><Link className="primary-button" href="/projects/new">Create your first project</Link></section>}</section><section><div className="section-heading"><h2>Workspace overview</h2><span className="card-meta">Last 30 days · live data</span></div>{overview ? <div className="stats-grid"><div className="stat-card"><div className="stat-label">Assets reviewed</div><div className="stat-value">{overview.assets_reviewed}</div><div className="stat-note">Across {overview.project_count} {overview.project_count === 1 ? "project" : "projects"}</div></div><div className="stat-card"><div className="stat-label">Need attention</div><div className="stat-value" style={{ color: "var(--gold)" }}>{overview.assets_need_attention}</div><div className="stat-note">{overview.high_priority_items} high-priority {overview.high_priority_items === 1 ? "item" : "items"}</div></div><div className="stat-card"><div className="stat-label">Evidence coverage</div><div className="stat-value" style={{ color: "var(--green)" }}>{overview.evidence_coverage}%</div><div className="stat-note">Assets with evidence-backed cards</div></div><div className="stat-card"><div className="stat-label">Research runs</div><div className="stat-value">{overview.research_runs}</div><div className="stat-note">{overview.parallel_sources} Parallel-backed sources</div></div></div> : <div className="overview-unavailable">Live workspace metrics are temporarily unavailable.</div>}</section>{reviewProject ? <Link className="floating-review-link" href={`/projects/${reviewProject.id}/review` as Route}>Open review queue →</Link> : null}</WorkspaceShell>;
}
