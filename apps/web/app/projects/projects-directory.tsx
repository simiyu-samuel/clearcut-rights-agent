"use client";

import Link from "next/link";
import type { Route } from "next";
import { useCallback, useEffect, useMemo, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { authorizedFetch as fetch } from "@/lib/api-client";
import type { Project, ProjectStatus } from "@/lib/types";

const statuses: Array<"all" | ProjectStatus> = ["all", "active", "review", "draft", "complete", "archived"];

function statusLabel(status: string) {
  return status === "review" ? "In review" : status.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function ProjectsSkeleton() {
  return <div className="directory-table" aria-busy="true" aria-label="Loading projects"><div className="directory-table-head"><span>Project</span><span>Status</span><span>Source</span><span>Last activity</span><span /></div>{["one", "two", "three"].map((key) => <div className="directory-row skeleton-directory-row" key={key}><span className="skeleton-block skeleton-row-title" /><span className="skeleton-block skeleton-status" /><span className="skeleton-block skeleton-copy" /><span className="skeleton-block skeleton-copy" /><span className="skeleton-block skeleton-row-actions" /></div>)}</div>;
}

export function ProjectsDirectory() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"all" | ProjectStatus>("all");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      const response = await fetch("/v1/projects", { cache: "no-store" });
      if (!response.ok) throw new Error("Unable to load projects. Retry to refresh the directory.");
      setProjects(await response.json() as Project[]);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load projects. Retry to refresh the directory.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => projects.filter((project) => {
    const matchesStatus = status === "all" || project.status === status;
    const normalizedQuery = query.trim().toLowerCase();
    const matchesQuery = !normalizedQuery || [project.title, project.project_type, ...project.territories, ...project.distribution_modes].join(" ").toLowerCase().includes(normalizedQuery);
    return matchesStatus && matchesQuery;
  }), [projects, query, status]);

  return <WorkspaceShell active="projects" breadcrumbs={<><span>Studio Meridian</span><span>/</span><strong>Projects</strong></>}>
    <section className="hero directory-hero">
      <div><div className="eyebrow">Production directory · {projects.length} {projects.length === 1 ? "project" : "projects"}</div><h1>Projects</h1><p>Every production, one accountable rights workspace.</p></div>
      <div className="hero-actions"><span className="live-data-label"><span className="env-dot" />Live workspace data</span><Link className="primary-button" href="/projects/new">+ New project</Link></div>
    </section>
    {message ? <div className="dashboard-error" role="alert"><div><strong>Projects could not be loaded</strong><p>{message}</p></div><button className="secondary-button" disabled={loading} onClick={() => void load()} type="button">Retry</button></div> : null}
    <section className="directory-toolbar panel"><div className="directory-search"><span aria-hidden="true">⌕</span><input aria-label="Search projects" onChange={(event) => setQuery(event.target.value)} placeholder="Search projects, formats, territories…" value={query} /></div><div className="directory-filters" role="group" aria-label="Project status filters">{statuses.map((value) => <button className={`filter-chip ${status === value ? "active" : ""}`} key={value} onClick={() => setStatus(value)} type="button">{value === "all" ? "All projects" : statusLabel(value)}</button>)}</div></section>
    {loading ? <ProjectsSkeleton /> : filtered.length ? <section className="directory-table panel" aria-label="Projects directory"><div className="directory-table-head"><span>Project</span><span>Status</span><span>Scope</span><span>Last activity</span><span /></div>{filtered.map((project) => <Link className="directory-row" href={`/projects/${project.id}` as Route} key={project.id}><div className="directory-project"><strong>{project.title}</strong><small>{project.project_type}</small></div><span className={`status-chip ${project.status}`}>{statusLabel(project.status)}</span><div className="directory-scope"><span>{project.territories.join(" · ") || "Territories not set"}</span><small>{project.distribution_modes.join(" + ") || "Distribution not set"}</small></div><div className="directory-activity"><span>Updated</span><small>{new Date(project.updated_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</small></div><span className="directory-open">Open project →</span></Link>)}</section> : <section className="panel empty-state"><span className="eyebrow">{projects.length ? "No matching projects" : "First production"}</span><h2>{projects.length ? "Nothing matches these filters." : "No projects yet."}</h2><p>{projects.length ? "Try a different search or status filter." : "Create a project to define the production context and start the evidence workflow."}</p>{projects.length ? <button className="secondary-button" onClick={() => { setQuery(""); setStatus("all"); }} type="button">Clear filters</button> : <Link className="primary-button" href="/projects/new">Create your first project</Link>}</section>}
  </WorkspaceShell>;
}
