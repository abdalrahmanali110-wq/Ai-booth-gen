import { useState } from "react";
import { getSupabaseClient } from "../services/supabaseClient";
import { setPendingAuthSession } from "../services/storage";

export default function AuthModal({
  open,
  onClose,
  sessionId,
  intent = "signin",
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  const forConvert = intent === "convert";

  async function handleGoogleSignIn() {
    setLoading(true);
    setError("");

    try {
      setPendingAuthSession(sessionId || null, { convert: forConvert });
      const supabase = await getSupabaseClient();
      const redirectTo = sessionId
        ? `${window.location.origin}/chat/${sessionId}`
        : `${window.location.origin}/chat`;

      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo,
          queryParams: {
            access_type: "offline",
            prompt: "select_account",
          },
        },
      });

      if (oauthError) {
        throw oauthError;
      }
    } catch (err) {
      setPendingAuthSession(null);
      setError(err.message || "Google sign-in failed.");
      setLoading(false);
    }
  }

  return (
    <div className="auth-modal-backdrop" role="dialog" aria-modal="true">
      <div className="auth-modal">
        <header className="auth-modal-header">
          <h2>{forConvert ? "Sign in to unlock 3D" : "Welcome back"}</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>
        <p className="auth-modal-copy">
          {forConvert
            ? "Sign in with Google to convert your booth concept into an interactive 3D model and save your project."
            : "Sign in with Google anytime to save your booth projects and unlock 3D conversion."}
        </p>

        {error && (
          <p className="auth-error" role="alert">
            {error}
          </p>
        )}

        <button
          type="button"
          className="google-signin-btn pressable"
          onClick={handleGoogleSignIn}
          disabled={loading}
        >
          <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
            <path
              fill="#FFC107"
              d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 7.9 3l5.7-5.7C34.2 6.1 29.4 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.5-.4-3.5z"
            />
            <path
              fill="#FF3D00"
              d="M6.3 14.7l6.6 4.8C14.7 16.1 19 13 24 13c3 0 5.8 1.1 7.9 3l5.7-5.7C34.2 6.1 29.4 4 24 4 16.3 4 9.6 8.3 6.3 14.7z"
            />
            <path
              fill="#4CAF50"
              d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.3 0-9.7-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z"
            />
            <path
              fill="#1976D2"
              d="M43.6 20.5H42V20H24v8h11.3c-1.1 3.1-3.5 5.5-6.5 6.6l.1.1 6.2 5.2C36.9 41.1 44 36 44 24c0-1.3-.1-2.5-.4-3.5z"
            />
          </svg>
          {loading ? "Redirecting to Google..." : "Continue with Google"}
        </button>
      </div>
    </div>
  );
}
