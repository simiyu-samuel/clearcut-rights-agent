import type { DemoAsset, Project } from "./types";

export const demoProjects: Project[] = [
  {
    id: "the-last-signal",
    organization_id: "demo-org",
    title: "The Last Signal",
    project_type: "Feature film",
    territories: ["Kenya", "United Kingdom"],
    distribution_modes: ["Theatrical", "Streaming"],
    target_release_at: "2026-11-18T00:00:00Z",
    status: "review",
    created_at: "2026-08-19T09:30:00Z",
    updated_at: "2026-08-22T08:15:00Z",
  },
  {
    id: "north-star-series",
    organization_id: "demo-org",
    title: "North Star",
    project_type: "Limited series",
    territories: ["East Africa"],
    distribution_modes: ["Streaming"],
    target_release_at: "2027-02-04T00:00:00Z",
    status: "active",
    created_at: "2026-08-11T10:00:00Z",
    updated_at: "2026-08-21T16:42:00Z",
  },
];

export const demoAssets: DemoAsset[] = [
  { number: "01", name: "Song reference: Neon Afterglow", category: "Music", context: "Scene 04 · page 12 · dialogue cue", risk: "high" },
  { number: "02", name: "Harbor Light Café", category: "Brand / logo", context: "Scene 06 · background signage", risk: "medium" },
  { number: "03", name: "Old Railway Station", category: "Location", context: "Scenes 02, 07 · exterior location", risk: "medium" },
  { number: "04", name: "The Blue Hour photograph", category: "Artwork", context: "Scene 09 · wall dressing", risk: "low" },
  { number: "05", name: "National Falcons", category: "Organization", context: "Scene 11 · sports reference", risk: "medium" },
];
