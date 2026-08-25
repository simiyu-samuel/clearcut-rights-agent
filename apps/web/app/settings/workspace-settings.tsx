"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";

type Member = { id: string; actor_id: string; display_name: string; role: string; status: string };
type ApiKey = { id: string; name: string; key_prefix: string; created_at: string; revoked_at: string | null; secret?: string | null };
type Webhook = { id: string; url: string; event_types: string[]; active: boolean; created_at: string };

const headers = { "x-organization-id": "demo-org", "x-actor-id": "demo-user" };

function label(value: string) {
  return value.replaceAll("_", " ");
}

export function WorkspaceSettings() {
  const { organizationRole } = useAuth();
  const canAdmin = organizationRole === "admin";
  const [members, setMembers] = useState<Member[]>([]);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [name, setName] = useState("");
  const [actorId, setActorId] = useState("");
  const [role, setRole] = useState("viewer");
  const [keyName, setKeyName] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [message, setMessage] = useState("");
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  async function load() {
    const membersResponse = await fetch(`${apiUrl}/v1/organizations/current/members`, { headers, cache: "no-store" });
    if (!membersResponse.ok) {
      throw new Error("Workspace settings are not available yet.");
    }
    setMembers(await membersResponse.json() as Member[]);
    if (!canAdmin) return;
    const [keysResponse, webhooksResponse] = await Promise.all([
      fetch(`${apiUrl}/v1/organizations/current/api-keys`, { headers, cache: "no-store" }),
      fetch(`${apiUrl}/v1/organizations/current/webhooks`, { headers, cache: "no-store" }),
    ]);
    if (!keysResponse.ok || !webhooksResponse.ok) throw new Error("Workspace integrations are not available yet.");
    setKeys(await keysResponse.json() as ApiKey[]);
    setWebhooks(await webhooksResponse.json() as Webhook[]);
  }

  useEffect(() => {
    void load().catch((error) => setMessage(error instanceof Error ? error.message : "Unable to load workspace settings."));
  }, [canAdmin]);

  async function addMember() {
    const response = await fetch(`${apiUrl}/v1/organizations/current/members`, {
      method: "POST",
      headers: { ...headers, "content-type": "application/json" },
      body: JSON.stringify({ actor_id: actorId, display_name: name, role }),
    });
    if (!response.ok) {
      setMessage("Unable to add workspace member.");
      return;
    }
    const created = await response.json() as Member;
    setMembers((current) => [...current, created]);
    setName("");
    setActorId("");
    setMessage("Member added.");
  }

  async function createKey() {
    const response = await fetch(`${apiUrl}/v1/organizations/current/api-keys`, {
      method: "POST",
      headers: { ...headers, "content-type": "application/json" },
      body: JSON.stringify({ name: keyName }),
    });
    if (!response.ok) {
      setMessage("Unable to create API key.");
      return;
    }
    const created = await response.json() as ApiKey;
    setKeys((current) => [created, ...current]);
    setSecret(created.secret ?? "");
    setKeyName("");
    setMessage("API key created. Copy the secret before leaving this page.");
  }

  async function revokeKey(key: ApiKey) {
    const response = await fetch(`${apiUrl}/v1/organizations/current/api-keys/${key.id}/revoke`, { method: "POST", headers });
    if (!response.ok) {
      setMessage("Unable to revoke API key.");
      return;
    }
    const updated = await response.json() as ApiKey;
    setKeys((current) => current.map((item) => item.id === updated.id ? updated : item));
    setMessage(`${key.name} revoked.`);
  }

  async function addWebhook() {
    const response = await fetch(`${apiUrl}/v1/organizations/current/webhooks`, {
      method: "POST",
      headers: { ...headers, "content-type": "application/json" },
      body: JSON.stringify({ url: webhookUrl, event_types: ["approval.recorded", "report.created"] }),
    });
    if (!response.ok) {
      setMessage("Unable to add webhook endpoint.");
      return;
    }
    const created = await response.json() as Webhook;
    setWebhooks((current) => [created, ...current]);
    setWebhookUrl("");
    setMessage("Webhook endpoint added.");
  }

  async function toggleWebhook(webhook: Webhook) {
    const response = await fetch(`${apiUrl}/v1/organizations/current/webhooks/${webhook.id}/toggle`, { method: "POST", headers });
    if (!response.ok) {
      setMessage("Unable to update webhook endpoint.");
      return;
    }
    const updated = await response.json() as Webhook;
    setWebhooks((current) => current.map((item) => item.id === updated.id ? updated : item));
    setMessage(`${webhook.url} ${updated.active ? "resumed" : "paused"}.`);
  }

  return (
    <div className="settings-grid">
      {message ? <div className="review-message" role="status">{message}</div> : null}
      <section className="panel settings-card">
        <div className="panel-header"><div><h2>Workspace members</h2><p className="panel-subtitle">Assign responsibility by production role</p></div><span>{members.length} members</span></div>
        <div className="settings-list">{members.map((member) => <div className="settings-row" key={member.id}><div><strong>{member.display_name}</strong><small>{member.actor_id} · {label(member.role)}</small></div><span className="table-status approved">{member.status}</span></div>)}</div>
        {canAdmin ? <div className="settings-form"><input onChange={(event) => setName(event.target.value)} placeholder="Display name" value={name} /><input onChange={(event) => setActorId(event.target.value)} placeholder="Firebase user ID" value={actorId} /><select onChange={(event) => setRole(event.target.value)} value={role}><option value="viewer">Viewer</option><option value="coordinator">Coordinator</option><option value="producer">Producer</option><option value="legal_reviewer">Legal reviewer</option><option value="post_supervisor">Post supervisor</option></select><button className="secondary-button" disabled={!name || !actorId} onClick={() => void addMember()} type="button">Add member</button></div> : <p className="panel-message">Only workspace admins can change membership or integrations.</p>}
      </section>
      {canAdmin ? <section className="panel settings-card">
        <div className="panel-header"><div><h2>API access</h2><p className="panel-subtitle">Server-side integrations with one-time secret display</p></div></div>
        <div className="settings-list">{keys.map((key) => <div className="settings-row" key={key.id}><div><strong>{key.name}</strong><small>{key.key_prefix} · created {new Date(key.created_at).toLocaleDateString()}</small></div><div className="settings-row-actions"><span className={`table-status ${key.revoked_at ? "rejected" : "approved"}`}>{key.revoked_at ? "Revoked" : "Active"}</span>{!key.revoked_at ? <button className="table-action" onClick={() => void revokeKey(key)} type="button">Revoke</button> : null}</div></div>)}</div>
        <div className="settings-form"><input onChange={(event) => setKeyName(event.target.value)} placeholder="Key name" value={keyName} /><button className="secondary-button" disabled={!keyName} onClick={() => void createKey()} type="button">Create API key</button></div>
        {secret ? <div className="secret-callout"><strong>Copy this secret now</strong><code>{secret}</code><small>It will not be shown again after this screen.</small></div> : null}
      </section> : null}
      {canAdmin ? <section className="panel settings-card">
        <div className="panel-header"><div><h2>Webhooks</h2><p className="panel-subtitle">Notify external systems when rights state changes</p></div><span>{webhooks.length} endpoints</span></div>
        <div className="settings-list">{webhooks.map((webhook) => <div className="settings-row" key={webhook.id}><div><strong>{webhook.url}</strong><small>{webhook.event_types.map(label).join(" · ")}</small></div><div className="settings-row-actions"><span className={`table-status ${webhook.active ? "approved" : "rejected"}`}>{webhook.active ? "Active" : "Paused"}</span><button className="table-action" onClick={() => void toggleWebhook(webhook)} type="button">{webhook.active ? "Pause" : "Resume"}</button></div></div>)}</div>
        <div className="settings-form"><input onChange={(event) => setWebhookUrl(event.target.value)} placeholder="https://example.com/clearcut-hook" value={webhookUrl} /><button className="secondary-button" disabled={!webhookUrl} onClick={() => void addWebhook()} type="button">Add endpoint</button></div>
      </section> : null}
    </div>
  );
}
