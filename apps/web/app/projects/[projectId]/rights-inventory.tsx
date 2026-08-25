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
  priority: string;
  owner_id: string | null;
  due_at: string | null;
  next_action: string | null;
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
type Member = { actor_id: string; display_name: string; role: string };
type Comment = { id: string; author_id: string; body: string; mention_ids: string[]; created_at: string };
type Playbook = { category: string; rights_questions: string[]; required_evidence: string[]; recommended_actions: string[]; escalation_signals: string[] };
type Recheck = { id: string; cadence_days: number; next_run_at: string; active: boolean };

const headers = { "x-organization-id": "demo-org" };

function label(value: string) {
  return value.replaceAll("_", " ");
}

function dateLabel(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown date" : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function RightsInventory({ projectId }: RightsInventoryProps) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [playbook, setPlaybook] = useState<Playbook | null>(null);
  const [recheck, setRecheck] = useState<Recheck | null>(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [status, setStatus] = useState("all");
  const [selected, setSelected] = useState<Asset | null>(null);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [message, setMessage] = useState("");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  async function loadInventory() {
    setLoading(true);
    try {
      const [assetsResponse, cardsResponse, membersResponse] = await Promise.all([
        fetch(`${apiUrl}/v1/projects/${projectId}/assets`, { headers, cache: "no-store" }),
        fetch(`${apiUrl}/v1/projects/${projectId}/clearance-cards`, { headers, cache: "no-store" }),
        fetch(`${apiUrl}/v1/organizations/current/members`, { headers, cache: "no-store" }),
      ]);
      if (!assetsResponse.ok || !cardsResponse.ok || !membersResponse.ok) throw new Error("Unable to load rights inventory.");
      const nextAssets = await assetsResponse.json() as Asset[];
      setAssets(nextAssets);
      setCards(await cardsResponse.json() as Card[]);
      setMembers(await membersResponse.json() as Member[]);
      if (selected) setSelected(nextAssets.find((asset) => asset.id === selected.id) ?? null);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load rights inventory.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadInventory();
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
    if (!selected) {
      setSources([]);
      setComments([]);
      setPlaybook(null);
      setRecheck(null);
      return;
    }
    void Promise.all([
      selectedCard ? fetch(`${apiUrl}/v1/research-runs/${selectedCard.research_run_id}/sources`, { headers }) : Promise.resolve(null),
      fetch(`${apiUrl}/v1/assets/${selected.id}/comments`, { headers }),
      fetch(`${apiUrl}/v1/assets/${selected.id}/playbook`, { headers }),
      fetch(`${apiUrl}/v1/assets/${selected.id}/research-recheck`, { headers }),
    ]).then(async ([sourcesResponse, commentsResponse, playbookResponse, recheckResponse]) => {
      setSources(sourcesResponse?.ok ? await sourcesResponse.json() as Source[] : []);
      setComments(commentsResponse.ok ? await commentsResponse.json() as Comment[] : []);
      setPlaybook(playbookResponse.ok ? await playbookResponse.json() as Playbook : null);
      setRecheck(recheckResponse.ok ? await recheckResponse.json() as Recheck : null);
    }).catch(() => {
      setSources([]);
      setComments([]);
      setPlaybook(null);
      setRecheck(null);
    });
  }, [selected, selectedCard, apiUrl]);

  async function saveAsset() {
    if (!selected) return;
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`${apiUrl}/v1/assets/${selected.id}`, {
        method: "PATCH",
        headers: { ...headers, "content-type": "application/json", "x-actor-id": "demo-producer" },
        body: JSON.stringify({ priority: selected.priority, owner_id: selected.owner_id || null, due_at: selected.due_at || null, next_action: selected.next_action || null }),
      });
      if (!response.ok) throw new Error("Unable to save asset accountability.");
      const updated = await response.json() as Asset;
      setAssets((current) => current.map((asset) => asset.id === updated.id ? updated : asset));
      setSelected(updated);
      setMessage("Asset accountability saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save asset accountability.");
    } finally {
      setBusy(false);
    }
  }

  async function addComment() {
    if (!selected || !comment.trim()) return;
    setBusy(true);
    try {
      const response = await fetch(`${apiUrl}/v1/assets/${selected.id}/comments`, {
        method: "POST",
        headers: { ...headers, "content-type": "application/json", "x-actor-id": "demo-producer" },
        body: JSON.stringify({ body: comment.trim(), mention_ids: [] }),
      });
      if (!response.ok) throw new Error("Unable to add the comment.");
      const created = await response.json() as Comment;
      setComments((current) => [...current, created]);
      setComment("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to add the comment.");
    } finally {
      setBusy(false);
    }
  }

  async function scheduleRecheck() {
    if (!selected) return;
    setScheduling(true);
    try {
      const response = await fetch(`${apiUrl}/v1/assets/${selected.id}/research-recheck`, {
        method: "POST",
        headers: { ...headers, "content-type": "application/json", "x-actor-id": "demo-producer" },
        body: JSON.stringify({ cadence_days: recheck?.cadence_days ?? 30 }),
      });
      if (!response.ok) throw new Error("Unable to schedule the evidence recheck.");
      setRecheck(await response.json() as Recheck);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to schedule the evidence recheck.");
    } finally {
      setScheduling(false);
    }
  }

  return (
    <>
      <section className="panel inventory-panel">
        <div className="panel-header"><div><h2>Rights inventory</h2><p className="panel-subtitle">Every potential rights-bearing asset extracted from the project</p></div><span>{loading ? "Loading" : `${filteredAssets.length} of ${assets.length}`}</span></div>
        <div className="inventory-toolbar"><input aria-label="Search rights inventory" onChange={(event) => setQuery(event.target.value)} placeholder="Search assets or context" value={query} /><select aria-label="Filter by category" onChange={(event) => setCategory(event.target.value)} value={category}><option value="all">All categories</option>{categories.map((value) => <option key={value} value={value}>{label(value)}</option>)}</select><select aria-label="Filter by status" onChange={(event) => setStatus(event.target.value)} value={status}><option value="all">All statuses</option><option value="research_needed">Research needed</option><option value="pending_review">Pending review</option><option value="approved">Approved</option><option value="needs_more_research">Needs more research</option><option value="escalated">Escalated</option></select></div>
        {message ? <div className="review-message" role="status">{message}</div> : null}
        {!loading && !message && filteredAssets.length === 0 ? <div className="review-empty">No assets match these filters.</div> : null}
        {filteredAssets.length > 0 ? <div className="inventory-table-wrap"><table className="inventory-table"><thead><tr><th>Asset</th><th>Category</th><th>Risk</th><th>Review status</th><th>Owner</th><th>Evidence</th><th /></tr></thead><tbody>{filteredAssets.map((asset) => { const card = latestCards.get(asset.id); const owner = members.find((member) => member.actor_id === asset.owner_id); return <tr key={asset.id}><td><strong>{asset.canonical_name}</strong><small>{asset.scene_reference ? `Scene ${asset.scene_reference}` : "Source context available"}</small></td><td>{label(asset.category)}</td><td><span className={`table-risk ${asset.risk_status}`}>{label(asset.risk_status)}</span></td><td><span className={`table-status ${card?.status ?? "research_needed"}`}>{label(card?.status ?? "research_needed")}</span></td><td>{owner?.display_name ?? "Unassigned"}</td><td>{card ? `${card.evidence_count} sources` : "—"}</td><td><button className="table-action" onClick={() => { setSelected(asset); setMessage(""); }} type="button">Inspect</button></td></tr>; })}</tbody></table></div> : null}
      </section>
      {selected ? <div className="drawer-layer" onClick={() => setSelected(null)}><aside aria-label="Asset details" className="asset-drawer" onClick={(event) => event.stopPropagation()}><div className="drawer-header"><div><span className="eyebrow">{label(selected.category)}</span><h2>{selected.canonical_name}</h2></div><button aria-label="Close asset details" className="icon-button" onClick={() => setSelected(null)} type="button">×</button></div>
        <div className="drawer-section"><span className="drawer-label">Source context</span><p>{selected.context}</p><small>{selected.scene_reference ? `Scene ${selected.scene_reference}` : "Scene reference not available"} · {Math.round(selected.extraction_confidence * 100)}% extraction confidence</small></div>
        <div className="drawer-section"><span className="drawer-label">Accountability</span><div className="asset-edit-grid"><label>Priority<select value={selected.priority} onChange={(event) => setSelected({ ...selected, priority: event.target.value })}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></label><label>Owner<select value={selected.owner_id ?? ""} onChange={(event) => setSelected({ ...selected, owner_id: event.target.value || null })}><option value="">Unassigned</option>{members.map((member) => <option key={member.actor_id} value={member.actor_id}>{member.display_name}</option>)}</select></label><label>Due date<input type="date" value={selected.due_at ? selected.due_at.slice(0, 10) : ""} onChange={(event) => setSelected({ ...selected, due_at: event.target.value ? `${event.target.value}T23:59:59Z` : null })} /></label><label>Next action<input value={selected.next_action ?? ""} onChange={(event) => setSelected({ ...selected, next_action: event.target.value })} placeholder="What happens next?" /></label></div><button className="secondary-button drawer-save" disabled={busy} onClick={() => void saveAsset()} type="button">{busy ? "Saving…" : "Save accountability"}</button></div>
        <div className="drawer-section"><span className="drawer-label">Current risk</span><div className="drawer-status-row"><span className={`table-risk ${selected.risk_status}`}>{label(selected.risk_status)}</span>{selectedCard ? <span className={`table-status ${selectedCard.status}`}>{label(selectedCard.status)}</span> : <span className="table-status research_needed">Research needed</span>}</div></div>
        {selectedCard ? <><div className="drawer-section"><span className="drawer-label">Clearance assessment</span><div className="drawer-score-grid"><div><strong>{selectedCard.risk_score}</strong><small>risk / 100</small></div><div><strong>{Math.round(selectedCard.confidence_score * 100)}%</strong><small>confidence</small></div><div><strong>{selectedCard.evidence_count}</strong><small>sources</small></div></div><p>{selectedCard.summary}</p><div className="recommendation"><span>Next action</span><p>{selectedCard.recommendation}</p></div></div><div className="drawer-section"><span className="drawer-label">Evidence</span>{sources.length ? <div className="drawer-sources">{sources.map((source) => <a href={source.url} key={source.id} rel="noreferrer" target="_blank"><strong>{source.title}</strong><small>{source.source_quality} · {source.excerpt}</small></a>)}</div> : <p className="drawer-muted">No source records available.</p>}</div><div className="drawer-section"><span className="drawer-label">Reason codes</span><div className="reason-codes">{selectedCard.reason_codes.map((code) => <span key={code}>{label(code)}</span>)}</div></div></> : <div className="drawer-empty">Research this asset to create an evidence-backed clearance card.</div>}
        {playbook ? <div className="drawer-section"><span className="drawer-label">Rights playbook</span><details className="playbook-details" open><summary>Category-specific clearance checklist</summary><div className="playbook-block"><strong>Required evidence</strong>{playbook.required_evidence.map((item) => <span key={item}>• {item}</span>)}</div><div className="playbook-block"><strong>Escalation signals</strong>{playbook.escalation_signals.map((item) => <span key={item}>• {item}</span>)}</div></details></div> : null}
        <div className="drawer-section"><div className="drawer-label-row"><span className="drawer-label">Evidence recheck</span>{recheck ? <span className="schedule-active">Every {recheck.cadence_days} days</span> : null}</div><p className="drawer-muted">{recheck ? `Next scheduled check ${dateLabel(recheck.next_run_at)}.` : "Keep rights evidence fresh before delivery."}</p><button className="secondary-button" disabled={scheduling} onClick={() => void scheduleRecheck()} type="button">{scheduling ? "Scheduling…" : recheck ? "Update recheck schedule" : "Schedule 30-day recheck"}</button></div>
        <div className="drawer-section"><span className="drawer-label">Team comments</span><div className="comment-list">{comments.map((item) => <div className="comment-row" key={item.id}><strong>{item.author_id}</strong><small>{dateLabel(item.created_at)}</small><p>{item.body}</p></div>)}{!comments.length ? <p className="drawer-muted">No internal comments yet.</p> : null}</div><div className="comment-compose"><textarea aria-label="Add internal comment" onChange={(event) => setComment(event.target.value)} placeholder="Add an internal note or next step…" value={comment} /><button className="secondary-button" disabled={busy || !comment.trim()} onClick={() => void addComment()} type="button">Add comment</button></div></div>
        <div className="drawer-footer"><button className="secondary-button" onClick={() => { setSelected(null); document.getElementById("review-queue")?.scrollIntoView({ behavior: "smooth" }); }} type="button">Open review queue</button></div>
      </aside></div> : null}
    </>
  );
}
