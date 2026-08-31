"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useEffect, useMemo, useState } from "react";

type OperationsPanelProps = { projectId: string };
type Readiness = {
  status: "not_ready" | "conditional" | "ready";
  total_assets: number;
  clear_assets: number;
  unresolved_assets: number;
  blocked_assets: number;
  stale_rechecks: number;
  open_requests: number;
  required_actions: string[];
};
type Asset = { id: string; canonical_name: string };
type Recheck = { id: string; asset_id: string; cadence_days: number; next_run_at: string; active: boolean };
type Member = { actor_id: string; display_name: string; role: string; status: string };
type Activity = { id: string; action: string; actor_id: string; resource_type: string; created_at: string; metadata_json: string | null };

function label(value: string) {
  return value.replaceAll("_", " ");
}

function dateLabel(value: string) {
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function OperationsPanel({ projectId }: OperationsPanelProps) {
  const auth = useAuth();
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [rechecks, setRechecks] = useState<Recheck[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  function actorLabel(actorId: string): string {
    if (actorId === auth.user?.actorId) return auth.user.displayName;
    if (actorId.startsWith("system")) return "ClearCut";
    if (actorId.startsWith("demo-")) return "Studio team";
    return "Workspace member";
  }

  async function load() {
    setLoading(true);
    try {
      const [readinessResponse, assetsResponse, rechecksResponse, membersResponse, activityResponse] = await Promise.all([
        fetch(`${apiUrl}/v1/projects/${projectId}/delivery-readiness`, { cache: "no-store" }),
        fetch(`${apiUrl}/v1/projects/${projectId}/assets`, { cache: "no-store" }),
        fetch(`${apiUrl}/v1/projects/${projectId}/research-rechecks`, { cache: "no-store" }),
        fetch(`${apiUrl}/v1/organizations/current/members`, { cache: "no-store" }),
        fetch(`${apiUrl}/v1/projects/${projectId}/activity`, { cache: "no-store" }),
      ]);
      if (!readinessResponse.ok || !assetsResponse.ok || !rechecksResponse.ok || !membersResponse.ok || !activityResponse.ok) {
        throw new Error("Operations data is not available yet.");
      }
      setReadiness(await readinessResponse.json() as Readiness);
      setAssets(await assetsResponse.json() as Asset[]);
      setRechecks(await rechecksResponse.json() as Recheck[]);
      setMembers(await membersResponse.json() as Member[]);
      setActivity(await activityResponse.json() as Activity[]);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load operations data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    const refresh = () => void load();
    window.addEventListener("clearcut:research-updated", refresh);
    return () => window.removeEventListener("clearcut:research-updated", refresh);
  }, [projectId]);

  const assetNames = useMemo(() => new Map(assets.map((asset) => [asset.id, asset.canonical_name])), [assets]);

  return (
    <section className="operations-panel panel" aria-label="Project operations">
      <div className="panel-header">
        <div><h2>Production operations</h2><p className="panel-subtitle">Delivery readiness, accountability, and evidence maintenance</p></div>
        <button className="table-action" disabled={loading} onClick={() => void load()} type="button">{loading ? "Refreshing…" : "Refresh"}</button>
      </div>
      {message ? <div className="review-message" role="status">{message}</div> : null}
      {readiness ? (
        <>
          <div className="readiness-header">
            <div><span className="eyebrow">Delivery gate</span><h3>{readiness.status === "ready" ? "Ready for delivery review" : readiness.status === "conditional" ? "Conditional readiness" : "Not ready yet"}</h3><p>{readiness.required_actions.length ? "The project still has concrete clearance work to finish." : "No unresolved operational blockers are currently recorded."}</p></div>
            <span className={`readiness-status ${readiness.status}`}>{label(readiness.status)}</span>
          </div>
          <div className="readiness-metrics">
            <div><strong>{readiness.clear_assets}/{readiness.total_assets}</strong><span>assets clear</span></div>
            <div><strong>{readiness.unresolved_assets}</strong><span>unresolved</span></div>
            <div><strong>{readiness.blocked_assets}</strong><span>blocked</span></div>
            <div><strong>{readiness.open_requests}</strong><span>open requests</span></div>
            <div><strong>{readiness.stale_rechecks}</strong><span>stale rechecks</span></div>
          </div>
          {readiness.required_actions.length ? <div className="readiness-actions"><span>Required next actions</span>{readiness.required_actions.map((action) => <div key={action}><b>→</b>{action}</div>)}</div> : null}
        </>
      ) : null}
      <div className="operations-grid">
        <div className="operations-section"><div className="operations-section-heading"><span>Team coverage</span><small>{members.length} members</small></div>{members.map((member) => <div className="member-row" key={member.actor_id}><span className="avatar small">{member.display_name.slice(0, 2).toUpperCase()}</span><div><strong>{member.display_name}</strong><small>{label(member.role)} · {member.status}</small></div></div>)}</div>
        <div className="operations-section"><div className="operations-section-heading"><span>Evidence maintenance</span><small>{rechecks.length} schedules</small></div>{rechecks.length ? rechecks.map((recheck) => <div className="recheck-row" key={recheck.id}><div><strong>{assetNames.get(recheck.asset_id) ?? "Asset"}</strong><small>Every {recheck.cadence_days} days · next {dateLabel(recheck.next_run_at)}</small></div><span className={recheck.active ? "schedule-active" : "schedule-paused"}>{recheck.active ? "Active" : "Paused"}</span></div>) : <p className="operations-empty">No scheduled evidence rechecks. Add one from an asset detail view.</p>}</div>
        <div className="operations-section activity-section"><div className="operations-section-heading"><span>Recent activity</span><small>{activity.length} events</small></div>{activity.slice(0, 6).map((event) => <div className="activity-row" key={event.id}><span className="activity-dot" /><div><strong>{label(event.action)}</strong><small>{actorLabel(event.actor_id)} · {dateLabel(event.created_at)}</small></div></div>)}{!activity.length ? <p className="operations-empty">No activity has been recorded for this project yet.</p> : null}</div>
      </div>
    </section>
  );
}
