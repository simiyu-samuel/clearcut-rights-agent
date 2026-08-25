"use client";

import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { authorizedFetch as fetch } from "@/lib/api-client";
import { authErrorMessage } from "@/lib/auth";
import { useState, type FormEvent } from "react";

function Brand() {
  return <div className="brand"><img className="brand-logo" src="/clearcut-logo.png" alt="ClearCut" /></div>;
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const auth = useAuth();
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaceMessage, setWorkspaceMessage] = useState("");
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [signInMessage, setSignInMessage] = useState("");
  const [authView, setAuthView] = useState<"google" | "email" | "register">("google");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authDisplayName, setAuthDisplayName] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [resetSent, setResetSent] = useState(false);
  if (pathname.startsWith("/review/")) return children;

  if (auth.status === "loading") {
    return <main className="auth-screen"><Brand /><div className="auth-card panel"><span className="eyebrow">Secure workspace</span><h1>Loading your workspace…</h1><p>Checking your ClearCut identity and access.</p></div></main>;
  }
  if (auth.status === "configuration_error") {
    return <main className="auth-screen"><Brand /><div className="auth-card panel"><span className="eyebrow">Workspace configuration</span><h1>Authentication needs setup.</h1><p>Set the Firebase client configuration and API audience before using Identity Platform mode.</p></div></main>;
  }
  if (auth.status === "signed_out") {
    async function signInGoogle() {
      setSignInMessage("");
      setResetSent(false);
      try { await auth.signInWithGoogle(); } catch (error) { setSignInMessage(authErrorMessage(error)); }
    }
    async function submitEmail(event: FormEvent<HTMLFormElement>) {
      event.preventDefault();
      setSignInMessage("");
      setResetSent(false);
      setAuthBusy(true);
      try {
        if (authView === "register") {
          if (authPassword.length < 6) throw new Error("Use a password with at least six characters.");
          await auth.registerWithEmail(authEmail, authPassword, authDisplayName);
        } else {
          await auth.signInWithEmail(authEmail, authPassword);
        }
      } catch (error) {
        setSignInMessage(authErrorMessage(error));
      } finally {
        setAuthBusy(false);
      }
    }
    async function sendReset() {
      setSignInMessage("");
      setResetSent(false);
      if (!authEmail.trim()) { setSignInMessage("Enter your email first."); return; }
      setAuthBusy(true);
      try {
        await auth.resetPassword(authEmail);
        setResetSent(true);
      } catch (error) {
        setSignInMessage(authErrorMessage(error));
      } finally {
        setAuthBusy(false);
      }
    }
    return <main className="auth-screen"><Brand /><div className="auth-card panel"><span className="eyebrow">ClearCut workspace</span><h1>Rights work, with a clear chain of custody.</h1><p>Sign in to review evidence, assign actions, and prepare delivery records for your production.</p>{signInMessage ? <div className="form-message" role="alert">{signInMessage}</div> : null}{resetSent ? <div className="form-success" role="status">Password reset instructions sent. Check your inbox.</div> : null}<div className="auth-methods"><button className="primary-button" disabled={authBusy} onClick={() => void signInGoogle()} type="button">Continue with Google</button><div className="auth-divider"><span>or use email</span></div>{authView === "google" ? <button className="secondary-button" onClick={() => setAuthView("email")} type="button">Sign in with email</button> : <form className="auth-form" onSubmit={(event) => void submitEmail(event)}><label className="form-field"><span>Email address</span><input autoComplete="email" onChange={(event) => setAuthEmail(event.target.value)} placeholder="you@studio.com" required type="email" value={authEmail} /></label>{authView === "register" ? <label className="form-field"><span>Your name</span><input autoComplete="name" onChange={(event) => setAuthDisplayName(event.target.value)} placeholder="Alex Morgan" type="text" value={authDisplayName} /></label> : null}<label className="form-field"><span>Password</span><input autoComplete={authView === "register" ? "new-password" : "current-password"} minLength={6} onChange={(event) => setAuthPassword(event.target.value)} required type="password" value={authPassword} /></label><button className="primary-button" disabled={authBusy} type="submit">{authBusy ? "Working…" : authView === "register" ? "Create account" : "Sign in"}</button>{authView === "email" ? <button className="auth-link-button" disabled={authBusy} onClick={() => void sendReset()} type="button">Forgot password?</button> : null}<button className="auth-link-button" onClick={() => { setAuthView(authView === "register" ? "email" : "register"); setSignInMessage(""); }} type="button">{authView === "register" ? "Already have an account? Sign in" : "New to ClearCut? Create an account"}</button><button className="auth-link-button" onClick={() => setAuthView("google")} type="button">Use Google instead</button></form>}</div></div></main>;
  }
  if (!auth.memberships.length) {
    async function createWorkspace() {
      if (workspaceName.trim().length < 2) { setWorkspaceMessage("Enter a workspace name first."); return; }
      setCreatingWorkspace(true);
      setWorkspaceMessage("");
      try {
        const response = await fetch("/v1/organizations", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ name: workspaceName.trim() }) });
        if (!response.ok) { const payload = await response.json().catch(() => ({})); throw new Error(payload.detail ?? "Unable to create workspace."); }
        window.location.reload();
      } catch (error) {
        setWorkspaceMessage(error instanceof Error ? error.message : "Unable to create workspace.");
        setCreatingWorkspace(false);
      }
    }
    return <main className="auth-screen"><Brand /><div className="auth-card panel"><span className="eyebrow">First workspace</span><h1>Create your ClearCut workspace.</h1><p>You are signed in, but this account is not attached to a production organization yet. Create one now or ask an administrator for an invite.</p><label className="form-field"><span>Workspace name</span><input value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} placeholder="e.g. Meridian Pictures" /></label>{workspaceMessage ? <div className="form-message" role="status">{workspaceMessage}</div> : null}<div className="form-actions"><button className="primary-button" disabled={creatingWorkspace} onClick={() => void createWorkspace()} type="button">{creatingWorkspace ? "Creating…" : "Create workspace"}</button><button className="secondary-button" onClick={() => void auth.signOut()} type="button">Sign out</button></div></div></main>;
  }
  return children;
}
