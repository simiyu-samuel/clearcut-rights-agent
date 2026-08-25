import Link from "next/link";
import { WorkspaceShell } from "@/components/workspace-shell";
import { ActivityViewer } from "./activity-viewer";

export default function ActivityPage() {
  return <WorkspaceShell active="activity" breadcrumbs={<><Link href="/">Projects</Link><span>/</span><strong>Activity</strong></>}><section className="hero"><div><div className="eyebrow">Workspace accountability</div><h1>Activity and notifications.</h1><p>See what changed, who changed it, and which review actions need a response.</p></div></section><ActivityViewer /></WorkspaceShell>;
}
