import Link from "next/link";
import type { Route } from "next";
import { fetchProjects } from "@/lib/api";
import { ReportButton } from "../projects/[projectId]/report-button";

export default async function ReportsPage() {
  const projects = await fetchProjects();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">C</div><div><div className="brand-name">ClearCut</div><div className="brand-caption">Rights intelligence</div></div></div>
        <div className="nav-label">Workspace</div>
        <nav className="nav"><Link className="nav-item" href="/"><span className="nav-icon">⌂</span>Projects</Link><Link className="nav-item active" href={"/reports" as Route}><span className="nav-icon">↗</span>Reports</Link><Link className="nav-item" href={"/activity" as Route}><span className="nav-icon">◌</span>Activity</Link><Link className="nav-item" href={"/settings" as Route}><span className="nav-icon">⚙</span>Settings</Link></nav>
        <div className="sidebar-bottom"><div className="account"><div className="avatar">SM</div><div><div className="account-name">Studio Meridian</div><div className="account-role">Producer workspace</div></div></div></div>
      </aside>
      <main className="main">
        <header className="topbar"><div className="breadcrumbs"><Link href="/">Projects</Link><span>/</span><strong>Reports</strong></div><div className="topbar-actions"><div className="env-pill"><span className="env-dot" />Staging environment</div></div></header>
        <div className="content"><section className="hero"><div><div className="eyebrow">Clearance reporting</div><h1>Project reports.</h1><p>Generate, view, and download evidence-backed clearance reports for every project.</p></div><Link className="primary-button" href="/projects/new">+ New project</Link></section><section className="panel report-list">{projects.length === 0 ? <div className="review-empty">No projects yet. Create a project to generate a report.</div> : projects.map((project) => <div className="report-row" key={project.id}><div><strong>{project.title}</strong><span>{project.project_type} · {project.status}</span></div><div className="report-row-actions"><Link className="secondary-button" href={`/reports/${project.id}` as Route}>View report</Link><ReportButton projectId={project.id} /></div></div>)}</section></div>
      </main>
    </div>
  );
}
