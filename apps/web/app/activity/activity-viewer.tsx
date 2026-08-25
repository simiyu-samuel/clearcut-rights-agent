"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { useEffect, useState } from "react";

type Activity = { id: string; action: string; actor_id: string; resource_type: string; resource_id: string; created_at: string; metadata_json: string | null };
type Notification = { id: string; title: string; body: string; read_at: string | null; created_at: string };
const headers = { "x-organization-id": "demo-org", "x-actor-id": "demo-user" };

function label(value: string) { return value.replaceAll("_", " "); }
function dateLabel(value: string) { return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }

export function ActivityViewer() {
  const [activity, setActivity] = useState<Activity[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  async function load() {
    setLoading(true);
    try {
      const [activityResponse, notificationsResponse] = await Promise.all([
        fetch(`${apiUrl}/v1/activity`, { headers, cache: "no-store" }),
        fetch(`${apiUrl}/v1/notifications`, { headers, cache: "no-store" }),
      ]);
      if (!activityResponse.ok || !notificationsResponse.ok) throw new Error("Activity data is not available yet.");
      setActivity(await activityResponse.json() as Activity[]);
      setNotifications(await notificationsResponse.json() as Notification[]);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load activity.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function markRead(notificationId: string) {
    const response = await fetch(`${apiUrl}/v1/notifications/${notificationId}/read`, { method: "POST", headers });
    if (response.ok) setNotifications((current) => current.map((notification) => notification.id === notificationId ? { ...notification, read_at: new Date().toISOString() } : notification));
  }

  return (
    <div className="activity-layout">
      <section className="panel"><div className="panel-header"><div><h2>Activity trail</h2><p className="panel-subtitle">Immutable workflow events across the workspace</p></div><button className="table-action" disabled={loading} onClick={() => void load()} type="button">{loading ? "Refreshing…" : "Refresh"}</button></div>{message ? <div className="review-message" role="status">{message}</div> : null}<div className="activity-feed">{activity.map((event) => <article className="activity-feed-row" key={event.id}><span className="activity-dot" /><div><strong>{label(event.action)}</strong><p>{event.actor_id} updated {event.resource_type} <code>{event.resource_id.slice(0, 8)}</code></p><small>{dateLabel(event.created_at)}</small></div></article>)}{!loading && !activity.length ? <div className="review-empty">No workspace activity recorded yet.</div> : null}</div></section>
      <section className="panel"><div className="panel-header"><div><h2>Notifications</h2><p className="panel-subtitle">Mentions, assignments, and review changes</p></div><span>{notifications.filter((notification) => !notification.read_at).length} unread</span></div><div className="notification-list">{notifications.map((notification) => <article className={`notification-row ${notification.read_at ? "read" : "unread"}`} key={notification.id}><div><strong>{notification.title}</strong><p>{notification.body}</p><small>{dateLabel(notification.created_at)}</small></div>{!notification.read_at ? <button className="table-action" onClick={() => void markRead(notification.id)} type="button">Mark read</button> : null}</article>)}{!loading && !notifications.length ? <div className="review-empty">No notifications yet.</div> : null}</div></section>
    </div>
  );
}
