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

export type DocumentResponse = {
  id: string;
  organization_id: string;
  project_id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  status: "uploaded" | "processing" | "analyzed" | "failed";
  created_at: string;
  updated_at: string;
};

export type AssetResponse = {
  id: string;
  organization_id: string;
  project_id: string;
  document_id: string;
  canonical_name: string;
  category: string;
  context: string;
  scene_reference: string | null;
  extraction_confidence: number;
  risk_status: "high_risk" | "needs_review" | "likely_clear" | "blocked" | "insufficient_evidence";
  reason_codes: string[];
  created_at: string;
  updated_at: string;
};

export type ResearchRunResponse = {
  id: string;
  organization_id: string;
  asset_id: string;
  provider: "parallel";
  operation: "search" | "extract";
  objective: string;
  query: string;
  status: "queued" | "running" | "completed" | "partial" | "failed";
  provider_request_id: string | null;
  error_code: string | null;
  created_at: string;
  updated_at: string;
};
