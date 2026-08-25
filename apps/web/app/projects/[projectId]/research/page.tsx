import { ProjectWorkspace } from "../project-workspace";

export default async function ProjectResearchPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  return <ProjectWorkspace projectId={projectId} section="research" />;
}
