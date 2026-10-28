# Frontend application-security review

Branch: `cursor/application-security-review-e4de`  
Scope: `frontend/src/**/*.{js,jsx}` (with backend only to validate E2E reachability)  
Already reported (#1–#8) and prior dismissals were treated as out of scope for duplicates.

## (A) NEW validated finding

### F9 — Implicit OAuth leaves access/refresh tokens in tab session history

- **Severity:** Medium (High on shared devices)
- **Type:** OAuth token exposure / session hijack precursor (distinct from #7 injection)
- **Components:**
  - `frontend/src/services/supabaseClient.js` (no `flowType: 'pkce'` → library default `implicit`)
  - `frontend/src/pages/Chat/Chat.jsx` (OAuth return handling + `history.replaceState` cleanup)
  - `@supabase/auth-js` `GoTrueClient._getSessionFromURL` clears the fragment via `window.location.hash = ''`

#### Why this is not #7

| | #7 (already reported) | F9 (this finding) |
|---|---|---|
| Prerequisite | Attacker crafts a malicious URL containing tokens | Victim completes a **legitimate** Google sign-in |
| Mechanism | Token **injection** into the victim browser | Token **residue** left in the tab’s session history |
| User action | Click attacker link | Sign in, then later use Back / share the machine |

#### Technical root cause

1. `createClient(..., { auth: { detectSessionInUrl: true } })` does **not** set `flowType: 'pkce'`.
2. Confirmed at runtime with the installed `@supabase/supabase-js@2.111`: **`flowType === "implicit"`**.
3. Implicit redirect returns:
   `/chat/<sessionId>#access_token=...&refresh_token=...&provider_token=...&token_type=bearer&expires_in=...`
4. After parsing, auth-js clears the fragment with **`window.location.hash = ''`**, which navigates and **pushes a new session-history entry** instead of replacing the token URL.
5. `Chat.jsx` later runs `history.replaceState({}, "", "/chat/...")`, which only rewrites the **current** entry. The prior history entry still contains the secrets.

#### E2E attack path

1. Victim signs in with Google on Booth AI (shared PC, kiosk, or unattended laptop).
2. Supabase redirects back to `/chat/...#access_token=<victim>&refresh_token=<victim>&...`.
3. App finishes sign-in; UI URL looks clean.
4. Attacker (or next user of the machine) presses **Back** until the OAuth callback entry reappears with tokens in the fragment.
5. Attacker copies `access_token` / `refresh_token`.
6. Impact:
   - Call `POST /auth/oauth/complete` with the stolen `access_token` → become the victim’s app user, claim sessions, create leads under the victim email.
   - Use the Supabase session / refresh token as the victim (especially powerful with missing RLS #1).
   - Optionally reopen the token URL in the app: `Chat.jsx` treats `hash.includes("access_token")` as an OAuth return and re-runs `completeOAuth` + session claim.

#### Remediation (applied on this branch)

1. Set `flowType: 'pkce'` in `getSupabaseClient()` so codes arrive in the query string (single-use, verifier-bound), not tokens in the hash.
2. Tighten `hasOAuthReturn` to parse real `code` / `access_token` parameters instead of substring `includes(...)`.
3. On `completeOAuth` success **and** failure, scrub auth params with `history.replaceState` only (avoid leaving bearer tokens recoverable via Back).

---

## (B) Dismissed candidates (this pass)

| Candidate | Why dismissed |
|---|---|
| `ConsultationReport` / `BoothWorkspace` / `Design` `javascript:` / open-URL in `href`/`src` | Real sinks, but weaponization needs poisoned `image_url` / `company.url` via already-reported #1/#2 (same class as prior “download `window.open` needs poisoned URLs”). |
| React text XSS in messages / titles / errors | Text nodes only; previously dismissed. |
| AuthModal `redirectTo` open redirect | Built from `window.location.origin` + path; previously dismissed. |
| postMessage / DOM clobbering | No `postMessage` listeners; no clobberable globals in app code. |
| Prototype pollution via `JSON.parse` of `ai_booth_auth` | Parsed object is read for own fields only; no unsafe recursive merge. |
| localStorage `auth_user_id` spoofing | Impact is #2 / #3 (already reported). |
| Visitor-id interceptor “adoption” of foreign IDs | Top-level `visitor_id` is always the caller’s resolved visitor; session GET nests `visitor_id` under `session` (disclosure = #8, not auto-adopt). |
| `?code=` CSRF session planting into a logged-in account | Claim is blocked when victim sends a mismatched `X-Visitor-Id` (normal after first API call); race is unreliable. Overlaps #7 when real attacker tokens are present. |
| OAuth `code` Referer leak to Google Fonts | Fragments aren’t sent; with implicit flow the secret is in the hash. Prior “PKCE code forwarding needs verifier” dismissal covers code-only theft. |
| CSP missing | No concrete first-party XSS chain beyond poison-via-#1/#2 sinks. |
| ModelViewer arbitrary GLB URL | Integrity / parser risk only; previously dismissed. |
| `default_user_id` on `GET /auth/config` | Enables picking a known UUID for #2; not a new impact class. |
| Unauthenticated `GET /models3d/{id}` | Backend IDOR; UUID job IDs not exposed by frontend routes. |

## Files fully reviewed

`Chat.jsx`, `AuthModal.jsx`, `MessageList.jsx`, `ConsultationReport.jsx`, `BoothWorkspace.jsx`, `ModelViewer.jsx`, `api.js`, `authService.js`, `storage.js`, `supabaseClient.js`, `App.jsx`, `Design.jsx`, `RequirementsPanel.jsx`, `SessionSidebar.jsx`, `SummaryConfirmPopup.jsx`, `InlineQuestionCard.jsx`, `ProjectBrief.jsx`, plus remaining `frontend/src` services/hooks/utils.
