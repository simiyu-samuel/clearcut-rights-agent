"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useEffect, useMemo, useState } from "react";

type Activity = {
  id: string;
  action: string;
  actor_id: string;
  actor_type: string;
  resource_type: string;
  resource_id: string;
  created_at: string;
  metadata_json: string | null;
};

type Notification = { id: string; title: string; body: string; read_at: string | null; created_at: string };
type Project = { id: string; title: string };
type ActivityKind = "upload" | "analysis" | "research" | "review" | "workspace" | "other";

type ActivityCopy = {
  actor: string;
  message: string;
  projectName: string | null;
  kind: ActivityKind;
  kindLabel: string;
  metadata: Record<string, unknown>;
};

function humanize(value: string): string {
  return value
    .replace(/[._-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function parseMetadata(value: string | null): Record<string, unknown> {
  if (!value) return {};
  try {
    const parsed: unknown = JSON.parse(value);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? parsed as Record<string, unknown>
      : {};
  } catch {
    return {};
  }
}

function metadataString(metadata: Record<string, unknown>, key: string): string | null {
  const value = metadata[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : null;
}

function classify(action: string): { kind: ActivityKind; label: string } {
  const value = action.toLowerCase();
  if (value.includes("upload") || value.includes("media") || value.includes("document")) return { kind: "upload", label: "Uploads" };
  if (value.includes("analysis") || value.includes("analy")) return { kind: "analysis", label: "Analysis" };
  if (value.includes("research") || value.includes("source")) return { kind: "research", label: "Research" };
  if (value.includes("approval") || value.includes("review") || value.includes("clearance") || value.includes("escalat")) return { kind: "review", label: "Clearance" };
  if (value.includes("organization") || value.includes("member") || value.includes("invitation")) return { kind: "workspace", label: "Workspace" };
  return { kind: "other", label: "System" };
}

function activityCopy(event: Activity, projects: Project[], actorId: string | undefined, displayName: string): ActivityCopy {
  const metadata = parseMetadata(event.metadata_json);
  const classification = classify(event.action);
  const projectId = event.resource_type === "project"
    ? event.resource_id
    : metadataString(metadata, "project_id");
  const projectName = projectId ? projects.find((project) => project.id === projectId)?.title ?? null : null;
  const actor = event.actor_id === actorId
    ? displayName
    : event.actor_type === "system" || event.actor_id.startsWith("system")
      ? "ClearCut"
      : event.actor_id.startsWith("demo-")
        ? "Studio team"
        : "Workspace member";
  const action = event.action.toLowerCase();
  const name = metadataString(metadata, "title") ?? metadataString(metadata, "name");
  let message = `${action.includes("created") ? "created" : action.includes("updated") ? "updated" : "recorded a change to"} ${humanize(event.resource_type)}`;
  if (action.includes("upload")) message = `uploaded source material${metadataString(metadata, "version_number") ? ` · version ${metadataString(metadata, "version_number")}` : ""}`;
  else if (action.includes("analysis") || action.includes("analy")) message = "completed AI analysis";
  else if (action.includes("research")) message = "completed rights research";
  else if (action.includes("approval") || action.includes("clearance")) message = "recorded a clearance decision";
  else if (action.includes("invitation")) message = action.includes("accepted") ? "accepted a workspace invitation" : "updated a workspace invitation";
  else if (name) message = `${message} · ${name}`;
  return { actor, message, projectName, kind: classification.kind, kindLabel: classification.label, metadata };
}

function relativeLabel(value: string): string {
  const date = new Date(value);
  const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 172800) return "Yesterday";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" }).format(date);
}

function dayLabel(value: string): string {
  const date = new Date(value);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  return new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long" }).format(date);
}

function groupedActivity(items: Activity[]): Array<{ label: string; items: Activity[] }> {
  const groups: Array<{ label: string; items: Activity[] }> = [];
  for (const item of items) {
    const label = dayLabel(item.created_at);
    const group = groups[groups.length - 1];
    if (group?.label === label) group.items.push(item);
    else groups.push({ label, items: [item] });
  }
  return groups;
}

function exportActivity(items: Activity[], projects: Project[], actorId: string | undefined, displayName: string): void {
  const rows = [
    ["Timestamp", "Actor", "Event", "Project", "Type", "Resource ID"],
    ...items.map((event) => {
      const copy = activityCopy(event, projects, actorId, displayName);
      return [event.created_at, copy.actor, copy.message, copy.projectName ?? "", copy.kindLabel, event.resource_id];
    }),
  ];
  const csv = rows.map((row) => row.map((value) => `"${value.replaceAll('"', '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `clearcut-activity-${new Date().toISOString().slice(0, 10)}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ActivityViewer() {
  const auth = useAuth();
  const [activity, setActivity] = useState<Activity[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
  const [kindFilter, setKindFilter] = useState<ActivityKind | "all">("all");
  const [projectFilter, setProjectFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const displayName = auth.user?.displayName ?? "You";

  async function load() {
    setLoading(true);
    try {
      const [activityResponse, notificationsResponse, projectsResponse] = await Promise.all([
        fetch(`${apiUrl}/v1/activity`, { cache: "no-store" }),
        fetch(`${apiUrl}/v1/notifications`, { cache: "no-store" }),
        fetch(`${apiUrl}/v1/projects`, { cache: "no-store" }),
      ]);
      if (!activityResponse.ok || !notificationsResponse.ok) throw new Error("Activity data is not available yet.");
      setActivity(await activityResponse.json() as Activity[]);
      setNotifications(await notificationsResponse.json() as Notification[]);
      setProjects(projectsResponse.ok ? await projectsResponse.json() as Project[] : []);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load activity.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (auth.status !== "authenticated") return;
    void load();
  }, [auth.organizationId, auth.status]);

  async function markRead(notificationId: string) {
    const response = await fetch(`${apiUrl}/v1/notifications/${notificationId}/read`, { method: "POST" });
    if (response.ok) setNotifications((current) => current.map((notification) => notification.id === notificationId ? { ...notification, read_at: new Date().toISOString() } : notification));
  }

  const filteredActivity = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return activity.filter((event) => {
      const copy = activityCopy(event, projects, auth.user?.actorId, displayName);
      const matchesKind = kindFilter === "all" || copy.kind === kindFilter;
      const matchesProject = !projectFilter || (event.resource_type === "project" && event.resource_id === projectFilter) || metadataString(copy.metadata, "project_id") === projectFilter;
      const searchText = `${copy.actor} ${copy.message} ${copy.projectName ?? ""} ${event.action} ${event.resource_id}`.toLowerCase();
      return matchesKind && matchesProject && (!normalizedQuery || searchText.includes(normalizedQuery));
    });
  }, [activity, auth.user?.actorId, displayName, kindFilter, projectFilter, projects, query]);

  const groups = groupedActivity(filteredActivity);
  const unreadCount = notifications.filter((notification) => !notification.read_at).length;
  const reviewCount = activity.filter((event) => activityCopy(event, projects, auth.user?.actorId, displayName).kind === "review").length;

  return (
    <div className="activity-page">
      <div className="activity-page-header">
        <div>
          <div className="eyebrow">Workspace accountability</div>
          <h1>Activity</h1>
          <p>A transparent record of what changed, who acted, and when.</p>
        </div>
        <button className="secondary-button activity-export" disabled={!activity.length} onClick={() => exportActivity(filteredActivity, projects, auth.user?.actorId, displayName)} type="button">Export activity</button>
      </div>

      <div className="activity-stats" aria-label="Activity summary">
        <div><span>Total events</span><strong>{activity.length}</strong></div>
        <div><span>Clearance decisions</span><strong>{reviewCount}</strong></div>
        <div><span>Unread notifications</span><strong>{unreadCount}</strong></div>
      </div>

      <div className="activity-layout">
        <section className="panel activity-panel">
          <div className="activity-toolbar">
            <label className="activity-search"><span aria-hidden="true">⌕</span><input aria-label="Search activity" onChange={(event) => setQuery(event.target.value)} placeholder="Search activity, correlation IDs, or actors…" value={query} /></label>
            <div className="activity-filter-row">
              <div className="activity-filter-chips" role="group" aria-label="Filter by event type">
                {(["all", "review", "upload", "analysis", "research", "workspace"] as const).map((filter) => <button className={kindFilter === filter ? "active" : ""} key={filter} onClick={() => setKindFilter(filter)} type="button">{filter === "all" ? "All events" : filter === "review" ? "Clearance" : humanize(filter)}</button>)}
              </div>
              <select aria-label="Filter by project" onChange={(event) => setProjectFilter(event.target.value)} value={projectFilter}><option value="">All projects</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select>
              {(query || kindFilter !== "all" || projectFilter) ? <button className="activity-clear" onClick={() => { setQuery(""); setKindFilter("all"); setProjectFilter(""); }} type="button">Clear filters</button> : null}
            </div>
          </div>
          {message ? <div className="review-message" role="status">{message}</div> : null}
          {loading ? <div className="activity-empty">Loading activity…</div> : groups.length ? <div className="activity-timeline">{groups.map((group) => <div className="activity-group" key={group.label}><div className="activity-date-label">{group.label}</div>{group.items.map((event) => { const copy = activityCopy(event, projects, auth.user?.actorId, displayName); const expanded = expandedId === event.id; return <article className={`activity-event ${copy.kind} ${expanded ? "expanded" : ""}`} key={event.id}><button aria-expanded={expanded} className="activity-event-trigger" onClick={() => setExpandedId(expanded ? null : event.id)} type="button"><span className="activity-event-avatar">{copy.kind === "upload" ? "↑" : copy.kind === "analysis" ? "✦" : copy.kind === "research" ? "⌕" : copy.kind === "review" ? "✓" : copy.kind === "workspace" ? "•" : "·"}</span><span className="activity-event-content"><span className="activity-event-topline"><span><strong>{copy.actor}</strong> <span>{copy.message}</span></span><time dateTime={event.created_at}>{relativeLabel(event.created_at)}</time></span><span className="activity-event-subline">{copy.projectName ? `Project: ${copy.projectName}` : humanize(event.resource_type)}<span className={`activity-kind-tag ${copy.kind}`}>{copy.kindLabel}</span></span></span><span className="activity-event-chevron" aria-hidden="true">{expanded ? "−" : "+"}</span></button>{expanded ? <div className="activity-event-details"><div><span>Event</span><strong>{humanize(event.action)}</strong></div><div><span>Recorded</span><strong>{new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(event.created_at))}</strong></div><div><span>Resource</span><strong>{humanize(event.resource_type)}</strong></div><div><span>Reference</span><code>{event.resource_id.slice(0, 12)}</code></div></div> : null}</article>; })}</div>)}</div> : <div className="activity-empty"><strong>No activity found</strong><span>Try adjusting your filters or search terms to find what you’re looking for.</span>{(query || kindFilter !== "all" || projectFilter) ? <button className="secondary-button" onClick={() => { setQuery(""); setKindFilter("all"); setProjectFilter(""); }} type="button">Clear filters</button> : null}</div>}
        </section>

        <section className="panel notification-panel"><div className="panel-header"><div><h2>Notifications</h2><p className="panel-subtitle">Mentions, assignments, and review changes</p></div><span>{unreadCount} unread</span></div><div className="notification-list">{notifications.map((notification) => <article className={`notification-row ${notification.read_at ? "read" : "unread"}`} key={notification.id}><div><strong>{notification.title}</strong><p>{notification.body}</p><small>{new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(notification.created_at))}</small></div>{!notification.read_at ? <button className="table-action" onClick={() => void markRead(notification.id)} type="button">Mark read</button> : null}</article>)}{!loading && !notifications.length ? <div className="activity-empty compact">No notifications yet.</div> : null}</div></section>
      </div>
    </div>
  );
}
