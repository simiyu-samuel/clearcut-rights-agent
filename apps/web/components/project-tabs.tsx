"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";

const tabs = [
  ["Overview", ""],
  ["Source", "/source"],
  ["Inventory", "/inventory"],
  ["Research", "/research"],
  ["Review", "/review"],
  ["Requests", "/requests"],
  ["Reports", "/reports"],
  ["Activity", "/activity"],
  ["Settings", "/settings"],
] as const;

export function ProjectTabs({ projectId }: { projectId: string }) {
  const pathname = usePathname();
  return <nav className="project-tabs" aria-label="Project workspace sections">{tabs.map(([label, suffix]) => { const href = `/projects/${projectId}${suffix}`; const active = suffix ? pathname === href || pathname.startsWith(`${href}/`) : pathname === `/projects/${projectId}`; return <Link className={`project-tab ${active ? "active" : ""}`} href={href as Route} key={href}>{label}</Link>; })}</nav>;
}
