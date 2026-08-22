import Link from "next/link";
import type { Route } from "next";
import { demoAssets, demoProjects } from "@/lib/demo-data";

export default async function ProjectPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const project = demoProjects.find((item) => item.id === projectId) ?? demoProjects[0];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">C</div><div><div className="brand-name">ClearCut</div><div className="brand-caption">Rights intelligence</div></div></div>
        <div className="nav-label">Workspace</div>
        <nav className="nav"><Link className="nav-item" href="/"><span className="nav-icon">⌂</span>Projects</Link><Link className="nav-item active" href={`/projects/${project.id}` as Route}><span className="nav-icon">◈</span>Review queue</Link><Link className="nav-item" href="/"><span className="nav-icon">↗</span>Reports</Link></nav>
        <div className="sidebar-bottom"><div className="account"><div className="avatar">SM</div><div><div className="account-name">Studio Meridian</div><div className="account-role">Producer workspace</div></div></div></div>
      </aside>

      <main className="main">
        <header className="topbar"><div className="breadcrumbs"><Link href="/">Projects</Link><span>/</span><strong>{project.title}</strong></div><div className="topbar-actions"><div className="env-pill"><span className="env-dot" />Demo environment</div><button className="icon-button" aria-label="Notifications">◌</button></div></header>
        <div className="content">
          <section className="project-header"><div><div className="eyebrow">Feature film · Review queue</div><h1>{project.title}</h1><p>Target release · 18 November 2026 &nbsp;·&nbsp; {project.distribution_modes.join(" + ")}</p></div><div className="header-actions"><button className="secondary-button">Export report</button><button className="primary-button">Start analysis</button></div></section>
          <div className="project-layout">
            <section className="panel"><div className="panel-header"><h2>Rights inventory</h2><span>5 assets · 3 need attention</span></div><div className="asset-list">{demoAssets.map((asset) => <div className="asset-row" key={asset.number}><div className="asset-number">{asset.number}</div><div><div className="asset-name">{asset.name}</div><div className="asset-context">{asset.context}</div></div><div className="asset-category">{asset.category}</div><div className={`risk-label ${asset.risk}`}>{asset.risk === "high" ? "High risk" : asset.risk === "medium" ? "Review" : "Likely clear"}</div></div>)}</div></section>
            <div className="side-stack">
              <section className="panel"><div className="panel-header"><h2>Latest evidence</h2><span>Parallel</span></div><div className="evidence-list"><div className="evidence-item"><div className="evidence-title">Official licensing page found</div><div className="evidence-source">music-rights.example · 4 min ago</div></div><div className="evidence-item"><div className="evidence-title">Trademark owner needs confirmation</div><div className="evidence-source">brand-registry.example · 7 min ago</div></div><div className="evidence-item"><div className="evidence-title">Location authority identified</div><div className="evidence-source">city-filming.example · 11 min ago</div></div></div></section>
              <section className="panel"><div className="panel-header"><h2>Project activity</h2><span>Today</span></div><div className="timeline"><div className="timeline-item"><div className="timeline-dot" /><div><h3>Research run completed</h3><p>5 source records normalized · 08:15</p></div></div><div className="timeline-item"><div className="timeline-dot" /><div><h3>3 assets moved to review</h3><p>Risk policy v0.1 · 08:12</p></div></div><div className="timeline-item"><div className="timeline-dot" /><div><h3>Screenplay v1 uploaded</h3><p>The Last Signal · 08:04</p></div></div></div></section>
              <div className="disclaimer"><strong>Human review required.</strong><br />ClearCut provides research and workflow support. It does not provide legal advice or declare an asset legally cleared.</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
