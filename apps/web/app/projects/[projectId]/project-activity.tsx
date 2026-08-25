"use client";

import { useEffect, useState } from "react";
import { authorizedFetch as fetch } from "@/lib/api-client";

type Activity = { id: string; action: string; actor_id: string; resource_type: string; resource_id: string; created_at: string; metadata_json: string | null };

export function ProjectActivity({ projectId }: { projectId: string }) {
  const [items, setItems] = useState<Activity[]>([]);
  const [message, setMessage] = useState("Loading project activity…");
  useEffect(() => {
    void fetch(`/v1/projects/${projectId}/activity`, { cache: "no-store" })
      .then(async (response) => { if (!response.ok) throw new Error("Project activity is unavailable."); setItems(await response.json() as Activity[]); setMessage(""); })
      .catch((error) => setMessage(error instanceof Error ? error.message : "Project activity is unavailable."));
  }, [projectId]);
  return <section className="panel project-activity-panel"><div className="panel-header"><div><h2>Project activity</h2><span>Auditable changes for this production</span></div></div>{message ? <p className="panel-message">{message}</p> : items.length ? <div className="timeline">{items.map((item) => <div className="timeline-item" key={item.id}><span className="timeline-dot" /><div><h3>{item.action.replaceAll("_", " ")}</h3><p>{item.actor_id} · {new Date(item.created_at).toLocaleString("en-GB")}</p></div></div>)}</div> : <p className="panel-message">No project activity has been recorded yet.</p>}</section>;
}
