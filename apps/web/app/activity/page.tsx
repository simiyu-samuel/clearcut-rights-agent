import Link from "next/link";
import { WorkspaceShell } from "@/components/workspace-shell";
import { ActivityViewer } from "./activity-viewer";

export default function ActivityPage() {
  return <WorkspaceShell active="activity" breadcrumbs={<><Link href="/">Projects</Link><span>/</span><strong>Activity</strong></>}><ActivityViewer /></WorkspaceShell>;
}
