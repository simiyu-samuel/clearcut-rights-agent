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
  risk_status: "high_risk" | "needs_review" | "likely_clear" | "blocked" | "insufficient_evidence" | "approved_for_delivery";
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

export type ClearanceCardResponse = {
  id: string;
  organization_id: string;
  asset_id: string;
  research_run_id: string;
  generated_by: string;
  model_name: string | null;
  status: "pending_review" | "approved" | "needs_more_research" | "rejected" | "escalated";
  risk_score: number;
  confidence_score: number;
  summary: string;
  recommendation: string;
  reason_codes: string[];
  evidence_count: number;
  needs_human_review: boolean;
  created_at: string;
  updated_at: string;
};

export type ApprovalDecision =
  | "approve_next_action"
  | "request_more_research"
  | "mark_not_applicable"
  | "reject"
  | "escalate_to_legal";

export type ApprovalResponse = {
  id: string;
  organization_id: string;
  asset_id: string;
  clearance_card_id: string;
  decision: ApprovalDecision;
  note: string | null;
  actor_id: string;
  supersedes_id: string | null;
  created_at: string;
};

export type OutreachDraftResponse = {
  id: string;
  organization_id: string;
  asset_id: string;
  clearance_card_id: string;
  recipient_hint: string;
  subject: string;
  body: string;
  status: "draft" | "approved" | "sent" | "cancelled";
  generated_by: string;
  created_by: string;
  approved_by: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ClearanceReportResponse = {
  id: string;
  organization_id: string;
  project_id: string;
  report_type: string;
  status: "ready" | "failed";
  generated_by: string;
  content_markdown: string;
  created_at: string;
};
