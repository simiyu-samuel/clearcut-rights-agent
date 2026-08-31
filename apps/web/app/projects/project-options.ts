import { authorizedFetch } from "@/lib/api-client";

export type ProjectOptionType = "project_type" | "territory" | "distribution_mode";

export type ProjectOption = {
  id: string;
  option_type: ProjectOptionType;
  label: string;
  is_custom: boolean;
};

export const DEFAULT_PROJECT_OPTIONS: Record<ProjectOptionType, string[]> = {
  project_type: [
    "Feature film",
    "Short film",
    "Documentary",
    "Series",
    "Commercial",
    "Music video",
    "Branded content",
  ],
  territory: [
    "Kenya",
    "United Kingdom",
    "United States",
    "Canada",
    "European Union",
    "Australia",
    "Worldwide",
  ],
  distribution_mode: [
    "Streaming",
    "Theatrical",
    "Broadcast",
    "TVOD",
    "AVOD",
    "Festival",
    "Educational",
    "Social",
  ],
};

export async function loadProjectOptions(): Promise<ProjectOption[]> {
  const response = await authorizedFetch("/v1/organizations/current/project-options", {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Unable to load workspace options.");
  }
  return response.json() as Promise<ProjectOption[]>;
}

export async function createProjectOption(
  optionType: ProjectOptionType,
  label: string,
): Promise<ProjectOption> {
  const response = await authorizedFetch("/v1/organizations/current/project-options", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ option_type: optionType, label }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      payload.detail === "option_already_exists"
        ? "That option already exists in this workspace."
        : payload.detail === "insufficient_workspace_role"
          ? "Only admins and producers can add workspace options."
          : payload.detail ?? "Unable to add workspace option.",
    );
  }
  return payload as ProjectOption;
}

export function labelsFor(
  options: ProjectOption[],
  optionType: ProjectOptionType,
  currentValues: string[] = [],
): string[] {
  const labels = [
    ...options.filter((option) => option.option_type === optionType).map((option) => option.label),
    ...DEFAULT_PROJECT_OPTIONS[optionType],
    ...currentValues,
  ];
  const seen = new Set<string>();
  return labels.filter((label) => {
    const key = label.trim().toLocaleLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

