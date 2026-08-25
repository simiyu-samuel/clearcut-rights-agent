import Link from "next/link";
import type { Route } from "next";
import { notFound } from "next/navigation";
import { fetchProject } from "@/lib/api";
import { ReportButton } from "./report-button";
import { ReviewQueue } from "./review-queue";
import { ProjectHealth } from "./project-health";
import { OperationsPanel } from "./operations-panel";
import { RightsInventory } from "./rights-inventory";
import { ResearchPanel } from "./research-panel";
import { UploadForm } from "./upload-form";
import { ProductionDesk } from "./production-desk";

export default async function ProjectPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const project = await fetchProject(projectId);
  if (!project) {
    notFound();
  }
  const targetRelease = project.target_release_at
    ? new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric" }).format(new Date(project.target_release_at))
    : "Not set";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">C</div><div><div className="brand-name">ClearCut</div><div className="brand-caption">Rights intelligence</div></div></div>
        <div className="nav-label">Workspace</div>
        <nav className="nav"><Link className="nav-item" href="/"><span className="nav-icon">⌂</span>Projects</Link><Link className="nav-item active" href={`/projects/${project.id}` as Route}><span className="nav-icon">◈</span>Review queue</Link><Link className="nav-item" href={"/reports" as Route}><span className="nav-icon">↗</span>Reports</Link><Link className="nav-item" href={"/activity" as Route}><span className="nav-icon">◌</span>Activity</Link><Link className="nav-item" href={"/settings" as Route}><span className="nav-icon">⚙</span>Settings</Link></nav>
        <div className="sidebar-bottom"><div className="account"><div className="avatar">SM</div><div><div className="account-name">Studio Meridian</div><div className="account-role">Producer workspace</div></div></div></div>
      </aside>

      <main className="main">
        <header className="topbar"><div className="breadcrumbs"><Link href="/">Projects</Link><span>/</span><strong>{project.title}</strong></div><div className="topbar-actions"><div className="env-pill"><span className="env-dot" />Staging environment</div><button className="icon-button" aria-label="Notifications">◌</button></div></header>
        <div className="content">
          <section className="project-header"><div><div className="eyebrow">{project.project_type} · Review queue</div><h1>{project.title}</h1><p>Target release · {targetRelease} &nbsp;·&nbsp; {project.distribution_modes.join(" + ") || "Distribution plan not set"}</p></div><div className="header-actions"><span className={`status-chip ${project.status}`}>{project.status.replaceAll("_", " ")}</span><ReportButton projectId={project.id} /></div></section>
          <section className={`workflow-banner ${project.status}`}><div><strong>{project.status === "complete" ? "Clearance review complete" : project.status === "review" ? "Human review is still required" : project.status === "active" ? "Analysis is in progress" : "Project setup required"}</strong><p>{project.status === "complete" ? "All researched assets have approved next actions. Generate or view the latest report for production records." : project.status === "review" ? "Review each clearance card, record the producer decision, and create permission-request drafts where needed." : project.status === "active" ? "Continue researching extracted assets until each one has an evidence-backed clearance card." : "Upload a screenplay and start analysis to create the rights inventory."}</p></div>{project.status === "complete" ? <Link className="secondary-button" href={`/reports/${project.id}` as Route}>Open report</Link> : null}</section>
          <ProjectHealth projectId={project.id} />
          <OperationsPanel projectId={project.id} />
          <UploadForm projectId={project.id} />
          <ProductionDesk projectId={project.id} />
          <ResearchPanel projectId={project.id} />
          <ReviewQueue projectId={project.id} />
          <div className="project-layout">
            <RightsInventory projectId={project.id} />
            <div className="side-stack">
              <section className="panel"><div className="panel-header"><h2>Next actions</h2><span>Project flow</span></div><div className="checklist"><div className={`checklist-item ${project.status !== "draft" ? "done" : ""}`}><span>01</span><div><strong>Ingest source material</strong><small>Upload and analyze the screenplay</small></div></div><div className={`checklist-item ${project.status === "review" || project.status === "complete" ? "done" : ""}`}><span>02</span><div><strong>Research rights signals</strong><small>Collect evidence for each asset</small></div></div><div className={`checklist-item ${project.status === "complete" ? "done" : ""}`}><span>03</span><div><strong>Record human decisions</strong><small>Approve, escalate, or request more research</small></div></div><div className={`checklist-item ${project.status === "complete" ? "done" : ""}`}><span>04</span><div><strong>Prepare delivery report</strong><small>Package evidence for production records</small></div></div></div></section>
              <div className="disclaimer"><strong>Human review required.</strong><br />ClearCut provides research and workflow support. It does not provide legal advice or declare an asset legally cleared.</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
