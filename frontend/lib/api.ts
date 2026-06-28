import { supabase } from "./supabase";

/**
 * fetch wrapper that attaches the Supabase access token as a Bearer header
 * when a user is signed in. Falls back to a plain fetch when auth isn't
 * configured, so the app keeps working with AUTH_ENABLED=false.
 */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  return fetch(path, { ...init, headers });
}

/** Open an authenticated HTML document in a new tab via a blob URL.
 * A plain anchor navigation can't carry the Bearer header, so we fetch it. */
export async function openAuthedDocument(path: string): Promise<void> {
  const res = await apiFetch(path);
  if (!res.ok) throw new Error(`Failed to load document (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener,noreferrer");
  // Revoke shortly after so the new tab has time to load it.
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
