"use client";

import Link from "next/link";
import type { Route } from "next";
import { useCallback, useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { authorizedFetch as fetch } from "@/lib/api-client";
import type { Project } from "@/lib/types";

type Asset = { id: string; risk_status: string; canonical_name: string };
type Card = { asset_id: string; status: string; needs_human_review: boolean };
type QueueProject = { project: Project; attention: number; highRisk: number };

export default function WorkspaceReviewPage() {
  const [items, setItems] = useState<QueueProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      const projectsResponse = await fetch("/v1/projects", { cache: "no-store" });
      if (!projectsResponse.ok) throw new Error("Unable to load the workspace review queue.");
      const projects = await projectsResponse.json() as Project[];
      const queue = await Promise.all(projects.map(async (project) => {
        const [assetsResponse, cardsResponse] = await Promise.all([
          fetch(`/v1/projects/${project.id}/assets`, { cache: "no-store" }),
          fetch(`/v1/projects/${project.id}/clearance-cards`, { cache: "no-store" }),
        ]);
        if (!assetsResponse.ok || !cardsResponse.ok) throw new Error("Unable to load review queue details.");
        const assets = await assetsResponse.json() as Asset[];
        const cards = await cardsResponse.json() as Card[];
        const latestCards = new Map<string, Card>();
        for (const card of cards) if (!latestCards.has(card.asset_id)) latestCards.set(card.asset_id, card);
        const attention = assets.filter((asset) => {
          const card = latestCards.get(asset.id);
          return !card || card.needs_human_review || !["approved", "complete"].includes(card.status);
        }).length;
        return { project, attention, highRisk: assets.filter((asset) => ["high_risk", "blocked"].includes(asset.risk_status)).length };
      }));
      setItems(queue.filter((item) => item.attention > 0));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load the review queue.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadQueue(); }, [loadQueue]);

  return (
    <WorkspaceShell active="review" breadcrumbs={<><Link href="/">Projects</Link><span>/</span><strong>Review queue</strong></>}>
      <section className="hero"><div><div className="eyebrow">Workspace review queue</div><h1>Decisions that need a human.</h1><p>Jump into the projects with unresolved rights signals, prioritized by the work that can block delivery.</p></div><button className="secondary-button" disabled={loading} onClick={() => void loadQueue()} type="button">{loading ? "Refreshing…" : "Refresh queue"}</button></section>
      {message ? <div className="dashboard-error" role="alert"><div><strong>Review queue unavailable</strong><p>{message}</p></div><button className="secondary-button" disabled={loading} onClick={() => void loadQueue()} type="button">Retry</button></div> : null}
      {loading ? <div className="project-grid" aria-busy="true" aria-label="Loading review queue">{["one", "two"].map((key) => <div className="project-card skeleton-card" key={key}><span className="skeleton-block skeleton-title" /><span className="skeleton-block skeleton-copy" /><span className="skeleton-block skeleton-copy short" /></div>)}</div> : items.length ? <div className="project-grid">{items.map(({ project, attention, highRisk }) => <Link className="project-card queue-project-card" href={`/projects/${project.id}/review` as Route} key={project.id}><div className="project-card-top"><div><h3>{project.title}</h3><div className="project-type">{project.project_type}</div></div><span className="status-chip review">Needs review</span></div><div className="queue-project-metrics"><div><strong>{attention}</strong><span>open decisions</span></div><div><strong>{highRisk}</strong><span>high-risk assets</span></div></div><div className="queue-project-link">Open project queue →</div></Link>)}</div> : <section className="panel empty-state"><span className="eyebrow">Queue clear</span><h2>No projects need a decision right now.</h2><p>When an asset needs review, escalation, or more evidence, it will appear here with a direct path into the project queue.</p><Link className="secondary-button" href="/">Back to projects</Link></section>}
    </WorkspaceShell>
  );
}
