"use client";

import { useEffect, useMemo, useState } from "react";

type ReviewQueueProps = { projectId: string };

type Asset = {
  id: string;
  canonical_name: string;
  category: string;
  context: string;
  risk_status: string;
};

type ClearanceCard = {
  id: string;
  asset_id: string;
  research_run_id: string;
  status: "pending_review" | "approved" | "needs_more_research" | "rejected" | "escalated";
  risk_score: number;
  confidence_score: number;
  summary: string;
  recommendation: string;
  reason_codes: string[];
  evidence_count: number;
  needs_human_review: boolean;
  generated_by: string;
};

type SourceRecord = {
  id: string;
  title: string;
  url: string;
  excerpt: string;
  source_quality: string;
};

const decisions = [
  { value: "approve_next_action", label: "Approve next action" },
  { value: "request_more_research", label: "Request more research" },
  { value: "escalate_to_legal", label: "Escalate to legal" },
] as const;

export function ReviewQueue({ projectId }: ReviewQueueProps) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [cards, setCards] = useState<ClearanceCard[]>([]);
  const [sourcesByRun, setSourcesByRun] = useState<Record<string, SourceRecord[]>>({});
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [busyCard, setBusyCard] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  async function loadQueue() {
    setLoading(true);
    setMessage("");
    try {
      const headers = { "x-organization-id": "demo-org" };
      const [assetsResponse, cardsResponse] = await Promise.all([
        fetch(`${apiUrl}/v1/projects/${projectId}/assets`, { headers }),
        fetch(`${apiUrl}/v1/projects/${projectId}/clearance-cards`, { headers }),
      ]);
      if (!assetsResponse.ok || !cardsResponse.ok) {
        throw new Error("The review API is not available yet.");
      }
      const nextAssets: Asset[] = await assetsResponse.json();
      const nextCards: ClearanceCard[] = await cardsResponse.json();
      const sourceEntries = await Promise.all(
        nextCards.map(async (card) => {
          const response = await fetch(`${apiUrl}/v1/research-runs/${card.research_run_id}/sources`, { headers });
          return [card.research_run_id, response.ok ? await response.json() : []] as const;
        }),
      );
      setAssets(nextAssets);
      setCards(nextCards);
      setSourcesByRun(Object.fromEntries(sourceEntries));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load the review queue.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadQueue();
  }, [projectId]);

  const latestCards = useMemo(() => {
    const unique = new Map<string, ClearanceCard>();
    for (const card of cards) {
      if (!unique.has(card.asset_id)) unique.set(card.asset_id, card);
    }
    return [...unique.values()];
  }, [cards]);

  async function recordDecision(card: ClearanceCard, decision: (typeof decisions)[number]["value"]) {
    setBusyCard(card.id);
    setMessage("");
    try {
      const response = await fetch(`${apiUrl}/v1/assets/${card.asset_id}/approvals`, {
        method: "POST",
        headers: { "content-type": "application/json", "x-organization-id": "demo-org", "x-actor-id": "demo-producer" },
        body: JSON.stringify({ decision }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Unable to record the decision.");
      }
      await loadQueue();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to record the decision.");
    } finally {
      setBusyCard(null);
    }
  }

  const assetById = new Map(assets.map((asset) => [asset.id, asset]));

  return (
    <section className="review-panel panel">
      <div className="panel-header">
        <div>
          <h2>AI clearance cards</h2>
          <p className="panel-subtitle">Evidence-backed triage awaiting a producer decision</p>
        </div>
        <span>{loading ? "Loading" : `${latestCards.length} cards`}</span>
      </div>
      {message ? <div className="review-message" role="status">{message}</div> : null}
      {!loading && !message && latestCards.length === 0 ? (
        <div className="review-empty">Run research on an extracted asset to create its first clearance card.</div>
      ) : null}
      <div className="clearance-grid">
        {latestCards.map((card) => {
          const asset = assetById.get(card.asset_id);
          return (
            <article className="clearance-card" key={card.id}>
              <div className="clearance-card-head">
                <div>
                  <div className="clearance-kicker">{asset?.category ?? "Asset"}</div>
                  <h3>{asset?.canonical_name ?? "Unnamed asset"}</h3>
                </div>
                <span className={`card-status ${card.status}`}>{card.status.replaceAll("_", " ")}</span>
              </div>
              <div className="clearance-metrics">
                <div><strong>{card.risk_score}</strong><span>risk / 100</span></div>
                <div><strong>{Math.round(card.confidence_score * 100)}%</strong><span>confidence</span></div>
                <div><strong>{card.evidence_count}</strong><span>sources</span></div>
              </div>
              <p className="clearance-summary">{card.summary}</p>
              <div className="recommendation"><span>Recommended next action</span><p>{card.recommendation}</p></div>
              <div className="reason-codes">{card.reason_codes.map((code) => <span key={code}>{code.replaceAll("_", " ")}</span>)}</div>
              <div className="card-evidence">
                <span>Evidence</span>
                {(sourcesByRun[card.research_run_id] ?? []).map((source) => <a href={source.url} key={source.id} rel="noreferrer" target="_blank">{source.title} <small>↗</small></a>)}
                {(sourcesByRun[card.research_run_id] ?? []).length === 0 ? <em>No source records returned.</em> : null}
              </div>
              {card.needs_human_review ? (
                <div className="review-actions">
                  {decisions.map((decision) => (
                    <button className={decision.value === "approve_next_action" ? "primary-button" : "secondary-button"} disabled={busyCard === card.id} key={decision.value} onClick={() => void recordDecision(card, decision.value)} type="button">
                      {busyCard === card.id ? "Saving…" : decision.label}
                    </button>
                  ))}
                </div>
              ) : <div className="review-complete">Decision recorded · {card.generated_by} card</div>}
            </article>
          );
        })}
      </div>
    </section>
  );
}
