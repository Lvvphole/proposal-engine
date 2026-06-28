"use client";

import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { authConfigured, supabase } from "../lib/supabase";

/**
 * Gates the app behind a Supabase session. When Supabase isn't configured
 * (no env vars), auth is disabled and children render directly — matching the
 * backend's AUTH_ENABLED=false default.
 */
export default function AuthGate({ children }: { children: React.ReactNode }) {
  if (!authConfigured) return <>{children}</>;
  return <AuthGateInner>{children}</AuthGateInner>;
}

function AuthGateInner({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase!.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });
    const { data: sub } = supabase!.auth.onAuthStateChange((_event, next) => {
      setSession(next);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  if (loading) {
    return <p className="p-8 text-center text-gray-500">Loading…</p>;
  }

  if (!session) {
    return <LoginForm />;
  }

  return (
    <>
      <SignOutBar email={session.user.email ?? "signed in"} />
      {children}
    </>
  );
}

function SignOutBar({ email }: { email: string }) {
  return (
    <div className="flex items-center justify-end gap-3 px-8 py-2 text-sm text-gray-500 border-b">
      <span>{email}</span>
      <button
        onClick={() => supabase!.auth.signOut()}
        className="underline hover:text-gray-800"
      >
        Sign out
      </button>
    </div>
  );
}

function LoginForm() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setBusy(true);
    try {
      if (mode === "signup") {
        const { error } = await supabase!.auth.signUp({ email, password });
        if (error) throw error;
        setInfo("Check your email to confirm your account, then sign in.");
        setMode("signin");
      } else {
        const { error } = await supabase!.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center p-8">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4">
        <div>
          <h1 className="text-2xl font-bold">Proposal Engine</h1>
          <p className="text-gray-600 text-sm mt-1">
            {mode === "signin" ? "Sign in to continue" : "Create your account"}
          </p>
        </div>

        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@company.com"
          className="w-full border rounded-lg p-3 text-sm"
        />
        <input
          type="password"
          required
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          className="w-full border rounded-lg p-3 text-sm"
        />

        {error && <p className="text-red-600 text-sm">{error}</p>}
        {info && <p className="text-green-700 text-sm">{info}</p>}

        <button
          type="submit"
          disabled={busy}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {busy ? "…" : mode === "signin" ? "Sign in" : "Sign up"}
        </button>

        <button
          type="button"
          onClick={() => {
            setMode(mode === "signin" ? "signup" : "signin");
            setError(null);
            setInfo(null);
          }}
          className="w-full text-sm text-gray-500 hover:text-gray-800"
        >
          {mode === "signin"
            ? "Need an account? Sign up"
            : "Already have an account? Sign in"}
        </button>
      </form>
    </main>
  );
}
