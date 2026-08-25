"use client";

import Link from "next/link";
import type { Route } from "next";
import { useEffect, useState } from "react";
import type { Project } from "@/lib/types";
import { authorizedFetch as fetch } from "@/lib/api-client";
import { WorkspaceShell } from "@/components/workspace-shell";
import { ProjectTabs } from "@/components/project-tabs";
import { ReportButton } from "./report-button";
import { ReviewQueue } from "./review-queue";
import { ProjectHealth } from "./project-health";
import { OperationsPanel } from "./operations-panel";
import { RightsInventory } from "./rights-inventory";
import { ResearchPanel } from "./research-panel";
import { UploadForm } from "./upload-form";
import { ProductionDesk } from "./production-desk";
import { ProjectActivity } from "./project-activity";
import { ProjectSettings } from "./project-settings";

type ProjectWorkspaceProps = { projectId: string; section: "overview" | "source" | "inventory" | "research" | "review" | "requests" | "reports" | "activity" | "settings" };

function workflowCopy(status: Project["status"]): { title: string; body: string } {
  if (status === "complete") return { title: "Clearance review complete", body: "All researched assets have approved next actions. Open the report for production records." };
  if (status === "review") return { title: "Human review is still required", body: "Review each clearance card, record the producer decision, and create permission-request drafts where needed." };
  if (status === "active") return { title: "Analysis is in progress", body: "Continue researching extracted assets until each one has an evidence-backed clearance card." };
  return { title: "Project setup required", body: "Upload a screenplay from the Source tab to create the rights inventory." };
}

function NextActions({ project }: { project: Project }) {
  const steps = [
    ["01", "Ingest source material", "Upload and analyze the screenplay", project.status !== "draft", "/source"],
    ["02", "Research rights signals", "Collect evidence for each asset", project.status === "review" || project.status === "complete", "/research"],
    ["03", "Record human decisions", "Approve, escalate, or request more research", project.status === "complete", "/review"],
    ["04", "Prepare delivery report", "Package evidence for production records", project.status === "complete", "/reports"],
  ] as const;
  return <section className="panel"><div className="panel-header"><h2>Next actions</h2><span>Project flow</span></div><div className="checklist">{steps.map(([number, title, description, done, href]) => <Link className={`checklist-item ${done ? "done" : ""}`} href={`/projects/${project.id}${href}` as Route} key={number}><span>{number}</span><div><strong>{title}</strong><small>{description}</small></div><b>→</b></Link>)}</div></section>;
}

function ReportsPanel({ projectId }: { projectId: string }) {
  const [hasReport, setHasReport] = useState(false);
  useEffect(() => { void fetch(`/v1/projects/${projectId}/reports`, { cache: "no-store" }).then((response) => response.ok ? response.json() : []).then((reports: Array<{ id: string }>) => setHasReport(reports.length > 0)); }, [projectId]);
  return <section className="panel route-panel"><div className="panel-header"><div><h2>Clearance reports</h2><span>Evidence-backed production records</span></div><ReportButton projectId={projectId} /></div><div className="route-panel-body">{hasReport ? <><p>The latest report is ready for review, printing, and PDF download.</p><Link className="primary-button" href={`/reports/${projectId}` as Route}>View latest report</Link></> : <><p>No report has been generated yet. Complete the research and human review workflow first.</p><ReportButton projectId={projectId} /></>}</div></section>;
}

export function ProjectWorkspace({ projectId, section }: ProjectWorkspaceProps) {
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => { setLoading(true); void fetch(`/v1/projects/${projectId}`, { cache: "no-store" }).then(async (response) => { if (response.status === 404) throw new Error("Project not found."); if (!response.ok) throw new Error("Unable to load this project."); setProject(await response.json() as Project); }).catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load this project.")).finally(() => setLoading(false)); }, [projectId]);
  if (loading) return <WorkspaceShell active="projects" breadcrumbs={<><Link href="/">Projects</Link><span>/</span><strong>Loading project…</strong></>}><div className="loading-panel panel">Loading project workspace…</div></WorkspaceShell>;
  if (error || !project) return <WorkspaceShell active="projects" breadcrumbs={<><Link href="/">Projects</Link><span>/</span><strong>Project</strong></>}><section className="panel empty-state"><span className="eyebrow">Workspace error</span><h1>{error || "Project not found."}</h1><Link className="secondary-button" href="/">Back to projects</Link></section></WorkspaceShell>;
  const copy = workflowCopy(project.status);
  const targetRelease = project.target_release_at ? new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric" }).format(new Date(project.target_release_at)) : "Not set";
  return <WorkspaceShell projectId={project.id} active="projects" breadcrumbs={<><Link href="/">Projects</Link><span>/</span><strong>{project.title}</strong></>}><section className="project-header"><div><div className="eyebrow">{project.project_type} · Project workspace</div><h1>{project.title}</h1><p>Target release · {targetRelease} &nbsp;·&nbsp; {project.distribution_modes.join(" + ") || "Distribution plan not set"}</p></div><div className="header-actions"><span className={`status-chip ${project.status}`}>{project.status.replaceAll("_", " ")}</span><ReportButton projectId={project.id} /></div></section><section className={`workflow-banner ${project.status}`}><div><strong>{copy.title}</strong><p>{copy.body}</p></div>{project.status === "complete" ? <Link className="secondary-button" href={`/reports/${project.id}` as Route}>Open report</Link> : <Link className="secondary-button" href={`/projects/${project.id}/source` as Route}>Open source</Link>}</section><ProjectTabs projectId={project.id} />{section === "overview" ? <><ProjectHealth projectId={project.id} /><OperationsPanel projectId={project.id} /><div className="project-layout"><NextActions project={project} /><div className="side-stack"><section className="panel route-panel"><div className="panel-header"><h2>Workspace map</h2><span>Dedicated sections</span></div><div className="route-list"><Link href={`/projects/${project.id}/source` as Route}><strong>Source desk</strong><span>Versions, files, and review links</span></Link><Link href={`/projects/${project.id}/inventory` as Route}><strong>Rights inventory</strong><span>Every extracted asset and its evidence</span></Link><Link href={`/projects/${project.id}/research` as Route}><strong>Research lab</strong><span>Parallel-backed findings and gaps</span></Link><Link href={`/projects/${project.id}/reports` as Route}><strong>Reports</strong><span>Styled review and PDF exports</span></Link></div></section><div className="disclaimer"><strong>Human review required.</strong><br />ClearCut supports rights operations; it does not provide legal advice or declare an asset legally cleared.</div></div></div></> : null}{section === "source" ? <><UploadForm projectId={project.id} /><ProductionDesk projectId={project.id} /></> : null}{section === "inventory" ? <RightsInventory projectId={project.id} /> : null}{section === "research" ? <ResearchPanel projectId={project.id} /> : null}{section === "review" ? <ReviewQueue projectId={project.id} /> : null}{section === "requests" ? <ReviewQueue projectId={project.id} mode="requests" /> : null}{section === "reports" ? <ReportsPanel projectId={project.id} /> : null}{section === "activity" ? <ProjectActivity projectId={project.id} /> : null}{section === "settings" ? <ProjectSettings project={project} /> : null}</WorkspaceShell>;
}
