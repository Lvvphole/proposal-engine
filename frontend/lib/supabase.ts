import { createClient, type SupabaseClient } from "@supabase/supabase-js";

// Configured from Vercel / .env.local. When unset, auth is disabled and the
// app runs unauthenticated — matching the backend's AUTH_ENABLED=false default.
const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const supabase: SupabaseClient | null =
  url && anonKey ? createClient(url, anonKey) : null;

export const authConfigured: boolean = supabase !== null;
