"use client";

import Link from "next/link";
import type { Route } from "next";
import { useCallback, useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { authorizedFetch as fetch } from "@/lib/api-client";
import type { Project, WorkspaceOverview } from "@/lib/types";

function statusLabel(status: string) {
  return status === "review" ? "Needs review" : status[0].toUpperCase() + status.slice(1);
}

function DashboardSkeleton() {
  return (
    <div className="project-grid" aria-busy="true" aria-label="Loading projects">
      {["one", "two", "three"].map((key) => <div className="project-card skeleton-card" key={key}><span className="skeleton-block skeleton-title" /><span className="skeleton-block skeleton-copy" /><span className="skeleton-block skeleton-copy short" /></div>)}
    </div>
  );
}

function StatsSkeleton() {
  return <div className="stats-grid" aria-busy="true" aria-label="Loading workspace metrics">{["one", "two", "three", "four"].map((key) => <div className="stat-card skeleton-stat" key={key}><span className="skeleton-block skeleton-label" /><span className="skeleton-block skeleton-value" /><span className="skeleton-block skeleton-note" /></div>)}</div>;
}

export function WorkspaceHome() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [overview, setOverview] = useState<WorkspaceOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const loadWorkspace = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      const [projectsResponse, overviewResponse] = await Promise.all([
        fetch("/v1/projects", { cache: "no-store" }),
        fetch("/v1/workspace/overview", { cache: "no-store" }),
      ]);
      const failures: string[] = [];
      if (projectsResponse.ok) setProjects(await projectsResponse.json() as Project[]);
      else failures.push("projects");
      if (overviewResponse.ok) setOverview(await overviewResponse.json() as WorkspaceOverview);
      else failures.push("workspace metrics");
      if (failures.length) setMessage(`Live ${failures.join(" and ")} could not be loaded. Retry to refresh the workspace.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load the live workspace. Retry to refresh.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadWorkspace(); }, [loadWorkspace]);

  const reviewProject = projects.find((project) => project.status === "review") ?? projects[0];
  return (
    <WorkspaceShell active="projects" breadcrumbs={<><span>Workspace</span><span>/</span><strong>Projects</strong></>}>
      <section className="hero">
        <div>
          <div className="eyebrow">Production workspace · {projects.length} {projects.length === 1 ? "project" : "projects"}</div>
          <h1>Keep the story moving.</h1>
          <p>ClearCut turns scripts and cuts into evidence-backed rights work, so your production team can see what needs attention before distribution.</p>
        </div>
        <div className="hero-actions"><span className="live-data-label"><span className="env-dot" />Live workspace data</span><Link className="primary-button" href="/projects/new">+ New project</Link></div>
      </section>
      {message ? <div className="dashboard-error" role="alert"><div><strong>Workspace data needs attention</strong><p>{message}</p></div><button className="secondary-button" disabled={loading} onClick={() => void loadWorkspace()} type="button">{loading ? "Refreshing…" : "Retry"}</button></div> : null}
      <section>
        <div className="section-heading"><h2>Active projects</h2><span className="section-heading-meta">{loading ? "Refreshing" : `${projects.length} total`}</span></div>
        {loading ? <DashboardSkeleton /> : projects.length ? <div className="project-grid">{projects.map((project) => <Link className="project-card" href={`/projects/${project.id}` as Route} key={project.id}><div className="project-card-top"><div><h3>{project.title}</h3><div className="project-type">{project.project_type}</div></div><span className={`status-chip ${project.status}`}>{statusLabel(project.status)}</span></div><div className="project-card-footer"><div className="card-meta">{project.territories.join(" · ") || "Territories not set"}<br />Updated {new Date(project.updated_at).toLocaleDateString()}</div><div className={`risk-count ${project.status === "complete" ? "ready" : ""}`}>{project.status === "review" ? "Human review" : project.status === "complete" ? "Delivery ready" : "In progress"}</div></div></Link>)}</div> : <section className="panel empty-state"><span className="eyebrow">First production</span><h2>No projects yet.</h2><p>Create a project to define the production context, upload source material, and start the evidence workflow.</p><Link className="primary-button" href="/projects/new">Create your first project</Link></section>}
      </section>
      <section>
        <div className="section-heading"><div><h2>Workspace overview</h2><p className="panel-subtitle">Operational metrics from the last 30 days</p></div><span className="section-heading-meta">{overview ? "Live" : loading ? "Loading" : "Unavailable"}</span></div>
        {loading ? <StatsSkeleton /> : overview ? <div className="stats-grid"><div className="stat-card"><div className="stat-label">Assets reviewed</div><div className="stat-value">{overview.assets_reviewed}</div><div className="stat-note">Across {overview.project_count} {overview.project_count === 1 ? "project" : "projects"}</div></div><div className="stat-card"><div className="stat-label">Need attention</div><div className="stat-value" style={{ color: "var(--gold)" }}>{overview.assets_need_attention}</div><div className="stat-note">{overview.high_priority_items} high-priority {overview.high_priority_items === 1 ? "item" : "items"}</div></div><div className="stat-card"><div className="stat-label">Evidence coverage</div><div className="stat-value" style={{ color: "var(--green)" }}>{overview.evidence_coverage}%</div><div className="stat-note">Assets with evidence-backed cards</div></div><div className="stat-card"><div className="stat-label">Research runs</div><div className="stat-value">{overview.research_runs}</div><div className="stat-note">{overview.parallel_sources} Parallel-backed sources</div></div></div> : <div className="overview-unavailable"><strong>Live metrics are unavailable.</strong><span>Retry the workspace load to see current project activity.</span></div>}
      </section>
      {reviewProject ? <Link className="floating-review-link" href={`/projects/${reviewProject.id}/review` as Route}>Open review queue →</Link> : null}
    </WorkspaceShell>
  );
}
