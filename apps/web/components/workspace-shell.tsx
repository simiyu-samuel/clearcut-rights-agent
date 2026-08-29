"use client";

import Link from "next/link";
import type { Route } from "next";
import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

type WorkspaceShellProps = {
  children: ReactNode;
  breadcrumbs: ReactNode;
  active?: "overview" | "projects" | "review" | "research" | "reports" | "activity" | "settings";
  projectId?: string;
};

type IconName = "dashboard" | "folder" | "review" | "research" | "reports" | "activity" | "settings" | "help" | "notifications";

function Icon({ name, filled = false }: { name: IconName; filled?: boolean }) {
  const common = { fill: "none", stroke: "currentColor", strokeLinecap: "round" as const, strokeLinejoin: "round" as const, strokeWidth: 1.8 };
  const paths: Record<IconName, ReactNode> = {
    dashboard: <><rect {...common} height="15" rx="1.5" width="15" x="4.5" y="4.5" /><path {...common} d="M4.5 10h15M10 4.5v15" /></>,
    folder: <><path {...common} d="M3.8 7.2h6l1.8 2h8.6v8.4a2 2 0 0 1-2 2H5.8a2 2 0 0 1-2-2V7.2Z" /><path {...common} d="M3.8 7.2V5.8a2 2 0 0 1 2-2h4l1.8 2h5.6a2 2 0 0 1 2 2v1.4" /></>,
    review: <><rect {...common} height="16" rx="2" width="16" x="4" y="4" /><path {...common} d="m8 12 2.2 2.2L16 8.5M8 8h3" /></>,
    research: <><circle {...common} cx="10.5" cy="10.5" r="5.5" /><path {...common} d="m15 15 4.5 4.5M8.5 10.5h4M10.5 8.5v4" /></>,
    reports: <><path {...common} d="M5 20V10M12 20V4M19 20v-7" /><path {...common} d="M3.5 20.5h17" /></>,
    activity: <><path {...common} d="M4 12h3l2-5 4 10 2-5h4.5" /><circle {...common} cx="12" cy="12" r="8.5" /></>,
    settings: <><circle {...common} cx="12" cy="12" r="3" /><path {...common} d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-1.8 1.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-2.6V20a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1-1.8-1.8.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.6-1H4v-2.6h.2a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1 1.8-1.8.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.6V4h2.6v.2a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1 1.8 1.8-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v2.6h-.2a1.7 1.7 0 0 0-1.6 1Z" /></>,
    help: <><circle {...common} cx="12" cy="12" r="8.5" /><path {...common} d="M9.7 9.2a2.4 2.4 0 1 1 4 1.8c-1.1.8-1.7 1.3-1.7 2.5M12 16.5h.01" /></>,
    notifications: <><path {...common} d="M18 10a6 6 0 0 0-12 0c0 7-3 7-3 8.5h18C21 17 18 17 18 10ZM10 21h4" /></>,
  };
  return <svg aria-hidden="true" className={`shell-icon ${filled ? "filled" : ""}`} viewBox="0 0 24 24">{paths[name]}</svg>;
}

export function WorkspaceShell({ children, breadcrumbs, active, projectId }: WorkspaceShellProps) {
  const pathname = usePathname();
  const auth = useAuth();
  const initials = (auth.user?.displayName ?? "ClearCut")
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const workspaceName = auth.organizationId === "demo-org" ? "Studio Meridian" : auth.organizationId ?? "Workspace";
  const projectReviewActive = Boolean(projectId && pathname.includes(`/projects/${projectId}/review`));
  const navItems: Array<{ key: NonNullable<WorkspaceShellProps["active"]>; label: string; href: Route; icon: IconName }> = [
    { key: "overview", label: "Overview", href: "/" as Route, icon: "dashboard" },
    { key: "projects", label: "Projects", href: "/projects" as Route, icon: "folder" },
    { key: "review", label: "Review queue", href: (projectId ? `/projects/${projectId}/review` : "/review") as Route, icon: "review" },
    { key: "research", label: "Research", href: (projectId ? `/projects/${projectId}/research` : "/research") as Route, icon: "research" },
    { key: "reports", label: "Reports", href: "/reports" as Route, icon: "reports" },
    { key: "activity", label: "Activity", href: "/activity" as Route, icon: "activity" },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><img className="brand-logo" src="/clearcut-logo.png" alt="ClearCut" /><div className="brand-workspace">{workspaceName}</div></div>
        <nav className="nav">
          {navItems.map((item) => {
            const isActive = item.key === "review" ? active === "review" || projectReviewActive : active === item.key;
            return <Link className={`nav-item ${isActive ? "active" : ""}`} href={item.href} key={item.key}><span className="nav-icon"><Icon filled={isActive} name={item.icon} /></span><span>{item.label}</span></Link>;
          })}
        </nav>
        <div className="sidebar-bottom">
          <nav className="nav nav-utility">
            <Link className={`nav-item ${active === "settings" ? "active" : ""}`} href="/settings"><span className="nav-icon"><Icon filled={active === "settings"} name="settings" /></span><span>Settings</span></Link>
            <Link className="nav-item" href="/activity"><span className="nav-icon"><Icon name="help" /></span><span>Help</span></Link>
          </nav>
          <div className="workspace-account">
            <div className="account"><div className="avatar">{initials}</div><div><div className="account-name">{auth.user?.displayName ?? "ClearCut user"}</div><div className="account-role">{auth.organizationRole ?? "Workspace member"}</div></div></div>
            {auth.memberships.length > 1 ? <select aria-label="Select organization" className="workspace-org-select" value={auth.organizationId ?? ""} onChange={(event) => auth.selectOrganization(event.target.value)}>{auth.memberships.map((membership) => <option key={membership.organization_id} value={membership.organization_id}>{membership.organization_id}</option>)}</select> : null}
            <button className="workspace-signout" onClick={() => void auth.signOut()} type="button">Sign out</button>
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar"><div className="breadcrumbs">{breadcrumbs}</div><div className="topbar-search"><Icon name="research" /><input aria-label="Search workspace" placeholder="Search projects, assets, evidence…" /></div><div className="topbar-actions"><div className="env-pill"><span className="env-dot" />{process.env.NEXT_PUBLIC_AUTH_MODE === "identity_platform" ? "Workspace healthy" : "Local demo mode"}</div><Link className="icon-button" aria-label="Open activity and notifications" href="/activity"><Icon name="notifications" /><span className="notification-dot" /></Link><div className="topbar-avatar avatar">{initials}</div></div></header>
        <div className="content">{children}</div>
      </main>
    </div>
  );
}
