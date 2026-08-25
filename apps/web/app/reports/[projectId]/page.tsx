import Link from "next/link";
import type { Route } from "next";
import { notFound } from "next/navigation";
import { fetchProject, fetchReports } from "@/lib/api";
import { ReportButton } from "../../projects/[projectId]/report-button";
import { ReportDocument } from "../report-document";

export default async function ReportPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const [project, reports] = await Promise.all([fetchProject(projectId), fetchReports(projectId)]);
  if (!project) notFound();
  const report = reports[0];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">C</div><div><div className="brand-name">ClearCut</div><div className="brand-caption">Rights intelligence</div></div></div>
        <div className="nav-label">Workspace</div>
        <nav className="nav"><Link className="nav-item" href="/"><span className="nav-icon">⌂</span>Projects</Link><Link className="nav-item" href={`/projects/${project.id}` as Route}><span className="nav-icon">◈</span>Review queue</Link><Link className="nav-item active" href="/reports"><span className="nav-icon">↗</span>Reports</Link><Link className="nav-item" href={"/activity" as Route}><span className="nav-icon">◌</span>Activity</Link><Link className="nav-item" href={"/settings" as Route}><span className="nav-icon">⚙</span>Settings</Link></nav>
        <div className="sidebar-bottom"><div className="account"><div className="avatar">SM</div><div><div className="account-name">Studio Meridian</div><div className="account-role">Producer workspace</div></div></div></div>
      </aside>
      <main className="main">
        <header className="topbar"><div className="breadcrumbs"><Link href="/reports">Reports</Link><span>/</span><strong>{project.title}</strong></div><div className="topbar-actions"><div className="env-pill"><span className="env-dot" />Staging environment</div></div></header>
        <div className="content"><section className="hero"><div><div className="eyebrow">{project.project_type} · {project.status}</div><h1>{project.title}</h1><p>Review the latest evidence-backed clearance report and download it for production records.</p></div><ReportButton projectId={project.id} /></section>{report ? <ReportDocument projectId={project.id} project={project} report={report} reports={reports} /> : <section className="panel report-empty"><h2>No report generated yet.</h2><p>Generate a report from this page after the research and approval decisions are complete.</p><ReportButton projectId={project.id} /></section>}</div>
      </main>
    </div>
  );
}
