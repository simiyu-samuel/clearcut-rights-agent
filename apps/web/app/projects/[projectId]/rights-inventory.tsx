"use client";

import { useEffect, useMemo, useState } from "react";

type RightsInventoryProps = { projectId: string };
type Asset = {
  id: string;
  canonical_name: string;
  category: string;
  context: string;
  scene_reference: string | null;
  risk_status: string;
  extraction_confidence: number;
};
type Card = {
  asset_id: string;
  research_run_id: string;
  status: string;
  risk_score: number;
  confidence_score: number;
  evidence_count: number;
  summary: string;
  recommendation: string;
  reason_codes: string[];
  needs_human_review: boolean;
};
type Source = { id: string; title: string; url: string; excerpt: string; source_quality: string };

function label(value: string) {
  return value.replaceAll("_", " ");
}

export function RightsInventory({ projectId }: RightsInventoryProps) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [status, setStatus] = useState("all");
  const [selected, setSelected] = useState<Asset | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const headers = { "x-organization-id": "demo-org" };
    void Promise.all([
      fetch(`${apiUrl}/v1/projects/${projectId}/assets`, { headers }),
      fetch(`${apiUrl}/v1/projects/${projectId}/clearance-cards`, { headers }),
    ])
      .then(async ([assetsResponse, cardsResponse]) => {
        if (!assetsResponse.ok || !cardsResponse.ok) throw new Error("Unable to load rights inventory.");
        setAssets(await assetsResponse.json());
        setCards(await cardsResponse.json());
      })
      .catch((error) => setMessage(error instanceof Error ? error.message : "Unable to load rights inventory."))
      .finally(() => setLoading(false));
  }, [projectId]);

  const latestCards = useMemo(() => {
    const result = new Map<string, Card>();
    for (const card of cards) if (!result.has(card.asset_id)) result.set(card.asset_id, card);
    return result;
  }, [cards]);
  const categories = [...new Set(assets.map((asset) => asset.category))].sort();
  const filteredAssets = assets.filter((asset) => {
    const card = latestCards.get(asset.id);
    const haystack = `${asset.canonical_name} ${asset.context} ${asset.category}`.toLowerCase();
    const matchesQuery = !query.trim() || haystack.includes(query.trim().toLowerCase());
    const matchesCategory = category === "all" || asset.category === category;
    const currentStatus = card?.status ?? "research_needed";
    const matchesStatus = status === "all" || currentStatus === status;
    return matchesQuery && matchesCategory && matchesStatus;
  });
  const selectedCard = selected ? latestCards.get(selected.id) : undefined;

  useEffect(() => {
    if (!selectedCard) {
      setSources([]);
      return;
    }
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    void fetch(`${apiUrl}/v1/research-runs/${selectedCard.research_run_id}/sources`, { headers: { "x-organization-id": "demo-org" } })
      .then((response) => (response.ok ? response.json() : []))
      .then(setSources)
      .catch(() => setSources([]));
  }, [selectedCard]);

  return (
    <>
      <section className="panel inventory-panel">
        <div className="panel-header"><div><h2>Rights inventory</h2><p className="panel-subtitle">Every potential rights-bearing asset extracted from the project</p></div><span>{loading ? "Loading" : `${filteredAssets.length} of ${assets.length}`}</span></div>
        <div className="inventory-toolbar"><input aria-label="Search rights inventory" onChange={(event) => setQuery(event.target.value)} placeholder="Search assets or context" value={query} /><select aria-label="Filter by category" onChange={(event) => setCategory(event.target.value)} value={category}><option value="all">All categories</option>{categories.map((value) => <option key={value} value={value}>{label(value)}</option>)}</select><select aria-label="Filter by status" onChange={(event) => setStatus(event.target.value)} value={status}><option value="all">All statuses</option><option value="research_needed">Research needed</option><option value="pending_review">Pending review</option><option value="approved">Approved</option><option value="needs_more_research">Needs more research</option><option value="escalated">Escalated</option></select></div>
        {message ? <div className="review-message" role="status">{message}</div> : null}
        {!loading && !message && filteredAssets.length === 0 ? <div className="review-empty">No assets match these filters.</div> : null}
        {filteredAssets.length > 0 ? <div className="inventory-table-wrap"><table className="inventory-table"><thead><tr><th>Asset</th><th>Category</th><th>Risk</th><th>Review status</th><th>Evidence</th><th /></tr></thead><tbody>{filteredAssets.map((asset) => { const card = latestCards.get(asset.id); return <tr key={asset.id}><td><strong>{asset.canonical_name}</strong><small>{asset.scene_reference ? `Scene ${asset.scene_reference}` : "Source context available"}</small></td><td>{label(asset.category)}</td><td><span className={`table-risk ${asset.risk_status}`}>{label(asset.risk_status)}</span></td><td><span className={`table-status ${card?.status ?? "research_needed"}`}>{label(card?.status ?? "research_needed")}</span></td><td>{card ? `${card.evidence_count} sources` : "—"}</td><td><button className="table-action" onClick={() => setSelected(asset)} type="button">Inspect</button></td></tr>; })}</tbody></table></div> : null}
      </section>
      {selected ? <div className="drawer-layer" onClick={() => setSelected(null)}><aside aria-label="Asset details" className="asset-drawer" onClick={(event) => event.stopPropagation()}><div className="drawer-header"><div><span className="eyebrow">{label(selected.category)}</span><h2>{selected.canonical_name}</h2></div><button aria-label="Close asset details" className="icon-button" onClick={() => setSelected(null)} type="button">×</button></div><div className="drawer-section"><span className="drawer-label">Source context</span><p>{selected.context}</p><small>{selected.scene_reference ? `Scene ${selected.scene_reference}` : "Scene reference not available"} · {Math.round(selected.extraction_confidence * 100)}% extraction confidence</small></div><div className="drawer-section"><span className="drawer-label">Current risk</span><div className="drawer-status-row"><span className={`table-risk ${selected.risk_status}`}>{label(selected.risk_status)}</span>{selectedCard ? <span className={`table-status ${selectedCard.status}`}>{label(selectedCard.status)}</span> : <span className="table-status research_needed">Research needed</span>}</div></div>{selectedCard ? <><div className="drawer-section"><span className="drawer-label">Clearance assessment</span><div className="drawer-score-grid"><div><strong>{selectedCard.risk_score}</strong><small>risk / 100</small></div><div><strong>{Math.round(selectedCard.confidence_score * 100)}%</strong><small>confidence</small></div><div><strong>{selectedCard.evidence_count}</strong><small>sources</small></div></div><p>{selectedCard.summary}</p><div className="recommendation"><span>Next action</span><p>{selectedCard.recommendation}</p></div></div><div className="drawer-section"><span className="drawer-label">Evidence</span>{sources.length ? <div className="drawer-sources">{sources.map((source) => <a href={source.url} key={source.id} rel="noreferrer" target="_blank"><strong>{source.title}</strong><small>{source.source_quality} · {source.excerpt}</small></a>)}</div> : <p className="drawer-muted">No source records available.</p>}</div><div className="drawer-section"><span className="drawer-label">Reason codes</span><div className="reason-codes">{selectedCard.reason_codes.map((code) => <span key={code}>{label(code)}</span>)}</div></div></> : <div className="drawer-empty">Research this asset to create an evidence-backed clearance card.</div>}<div className="drawer-footer"><button className="secondary-button" onClick={() => { setSelected(null); document.getElementById("review-queue")?.scrollIntoView({ behavior: "smooth" }); }} type="button">Open review queue</button></div></aside></div> : null}
    </>
  );
}
