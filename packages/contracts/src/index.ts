export type ProjectStatus = "draft" | "active" | "review" | "complete" | "archived";

export type CreateProjectRequest = {
  title: string;
  project_type: string;
  territories?: string[];
  distribution_modes?: string[];
  target_release_at?: string | null;
};

export type ProjectResponse = CreateProjectRequest & {
  id: string;
  organization_id: string;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
};

export type JobStatus = "queued" | "running" | "awaiting_review" | "completed" | "failed";

export type JobResponse = {
  id: string;
  project_id: string;
  job_type: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
};
