"use client";

import { useEffect, useMemo, useState } from "react";

type ResearchPanelProps = { projectId: string };

type Asset = {
  id: string;
  canonical_name: string;
  category: string;
  context: string;
  risk_status: string;
};

type ResearchTask = {
  id: string;
  angle: string;
  title: string;
  status: string;
  source_count: number;
  quality_tier: string;
  gap_codes: string[];
  error_code: string | null;
};

type ResearchSession = {
  id: string;
  asset_id: string;
  status: string;
  total_tasks: number;
  completed_tasks: number;
  objective: string;
  tasks: ResearchTask[];
};

const headers = { "x-organization-id": "demo-org" };

function statusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

function qualityLabel(quality: string): string {
  return { strong: "Strong evidence", moderate: "Search lead", demo: "Demo evidence", none: "No evidence" }[quality] ?? "Unrated";
}

export function ResearchPanel({ projectId }: ResearchPanelProps) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [sessions, setSessions] = useState<ResearchSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [busyAsset, setBusyAsset] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  async function load() {
    try {
      const [assetsResponse, sessionsResponse] = await Promise.all([
        fetch(`${apiUrl}/v1/projects/${projectId}/assets`, { headers, cache: "no-store" }),
        fetch(`${apiUrl}/v1/projects/${projectId}/research-sessions`, { headers, cache: "no-store" }),
      ]);
      if (!assetsResponse.ok || !sessionsResponse.ok) throw new Error("Research planning is not available yet.");
      setAssets(await assetsResponse.json() as Asset[]);
      setSessions(await sessionsResponse.json() as ResearchSession[]);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load research sessions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [projectId]);

  const latestByAsset = useMemo(() => {
    const map = new Map<string, ResearchSession>();
    for (const session of sessions) if (!map.has(session.asset_id)) map.set(session.asset_id, session);
    return map;
  }, [sessions]);

  async function waitForSession(sessionId: string) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 1200));
      const response = await fetch(`${apiUrl}/v1/research-sessions/${sessionId}`, { headers, cache: "no-store" });
      if (!response.ok) throw new Error("Unable to read the research session.");
      const session = await response.json() as ResearchSession;
      setSessions((current) => [session, ...current.filter((item) => item.id !== session.id)]);
      if (["completed", "partial", "failed"].includes(session.status)) return;
    }
    throw new Error("Research is taking longer than expected. Refresh this project shortly.");
  }

  async function startSession(asset: Asset) {
    setBusyAsset(asset.id);
    setMessage("");
    try {
      const response = await fetch(`${apiUrl}/v1/assets/${asset.id}/research-sessions`, {
        method: "POST",
        headers: { ...headers, "content-type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Unable to start the research session.");
      }
      const session = await response.json() as ResearchSession;
      setSessions((current) => [session, ...current.filter((item) => item.id !== session.id)]);
      await waitForSession(session.id);
      window.dispatchEvent(new Event("clearcut:research-updated"));
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to start the research session.");
    } finally {
      setBusyAsset(null);
    }
  }

  async function rerunSession(session: ResearchSession) {
    setBusyAsset(session.asset_id);
    setMessage("");
    try {
      const response = await fetch(`${apiUrl}/v1/research-sessions/${session.id}/retry`, {
        method: "POST",
        headers,
      });
      if (!response.ok) throw new Error("Unable to start a new research session.");
      const nextSession = await response.json() as ResearchSession;
      setSessions((current) => [nextSession, ...current]);
      await waitForSession(nextSession.id);
      window.dispatchEvent(new Event("clearcut:research-updated"));
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to re-run research.");
    } finally {
      setBusyAsset(null);
    }
  }

  return (
    <section className="research-panel panel" id="research-plan">
      <div className="panel-header research-panel-header">
        <div>
          <h2>Agent research plan</h2>
          <p className="panel-subtitle">Four rights questions, visible evidence, and explicit gaps for every asset</p>
        </div>
        <span>{loading ? "Loading" : `${sessions.length} session${sessions.length === 1 ? "" : "s"}`}</span>
      </div>
      {message ? <div className="review-message" role="status">{message}</div> : null}
      {!loading && !message && assets.length === 0 ? <div className="review-empty">Analyze a screenplay to create a rights research plan.</div> : null}
      {!loading && !message && assets.length > 0 ? (
        <div className="research-session-list">
          {assets.map((asset) => {
            const session = latestByAsset.get(asset.id);
            const busy = busyAsset === asset.id;
            const progress = session ? Math.round((session.completed_tasks / Math.max(session.total_tasks, 1)) * 100) : 0;
            return (
              <article className="research-session" key={asset.id}>
                <div className="research-session-summary">
                  <div className="research-asset-mark">{asset.category.slice(0, 1).toUpperCase()}</div>
                  <div className="research-session-title"><strong>{asset.canonical_name}</strong><span>{asset.category} · {asset.risk_status.replaceAll("_", " ")}</span><p>{asset.context}</p></div>
                  <div className="research-session-action">
                    {session ? <span className={`research-status ${session.status}`}>{statusLabel(session.status)}</span> : <span className="research-status planned">Not started</span>}
                    {!session ? <button className="secondary-button" disabled={busy} onClick={() => void startSession(asset)} type="button">{busy ? "Planning…" : "Start research"}</button> : null}
                    {session && ["completed", "partial", "failed"].includes(session.status) ? <button className="table-action" disabled={busy} onClick={() => void rerunSession(session)} type="button">{busy ? "Re-running…" : "Re-run session"}</button> : null}
                  </div>
                </div>
                {session ? (
                  <div className="research-session-body">
                    <div className="research-progress-row"><span>Research progress</span><strong>{session.completed_tasks}/{session.total_tasks} angles · {progress}%</strong></div>
                    <div className="research-progress-track"><span style={{ width: `${progress}%` }} /></div>
                    <div className="research-task-grid">
                      {session.tasks.map((task) => (
                        <div className="research-task" key={task.id}>
                          <div className="research-task-head"><strong>{task.title}</strong><span className={`task-status ${task.status}`}>{statusLabel(task.status)}</span></div>
                          <div className="research-task-meta"><span>{task.source_count} source{task.source_count === 1 ? "" : "s"}</span><span className={`quality-tier ${task.quality_tier}`}>{qualityLabel(task.quality_tier)}</span></div>
                          {task.gap_codes.length > 0 ? <div className="research-gaps">{task.gap_codes.map((gap) => <span key={gap}>{statusLabel(gap)}</span>)}</div> : <small className="research-clear">No gaps detected in this angle</small>}
                          {task.error_code ? <small className="research-error">{task.error_code}</small> : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : <div className="research-session-empty">The agent will search owner, licensing, territory, and conflict angles before generating a clearance card.</div>}
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
