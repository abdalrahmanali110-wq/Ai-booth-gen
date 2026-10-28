import { createClient } from "@supabase/supabase-js";
import { getAuthConfig } from "./authService";

let clientPromise = null;

export async function getSupabaseClient() {
  if (clientPromise) return clientPromise;

  clientPromise = (async () => {
    const viteUrl = import.meta.env.VITE_SUPABASE_URL;
    const viteKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

    let url = viteUrl;
    let anonKey = viteKey;

    if (!url || !anonKey) {
      const config = await getAuthConfig();
      url = config.supabase_url;
      anonKey = config.supabase_anon_key;
    }

    if (!url || !anonKey) {
      throw new Error(
        "Supabase Auth is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY."
      );
    }

    return createClient(url, anonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    });
  })();

  return clientPromise;
}
