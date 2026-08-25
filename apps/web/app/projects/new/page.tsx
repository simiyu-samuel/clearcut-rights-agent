import Link from "next/link";
import { WorkspaceShell } from "@/components/workspace-shell";
import { NewProjectForm } from "./new-project-form";

export default function NewProjectPage() {
  return <WorkspaceShell active="projects" breadcrumbs={<><Link href="/">Projects</Link><span>/</span><strong>New project</strong></>}><section className="project-header"><div><div className="eyebrow">Workspace setup</div><h1>Start a project.</h1><p>Define the production context before uploading creative material.</p></div></section><NewProjectForm /></WorkspaceShell>;
}
