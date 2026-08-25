import { notFound } from "next/navigation";

type SharePageProps = { params: Promise<{ shareToken: string }> };
type SharePayload = {
  project: { id: string; title: string; project_type: string; status: string };
  readiness: { status: string; total_assets: number; clear_assets: number; unresolved_assets: number; required_actions: string[] };
  assets: { id: string; canonical_name: string; category: string; risk_status: string }[];
  clearance_cards: { id: string; asset_id: string; status: string; risk_score: number; summary: string; recommendation: string; evidence_count: number }[];
};

export default async function ExternalReviewPage({ params }: SharePageProps) {
  const { shareToken } = await params;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const response = await fetch(apiUrl + "/v1/review-shares/" + encodeURIComponent(shareToken), { cache: "no-store" });
  if (!response.ok) notFound();
  const payload = await response.json() as SharePayload;
  const cards = new Map(payload.clearance_cards.map((card) => [card.asset_id, card]));
  return (
    <main className="external-review">
      <header className="external-review-header"><div className="report-cover-brand"><span className="brand-mark">C</span><div><strong>ClearCut</strong><small>Rights intelligence</small></div></div><span className="readiness-status conditional">Scoped external review</span></header>
      <section className="external-review-hero"><span className="eyebrow">{payload.project.project_type} · External review</span><h1>{payload.project.title}</h1><p>This read-only review link shows the current rights evidence and delivery readiness snapshot. It does not grant legal clearance or editing access.</p></section>
      <section className="external-readiness panel"><div><span className="eyebrow">Delivery gate</span><h2>{payload.readiness.status.replaceAll("_", " ")}</h2><p>{payload.readiness.clear_assets} of {payload.readiness.total_assets} assets currently have an approved card.</p></div><div className="external-readiness-metrics"><strong>{payload.readiness.unresolved_assets}</strong><span>unresolved</span></div></section>
      {payload.readiness.required_actions.length ? <section className="external-actions panel"><h2>Open actions</h2>{payload.readiness.required_actions.map((action) => <p key={action}>→ {action}</p>)}</section> : null}
      <section className="external-assets"><div className="external-section-heading"><span>Rights inventory</span><h2>Evidence-backed review items</h2></div><div className="external-card-grid">{payload.assets.map((asset) => { const card = cards.get(asset.id); return <article className="external-asset panel" key={asset.id}><div className="external-asset-head"><div><span>{asset.category}</span><h3>{asset.canonical_name}</h3></div><span className={"card-status " + (card?.status ?? "pending_review")}>{(card?.status ?? asset.risk_status).replaceAll("_", " ")}</span></div><div className="external-asset-meta"><span>Risk {card?.risk_score ?? "—"}</span><span>{card?.evidence_count ?? 0} sources</span></div><p>{card?.summary ?? "No clearance card has been generated for this asset yet."}</p>{card?.recommendation ? <div className="recommendation"><span>Recommended next action</span><p>{card.recommendation}</p></div> : null}</article>; })}</div></section>
      <footer className="external-review-footer">ClearCut is an AI-assisted rights operations workspace. Human review remains required.</footer>
    </main>
  );
}
