# Hostinger readiness (analysis — no migration yet)

This document summarizes how to run the AI Booth Generator on Hostinger later, without cutting over from Vercel yet.

## Current stack (keep)

| Layer | Recommendation |
|-------|----------------|
| Frontend | Static Vite build (`frontend/dist`) — Hostinger static hosting or Node |
| Backend | Long-running Python (VPS / Docker), **not** shared PHP hosting |
| Database | Keep **Supabase** managed Postgres for now |
| Files / GLB | Keep **Cloudinary** (or S3-compatible); avoid local disk |
| Secrets | Hostinger/VPS env vars only — never ship keys in the frontend |
| 3D / GPU | **Separate** GPU worker or external HF/Tripo API; do not co-locate on a cheap web plan |

## Hostinger plan tiers

1. **Shared / WordPress hosting** — Not suitable for FastAPI or async 3D jobs.
2. **VPS (recommended)** — Run `docker compose` with the API container; serve `frontend/dist` via nginx or Hostinger static.
3. **Optional GPU box** — Only if self-hosting image→3D; otherwise call Hugging Face / Tripo via `MODEL_3D_PROVIDER`.

## Docker on VPS

```bash
# From repo root
cp backend/.env.example backend/.env   # fill secrets
docker compose up -d --build api
```

- API listens on `:8000`
- Optional profile `frontend` for local Vite
- Optional profile `worker` for a future 3D worker process

On Vercel MVP, 3D jobs process in-request (or via `POST /models3d/{id}/process`). On Hostinger/VPS, prefer a real worker polling `PENDING` jobs.

## Cutover checklist

1. Run migrations through `008_lead_gen_3d.sql` on Supabase.
2. Set provider env: `LLM_PROVIDER`, `IMAGE_PROVIDER`, `MODEL_3D_PROVIDER`, `ANON_MAX_IMAGE_GENERATIONS`.
3. Set `SUPABASE_ANON_KEY` for Auth signup/login wrappers.
4. Build frontend with `VITE_API_URL` pointing at the VPS API (or same-origin reverse proxy).
5. Point DNS / SSL to Hostinger (or keep Vercel frontend proxying to VPS API).
6. Verify anonymous quota, claim session, Convert to 3D, and GLB viewer end-to-end.
7. Keep Cloudinary + Supabase; do not store uploads on the VPS disk.

## GPU separation

Image generation and image-to-3D should stay on external providers (HF / Tripo). The Hostinger VPS only orchestrates jobs, stores metadata in Supabase, and hosts the GLB URL from Cloudinary.

## Acceptable MVP limits

Anonymous cookie/VPN bypass of the 3-image quota is acknowledged for this phase. Enforce more strongly (device fingerprint + IP hash + auth) after lead-gen validation.
