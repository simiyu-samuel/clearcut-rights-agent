"use client";

import { getApp, getApps, initializeApp, type FirebaseApp } from "firebase/app";
import {
  createUserWithEmailAndPassword,
  getAuth,
  GoogleAuthProvider,
  onIdTokenChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut as firebaseSignOut,
  updateProfile,
  type Auth,
  type User,
  type UserCredential,
} from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
};

export function authMode(): "demo" | "identity_platform" {
  return process.env.NEXT_PUBLIC_AUTH_MODE === "identity_platform" ? "identity_platform" : "demo";
}

export function firebaseIsConfigured(): boolean {
  return Boolean(
    firebaseConfig.apiKey &&
      firebaseConfig.authDomain &&
      firebaseConfig.projectId &&
      firebaseConfig.appId,
  );
}

let app: FirebaseApp | null = null;
let auth: Auth | null = null;

export function getFirebaseAuth(): Auth | null {
  if (authMode() === "demo" || !firebaseIsConfigured()) return null;
  if (!app) app = getApps().length ? getApp() : initializeApp(firebaseConfig);
  auth ??= getAuth(app);
  return auth;
}

export function subscribeToAuth(callback: (user: User | null) => void): () => void {
  const firebaseAuth = getFirebaseAuth();
  return firebaseAuth ? onIdTokenChanged(firebaseAuth, callback) : () => undefined;
}

export async function signInWithGoogle(): Promise<UserCredential> {
  const firebaseAuth = getFirebaseAuth();
  if (!firebaseAuth) throw new Error("identity_platform_not_configured");
  const provider = new GoogleAuthProvider();
  provider.setCustomParameters({ prompt: "select_account" });
  return signInWithPopup(firebaseAuth, provider);
}

export async function signInWithEmail(email: string, password: string): Promise<UserCredential> {
  const firebaseAuth = getFirebaseAuth();
  if (!firebaseAuth) throw new Error("identity_platform_not_configured");
  return signInWithEmailAndPassword(firebaseAuth, email.trim(), password);
}

export async function registerWithEmail(
  email: string,
  password: string,
  displayName: string,
): Promise<UserCredential> {
  const firebaseAuth = getFirebaseAuth();
  if (!firebaseAuth) throw new Error("identity_platform_not_configured");
  const credential = await createUserWithEmailAndPassword(firebaseAuth, email.trim(), password);
  if (displayName.trim()) {
    await updateProfile(credential.user, { displayName: displayName.trim() });
  }
  return credential;
}

export async function resetPassword(email: string): Promise<void> {
  const firebaseAuth = getFirebaseAuth();
  if (!firebaseAuth) throw new Error("identity_platform_not_configured");
  await sendPasswordResetEmail(firebaseAuth, email.trim());
}

export function authErrorMessage(error: unknown): string {
  const code = typeof error === "object" && error && "code" in error
    ? String((error as { code?: unknown }).code)
    : "";
  switch (code) {
    case "auth/email-already-in-use":
      return "An account already exists for this email. Sign in instead.";
    case "auth/invalid-credential":
    case "auth/invalid-login-credentials":
      return "The email or password is incorrect.";
    case "auth/invalid-email":
      return "Enter a valid email address.";
    case "auth/weak-password":
      return "Use a stronger password with at least six characters.";
    case "auth/popup-closed-by-user":
      return "The Google sign-in window was closed before completion.";
    case "auth/popup-blocked":
      return "Your browser blocked the Google sign-in window. Allow pop-ups and try again.";
    case "auth/too-many-requests":
      return "Too many attempts. Wait a moment and try again.";
    default:
      return error instanceof Error ? error.message : "Unable to authenticate.";
  }
}

export async function signOut(): Promise<void> {
  const firebaseAuth = getFirebaseAuth();
  if (firebaseAuth) await firebaseSignOut(firebaseAuth);
}

export function currentUser(): User | null {
  return getFirebaseAuth()?.currentUser ?? null;
}
