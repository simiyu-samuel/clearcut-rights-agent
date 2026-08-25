import Link from "next/link";
import { WorkspaceShell } from "@/components/workspace-shell";
import { WorkspaceSettings } from "./workspace-settings";

export default function SettingsPage() {
  return <WorkspaceShell active="settings" breadcrumbs={<><Link href="/">Projects</Link><span>/</span><strong>Settings</strong></>}><section className="hero"><div><div className="eyebrow">Workspace administration</div><h1>Settings and access.</h1><p>Manage the people, roles, and integrations that make rights work accountable.</p></div></section><WorkspaceSettings /></WorkspaceShell>;
}
