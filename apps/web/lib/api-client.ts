"use client";

import { authMode, currentUser } from "./auth";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function authorizedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (authMode() === "demo") {
    if (!headers.has("x-organization-id")) {
      headers.set("x-organization-id", process.env.NEXT_PUBLIC_DEMO_ORGANIZATION_ID ?? "demo-org");
    }
    if (!headers.has("x-actor-id")) {
      headers.set("x-actor-id", process.env.NEXT_PUBLIC_DEMO_ACTOR_ID ?? "demo-user");
    }
  } else {
    const user = currentUser();
    if (!user) throw new Error("authentication_required");
    headers.set("Authorization", `Bearer ${await user.getIdToken()}`);
    const organizationId = window.localStorage.getItem("clearcut.organization_id");
    headers.delete("x-organization-id");
    if (organizationId) headers.set("x-organization-id", organizationId);
    headers.delete("x-actor-id");
  }
  const url = path.startsWith("http://") || path.startsWith("https://") ? path : `${apiUrl}${path}`;
  return fetch(url, { ...init, headers });
}

export { apiUrl };
