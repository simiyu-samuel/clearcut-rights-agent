import Link from "next/link";
import type { Route } from "next";
import { fetchProjects, fetchWorkspaceOverview } from "@/lib/api";

function statusLabel(status: string) {
  return status === "review" ? "Needs review" : status[0].toUpperCase() + status.slice(1);
}

export default async function HomePage() {
  const [projects, overview] = await Promise.all([fetchProjects(), fetchWorkspaceOverview()]);
  const reviewProject = projects.find((project) => project.status === "review") ?? projects[0];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">C</div>
          <div><div className="brand-name">ClearCut</div><div className="brand-caption">Rights intelligence</div></div>
        </div>
        <div className="nav-label">Workspace</div>
        <nav className="nav">
          <Link className="nav-item active" href="/"><span className="nav-icon">⌂</span>Projects</Link>
          <Link className="nav-item" href={(reviewProject ? `/projects/${reviewProject.id}` : "/") as Route}><span className="nav-icon">◈</span>Review queue</Link>
          <Link className="nav-item" href={"/reports" as Route}><span className="nav-icon">↗</span>Reports</Link>
          <Link className="nav-item" href={"/activity" as Route}><span className="nav-icon">◌</span>Activity</Link>
          <Link className="nav-item" href={"/settings" as Route}><span className="nav-icon">⚙</span>Settings</Link>
        </nav>
        <div className="sidebar-bottom">
          <div className="account"><div className="avatar">SM</div><div><div className="account-name">Studio Meridian</div><div className="account-role">Producer workspace</div></div></div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><span>/</span><strong>Projects</strong></div>
          <div className="topbar-actions"><div className="env-pill"><span className="env-dot" />Staging environment</div><button className="icon-button" aria-label="Notifications">◌</button></div>
        </header>

        <div className="content">
          <section className="hero">
            <div><div className="eyebrow">Studio Meridian · {projects.length} {projects.length === 1 ? "project" : "projects"}</div><h1>Keep the story moving.</h1><p>ClearCut turns scripts and cuts into evidence-backed rights work, so your production team can see what needs attention before distribution.</p></div>
            <Link className="primary-button" href="/projects/new">+ New project</Link>
          </section>

          <section>
            <div className="section-heading"><h2>Active projects</h2><Link href="/">View all →</Link></div>
            <div className="project-grid">
              {projects.map((project) => (
                <Link className="project-card" href={`/projects/${project.id}` as Route} key={project.id}>
                  <div className="project-card-top"><div><h3>{project.title}</h3><div className="project-type">{project.project_type}</div></div><span className={`status-chip ${project.status}`}>{statusLabel(project.status)}</span></div>
                  <div className="project-card-footer"><div className="card-meta">{project.territories.join(" · ") || "Territories not set"}<br />Updated {new Date(project.updated_at).toLocaleDateString()}</div><div className="risk-count">{project.status === "review" ? "Needs review" : "No open risks"}</div></div>
                </Link>
              ))}
            </div>
          </section>

          <section>
            <div className="section-heading"><h2>Workspace overview</h2><span className="card-meta">Last 30 days</span></div>
            {overview ? <div className="stats-grid">
              <div className="stat-card"><div className="stat-label">Assets reviewed</div><div className="stat-value">{overview.assets_reviewed}</div><div className="stat-note">Across {overview.project_count} {overview.project_count === 1 ? "project" : "projects"}</div></div>
              <div className="stat-card"><div className="stat-label">Need attention</div><div className="stat-value" style={{ color: "var(--gold)" }}>{overview.assets_need_attention}</div><div className="stat-note">{overview.high_priority_items} high-priority {overview.high_priority_items === 1 ? "item" : "items"}</div></div>
              <div className="stat-card"><div className="stat-label">Evidence coverage</div><div className="stat-value" style={{ color: "var(--green)" }}>{overview.evidence_coverage}%</div><div className="stat-note">Assets with evidence-backed cards</div></div>
              <div className="stat-card"><div className="stat-label">Research runs</div><div className="stat-value">{overview.research_runs}</div><div className="stat-note">{overview.parallel_sources} Parallel-backed sources</div></div>
            </div> : <div className="overview-unavailable">Live workspace metrics are temporarily unavailable. Project data is still available; refresh after the API deployment completes.</div>}
          </section>
        </div>
      </main>
    </div>
  );
}
