export type ProjectStatus = "draft" | "active" | "review" | "complete" | "archived";

export type Project = {
  id: string;
  organization_id: string;
  title: string;
  project_type: string;
  territories: string[];
  distribution_modes: string[];
  target_release_at: string | null;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
};

export type ClearanceReport = {
  id: string;
  organization_id: string;
  project_id: string;
  report_type: string;
  status: "ready" | "failed";
  generated_by: string;
  content_markdown: string;
  created_at: string;
};

export type AssetRisk = "high" | "medium" | "low";

export type DemoAsset = {
  number: string;
  name: string;
  category: string;
  context: string;
  risk: AssetRisk;
};
