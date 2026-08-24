import type { ClearanceReport, Project, WorkspaceOverview } from "./types";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const organizationHeaders = { "x-organization-id": "demo-org" };

async function request(path: string): Promise<Response> {
  return fetch(`${apiUrl}${path}`, {
    headers: organizationHeaders,
    cache: "no-store",
  });
}

export async function fetchProjects(): Promise<Project[]> {
  const response = await request("/v1/projects");
  if (!response.ok) {
    throw new Error(`Unable to load projects (${response.status})`);
  }
  return response.json() as Promise<Project[]>;
}

export async function fetchProject(projectId: string): Promise<Project | null> {
  const response = await request(`/v1/projects/${encodeURIComponent(projectId)}`);
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Unable to load project (${response.status})`);
  }
  return response.json() as Promise<Project>;
}

export async function fetchReports(projectId: string): Promise<ClearanceReport[]> {
  const response = await request(`/v1/projects/${encodeURIComponent(projectId)}/reports`);
  if (!response.ok) {
    throw new Error(`Unable to load reports (${response.status})`);
  }
  return response.json() as Promise<ClearanceReport[]>;
}

export async function fetchWorkspaceOverview(): Promise<WorkspaceOverview> {
  const response = await request("/v1/workspace/overview");
  if (!response.ok) {
    throw new Error(`Unable to load workspace overview (${response.status})`);
  }
  return response.json() as Promise<WorkspaceOverview>;
}
