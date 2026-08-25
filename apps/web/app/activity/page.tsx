import Link from "next/link";
import type { Route } from "next";
import { ActivityViewer } from "./activity-viewer";

export default function ActivityPage() {
  return (
    <div className="app-shell">
      <aside className="sidebar"><div className="brand"><div className="brand-mark">C</div><div><div className="brand-name">ClearCut</div><div className="brand-caption">Rights intelligence</div></div></div><div className="nav-label">Workspace</div><nav className="nav"><Link className="nav-item" href="/"><span className="nav-icon">⌂</span>Projects</Link><Link className="nav-item active" href={"/activity" as Route}><span className="nav-icon">◌</span>Activity</Link><Link className="nav-item" href={"/reports" as Route}><span className="nav-icon">↗</span>Reports</Link><Link className="nav-item" href={"/settings" as Route}><span className="nav-icon">⚙</span>Settings</Link></nav><div className="sidebar-bottom"><div className="account"><div className="avatar">SM</div><div><div className="account-name">Studio Meridian</div><div className="account-role">Producer workspace</div></div></div></div></aside>
      <main className="main"><header className="topbar"><div className="breadcrumbs"><Link href="/">Projects</Link><span>/</span><strong>Activity</strong></div><div className="topbar-actions"><div className="env-pill"><span className="env-dot" />Staging environment</div></div></header><div className="content"><section className="hero"><div><div className="eyebrow">Workspace accountability</div><h1>Activity and notifications.</h1><p>See what changed, who changed it, and which review actions need a response.</p></div></section><ActivityViewer /></div></main>
    </div>
  );
}
