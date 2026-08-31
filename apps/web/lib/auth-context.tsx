"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { User } from "firebase/auth";
import {
  authMode,
  currentUser,
  firebaseIsConfigured,
  registerWithEmail,
  resetPassword,
  signInWithDemo,
  signInWithEmail,
  signInWithGoogle,
  signOut,
  subscribeToAuth,
} from "./auth";

export type Membership = {
  id: string;
  organization_id: string;
  actor_id: string;
  display_name: string;
  role: string;
  status: string;
  organization_name?: string | null;
};

type AuthMeResponse = {
  identity: { actor_id: string; email: string | null; display_name: string };
  memberships: Membership[];
};

type AuthUser = {
  actorId: string;
  email: string | null;
  displayName: string;
};

type AuthContextValue = {
  status: "loading" | "signed_out" | "authenticated" | "configuration_error" | "workspace_error";
  errorMessage: string | null;
  user: AuthUser | null;
  memberships: Membership[];
  organizationId: string | null;
  organizationRole: string | null;
  signInWithGoogle: () => Promise<void>;
  signInWithDemo: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  registerWithEmail: (email: string, password: string, displayName: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
  selectOrganization: (organizationId: string) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const organizationStorageKey = "clearcut.organization_id";

function isOpaqueIdentity(value: string | null | undefined, actorId: string): boolean {
  const normalized = value?.trim();
  return !normalized || normalized === actorId || /^[0-9a-f]{8}-[0-9a-f-]{27,}$/i.test(normalized);
}

function emailDisplayName(email: string | null | undefined): string | null {
  const localPart = email?.split("@", 1)[0]?.replace(/[._-]+/g, " ").replace(/\d+$/g, "").trim();
  if (!localPart) return null;
  return localPart.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function resolveDisplayName(firebaseUser: User, payload: AuthMeResponse): string {
  const candidates = [
    firebaseUser.displayName,
    payload.memberships.find((membership) => membership.actor_id === payload.identity.actor_id)?.display_name,
    payload.identity.display_name,
  ];
  const usable = candidates.find((candidate) => !isOpaqueIdentity(candidate, payload.identity.actor_id));
  return usable?.trim() || emailDisplayName(firebaseUser.email || payload.identity.email) || "ClearCut user";
}

function demoSnapshot(): Pick<AuthContextValue, "user" | "memberships" | "organizationId"> {
  return {
    user: { actorId: "demo-user", email: null, displayName: "Studio Admin" },
    memberships: [
      {
        id: "demo-membership-demo-user",
        organization_id: "demo-org",
        actor_id: "demo-user",
        display_name: "Studio Admin",
        role: "admin",
        status: "active",
      },
    ],
    organizationId: "demo-org",
  };
}

async function loadIdentity(user: User): Promise<AuthMeResponse> {
  const token = await user.getIdToken();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const response = await fetch(`${apiUrl}/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Unable to load workspace access.");
  }
  return response.json() as Promise<AuthMeResponse>;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthContextValue["status"]>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [organizationId, setOrganizationId] = useState<string | null>(null);

  useEffect(() => {
    if (authMode() === "demo") {
      const snapshot = demoSnapshot();
      setUser(snapshot.user);
      setMemberships(snapshot.memberships);
      setOrganizationId(snapshot.organizationId);
      setStatus("authenticated");
      return;
    }
    if (!firebaseIsConfigured()) {
      setStatus("configuration_error");
      return;
    }

    let active = true;
    const unsubscribe = subscribeToAuth((firebaseUser) => {
      if (!firebaseUser) {
        setUser(null);
        setMemberships([]);
        setOrganizationId(null);
        setStatus("signed_out");
        return;
      }
      void loadIdentity(firebaseUser)
        .then((payload) => {
          if (!active) return;
          const stored = window.localStorage.getItem(organizationStorageKey);
          const selected = payload.memberships.some((item) => item.organization_id === stored)
            ? stored
            : payload.memberships[0]?.organization_id ?? null;
          if (selected) window.localStorage.setItem(organizationStorageKey, selected);
          setUser({
            actorId: payload.identity.actor_id,
            email: payload.identity.email,
            displayName: resolveDisplayName(firebaseUser, payload),
          });
          setMemberships(payload.memberships);
          setOrganizationId(selected);
          setStatus("authenticated");
        })
        .catch(() => {
          if (active) {
            setErrorMessage("Unable to load workspace access. Refresh and try again.");
            setStatus("workspace_error");
          }
        });
    });
    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      errorMessage,
      user,
      memberships,
      organizationId,
      organizationRole:
        memberships.find((item) => item.organization_id === organizationId)?.role ?? null,
      signInWithGoogle: async () => {
        await signInWithGoogle();
      },
      signInWithDemo: async () => {
        await signInWithDemo();
      },
      signInWithEmail: async (email: string, password: string) => {
        await signInWithEmail(email, password);
      },
      registerWithEmail: async (email: string, password: string, displayName: string) => {
        await registerWithEmail(email, password, displayName);
      },
      resetPassword: async (email: string) => {
        await resetPassword(email);
      },
      signOut: async () => {
        await signOut();
        setUser(null);
        setMemberships([]);
        setOrganizationId(null);
        setStatus("signed_out");
      },
      selectOrganization: (selectedOrganizationId: string) => {
        if (!memberships.some((item) => item.organization_id === selectedOrganizationId)) return;
        window.localStorage.setItem(organizationStorageKey, selectedOrganizationId);
        setOrganizationId(selectedOrganizationId);
      },
    }),
    [errorMessage, memberships, organizationId, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

export function getDemoOrCurrentUser(): User | null {
  return currentUser();
}
