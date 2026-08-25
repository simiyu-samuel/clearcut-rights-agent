"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { useEffect, useState } from "react";

type ProjectHealthProps = { projectId: string };
type Asset = { id: string; risk_status: string };
type Card = { asset_id: string; status: string; needs_human_review: boolean; evidence_count: number };

export function ProjectHealth({ projectId }: ProjectHealthProps) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const headers = { "x-organization-id": "demo-org" };
    void Promise.all([
      fetch(`${apiUrl}/v1/projects/${projectId}/assets`, { headers }),
      fetch(`${apiUrl}/v1/projects/${projectId}/clearance-cards`, { headers }),
    ])
      .then(async ([assetsResponse, cardsResponse]) => {
        if (!assetsResponse.ok || !cardsResponse.ok) throw new Error("health_unavailable");
        setAssets(await assetsResponse.json());
        setCards(await cardsResponse.json());
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [projectId]);

  const latestCards = new Map<string, Card>();
  for (const card of cards) if (!latestCards.has(card.asset_id)) latestCards.set(card.asset_id, card);
  const attention = assets.filter((asset) => {
    const card = latestCards.get(asset.id);
    return !card || card.needs_human_review || card.status !== "approved";
  }).length;
  const highPriority = assets.filter((asset) => ["high_risk", "blocked"].includes(asset.risk_status)).length;
  const evidenceAssets = [...latestCards.values()].filter((card) => card.evidence_count > 0).length;
  const evidenceCoverage = assets.length ? Math.round((evidenceAssets / assets.length) * 100) : 0;

  return (
    <section className="project-health" aria-label="Project health">
      <div className="health-heading"><div><span className="eyebrow">Operational health</span><h2>Clearance readiness</h2></div><span className="health-caption">{loading ? "Refreshing" : error ? "Unavailable" : "Live project data"}</span></div>
      <div className="health-grid">
        <div className="health-metric"><span>Assets</span><strong>{loading ? "—" : assets.length}</strong><small>extracted from source</small></div>
        <div className={`health-metric ${attention ? "attention" : "good"}`}><span>Need attention</span><strong>{loading ? "—" : attention}</strong><small>{highPriority} high-priority</small></div>
        <div className="health-metric"><span>Reviewed</span><strong>{loading ? "—" : latestCards.size}</strong><small>clearance cards</small></div>
        <div className={`health-metric ${evidenceCoverage >= 80 ? "good" : "attention"}`}><span>Evidence</span><strong>{loading ? "—" : `${evidenceCoverage}%`}</strong><small>coverage of assets</small></div>
      </div>
    </section>
  );
}
