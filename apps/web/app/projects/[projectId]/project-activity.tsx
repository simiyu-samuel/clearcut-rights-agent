"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useEffect, useState } from "react";

type Activity = { id: string; action: string; actor_id: string; actor_type: string; resource_type: string; resource_id: string; created_at: string; metadata_json: string | null };

function humanize(value: string): string {
  return value.replace(/[._-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function eventKind(action: string): "upload" | "analysis" | "research" | "review" | "workspace" {
  const value = action.toLowerCase();
  if (value.includes("upload") || value.includes("document") || value.includes("media")) return "upload";
  if (value.includes("analysis") || value.includes("analy")) return "analysis";
  if (value.includes("research") || value.includes("source")) return "research";
  if (value.includes("approval") || value.includes("review") || value.includes("clearance") || value.includes("escalat")) return "review";
  return "workspace";
}

function eventMessage(action: string, resourceType: string): string {
  const value = action.toLowerCase();
  if (value.includes("upload")) return "uploaded source material";
  if (value.includes("analysis") || value.includes("analy")) return "completed AI analysis";
  if (value.includes("research")) return "completed rights research";
  if (value.includes("approval") || value.includes("clearance")) return "recorded a clearance decision";
  return `updated ${humanize(resourceType)}`;
}

export function ProjectActivity({ projectId }: { projectId: string }) {
  const auth = useAuth();
  const [items, setItems] = useState<Activity[]>([]);
  const [message, setMessage] = useState("Loading project activity…");
  useEffect(() => {
    void fetch(`/v1/projects/${projectId}/activity`, { cache: "no-store" })
      .then(async (response) => { if (!response.ok) throw new Error("Project activity is unavailable."); setItems(await response.json() as Activity[]); setMessage(""); })
      .catch((error) => setMessage(error instanceof Error ? error.message : "Project activity is unavailable."));
  }, [projectId]);

  return <section className="panel project-activity-panel"><div className="panel-header"><div><h2>Project activity</h2><p className="panel-subtitle">A transparent record of changes for this production</p></div><span>{items.length} events</span></div>{message ? <p className="panel-message">{message}</p> : items.length ? <div className="activity-timeline project-activity-timeline"><div className="activity-date-label">Recent activity</div>{items.map((item) => { const kind = eventKind(item.action); const actor = item.actor_id === auth.user?.actorId ? auth.user.displayName : item.actor_type === "system" ? "ClearCut" : "Workspace member"; return <article className={`activity-event ${kind}`} key={item.id}><div className="activity-event-trigger"><span className="activity-event-avatar">{kind === "upload" ? "↑" : kind === "analysis" ? "✦" : kind === "research" ? "⌕" : kind === "review" ? "✓" : "•"}</span><span className="activity-event-content"><span className="activity-event-topline"><span><strong>{actor}</strong> <span>{eventMessage(item.action, item.resource_type)}</span></span><time dateTime={item.created_at}>{new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.created_at))}</time></span><span className="activity-event-subline">{humanize(item.resource_type)}<span className={`activity-kind-tag ${kind}`}>{humanize(kind)}</span></span></span></div></article>; })}</div> : <p className="panel-message">No project activity has been recorded yet.</p>}</section>;
}
