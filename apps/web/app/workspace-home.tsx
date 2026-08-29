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

function StatCard({ label, value, note, tone = "" }: { label: string; value: string | number; note: string; tone?: "attention" | "good" | "" }) {
  return <div className="stat-card dashboard-stat-card"><div className="stat-label">{label}</div><div className={`stat-value ${tone}`}>{value}</div><div className="stat-note">{note}</div></div>;
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
  const projectsInReview = projects.filter((project) => project.status === "review").length;
  return <WorkspaceShell active="overview" breadcrumbs={<><span>Studio Meridian</span><span>/</span><strong>Overview</strong></>}>
    <section className="hero dashboard-hero"><div><div className="eyebrow">Workspace overview</div><h1>Keep the story moving.</h1><p>See what needs attention across your productions before it becomes a delivery blocker.</p></div><div className="dashboard-hero-actions"><div className="dashboard-actions"><Link className="secondary-button" href="/review">Open review queue</Link><Link className="primary-button" href="/projects/new">+ New project</Link></div><span className="live-data-label"><span className="env-dot" />{loading ? "Refreshing workspace" : "Live workspace data"}</span></div></section>
    {message ? <div className="dashboard-error" role="alert"><div><strong>Workspace data needs attention</strong><p>{message}</p></div><button className="secondary-button" disabled={loading} onClick={() => void loadWorkspace()} type="button">{loading ? "Refreshing…" : "Retry"}</button></div> : null}
    {!loading && overview && overview.assets_need_attention > 0 ? <section className="priority-banner" aria-label="Priority work"><div className="priority-icon">!</div><div className="priority-copy"><strong>{overview.assets_need_attention} {overview.assets_need_attention === 1 ? "item needs" : "items need"} attention</strong><span>{overview.high_priority_items} high-priority {overview.high_priority_items === 1 ? "blocker requires" : "blockers require"} human review.</span></div><div className="priority-actions"><Link className="priority-button" href="/review">Review priority items</Link><Link className="priority-link" href="/review">View all blockers</Link></div></section> : null}
    <section><div className="section-heading dashboard-section-heading"><div><h2>Workspace signals</h2><p className="panel-subtitle">Operational metrics from the last {overview?.period_days ?? 30} days</p></div><span className="section-heading-meta">{overview ? "Live" : loading ? "Loading" : "Unavailable"}</span></div>{loading ? <StatsSkeleton /> : overview ? <div className="stats-grid dashboard-stats"><StatCard label="Active projects" value={projects.filter((project) => !["complete", "archived"].includes(project.status)).length} note={`${projectsInReview} currently in review`} /><StatCard label="Assets reviewed" value={overview.assets_reviewed} note={`Across ${overview.project_count} ${overview.project_count === 1 ? "project" : "projects"}`} /><StatCard label="Evidence coverage" value={`${overview.evidence_coverage}%`} note={`${overview.parallel_sources} Parallel-backed sources`} tone={overview.evidence_coverage >= 80 ? "good" : "attention"} /><StatCard label="Research runs" value={overview.research_runs} note={`${overview.high_priority_items} high-priority ${overview.high_priority_items === 1 ? "item" : "items"}`} tone={overview.high_priority_items ? "attention" : "good"} /></div> : <div className="overview-unavailable"><strong>Live metrics are unavailable.</strong><span>Retry the workspace load to see current project activity.</span></div>}</section>
    <section className="dashboard-work-grid"><div><div className="section-heading dashboard-section-heading"><div><h2>Continue where you left off</h2><p className="panel-subtitle">Open a production at its latest live state.</p></div><Link href="/projects">View all →</Link></div>{loading ? <DashboardSkeleton /> : projects.length ? <div className="continue-list">{projects.slice(0, 3).map((project) => <Link className="continue-card panel" href={`/projects/${project.id}` as Route} key={project.id}><div className="continue-card-top"><div><h3>{project.title}</h3><span>{project.project_type}</span></div><span className={`status-chip ${project.status}`}>{statusLabel(project.status)}</span></div><div className="continue-card-meta"><span>{project.territories.join(" · ") || "Territories not set"}</span><span>Updated {new Date(project.updated_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</span></div><div className="continue-card-action">Open project <span>↗</span></div></Link>)}</div> : <section className="panel empty-state"><span className="eyebrow">First production</span><h2>No projects yet.</h2><p>Create a project to define the production context, upload source material, and start the evidence workflow.</p><Link className="primary-button" href="/projects/new">Create your first project</Link></section>}</div><aside className="panel readiness-panel"><div className="panel-header"><div><h2>Delivery readiness</h2><p className="panel-subtitle">Current workspace blockers</p></div><span className={`readiness-status ${overview && overview.high_priority_items ? "conditional" : "ready"}`}>{overview && overview.high_priority_items ? "Conditional" : "Ready"}</span></div><div className="readiness-score"><strong>{overview?.evidence_coverage ?? 0}%</strong><span>evidence coverage</span></div><div className="readiness-progress"><span style={{ width: `${Math.min(100, overview?.evidence_coverage ?? 0)}%` }} /></div><div className="readiness-list"><div><span className="readiness-dot red" /><div><strong>High-priority blockers</strong><small>{overview?.high_priority_items ?? "—"} require human review</small></div></div><div><span className="readiness-dot gold" /><div><strong>Open attention items</strong><small>{overview?.assets_need_attention ?? "—"} assets need a next action</small></div></div><div><span className="readiness-dot blue" /><div><strong>Projects in review</strong><small>{projectsInReview} production{projectsInReview === 1 ? "" : "s"} awaiting decisions</small></div></div></div><Link className="secondary-button readiness-link" href="/review">Open readiness view</Link></aside></section>
    {reviewProject ? <Link className="floating-review-link" href={`/projects/${reviewProject.id}/review` as Route}>Open review queue →</Link> : null}
  </WorkspaceShell>;
}
