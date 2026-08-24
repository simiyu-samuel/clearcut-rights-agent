import Link from "next/link";
import type { Route } from "next";
import { NewProjectForm } from "./new-project-form";

export default function NewProjectPage() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">C</div><div><div className="brand-name">ClearCut</div><div className="brand-caption">Rights intelligence</div></div></div>
        <div className="nav-label">Workspace</div>
        <nav className="nav"><Link className="nav-item" href="/"><span className="nav-icon">⌂</span>Projects</Link><Link className="nav-item" href={"/reports" as Route}><span className="nav-icon">↗</span>Reports</Link></nav>
        <div className="sidebar-bottom"><div className="account"><div className="avatar">SM</div><div><div className="account-name">Studio Meridian</div><div className="account-role">Producer workspace</div></div></div></div>
      </aside>
      <main className="main">
        <header className="topbar"><div className="breadcrumbs"><Link href="/">Projects</Link><span>/</span><strong>New project</strong></div><div className="topbar-actions"><div className="env-pill"><span className="env-dot" />Staging environment</div></div></header>
        <div className="content"><section className="project-header"><div><div className="eyebrow">Workspace setup</div><h1>Start a project.</h1><p>Define the production context before uploading creative material.</p></div></section><NewProjectForm /></div>
      </main>
    </div>
  );
}
