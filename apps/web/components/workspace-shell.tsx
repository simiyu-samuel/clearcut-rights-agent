"use client";

import Link from "next/link";
import type { Route } from "next";
import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

type WorkspaceShellProps = {
  children: ReactNode;
  breadcrumbs: ReactNode;
  active?: "projects" | "review" | "reports" | "activity" | "settings";
  projectId?: string;
};

export function WorkspaceShell({ children, breadcrumbs, active, projectId }: WorkspaceShellProps) {
  const pathname = usePathname();
  const auth = useAuth();
  const initials = (auth.user?.displayName ?? "ClearCut")
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><img className="brand-logo" src="/clearcut-logo.png" alt="ClearCut" /></div>
        <div className="nav-label">Workspace</div>
        <nav className="nav">
          <Link className={`nav-item ${active === "projects" ? "active" : ""}`} href="/"><span className="nav-icon">⌂</span>Projects</Link>
          <Link className={`nav-item ${active === "review" || Boolean(projectId && pathname.includes(`/projects/${projectId}/review`)) ? "active" : ""}`} href={(projectId ? `/projects/${projectId}/review` : "/review") as Route}><span className="nav-icon">◈</span>Review queue</Link>
          <Link className={`nav-item ${active === "reports" ? "active" : ""}`} href="/reports"><span className="nav-icon">↗</span>Reports</Link>
          <Link className={`nav-item ${active === "activity" ? "active" : ""}`} href="/activity"><span className="nav-icon">◌</span>Activity</Link>
          <Link className={`nav-item ${active === "settings" ? "active" : ""}`} href="/settings"><span className="nav-icon">⚙</span>Settings</Link>
        </nav>
        <div className="sidebar-bottom">
          <div className="workspace-account">
            <div className="account"><div className="avatar">{initials}</div><div><div className="account-name">{auth.user?.displayName ?? "ClearCut user"}</div><div className="account-role">{auth.organizationRole ?? "Workspace member"}</div></div></div>
            {auth.memberships.length > 1 ? <select aria-label="Select organization" className="workspace-org-select" value={auth.organizationId ?? ""} onChange={(event) => auth.selectOrganization(event.target.value)}>{auth.memberships.map((membership) => <option key={membership.organization_id} value={membership.organization_id}>{membership.organization_id}</option>)}</select> : null}
            <button className="workspace-signout" onClick={() => void auth.signOut()} type="button">Sign out</button>
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar"><div className="breadcrumbs">{breadcrumbs}</div><div className="topbar-actions"><div className="env-pill"><span className="env-dot" />{process.env.NEXT_PUBLIC_AUTH_MODE === "identity_platform" ? "Secure workspace" : "Local demo mode"}</div><Link className="icon-button" aria-label="Open activity and notifications" href="/activity">◌</Link></div></header>
        <div className="content">{children}</div>
      </main>
    </div>
  );
}
