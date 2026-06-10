# AI Booth Generator

Chat-based exhibition booth consultant for the UAE market. Collects requirements via LLM, generates booth concepts with Hugging Face, and recommends budget-aware UAE contractors via web search.

## Stack

- **Backend:** FastAPI, Supabase, OpenRouter (Gemma), Hugging Face (FLUX), Cloudinary
- **Frontend:** React + Vite

## Setup

### 1. Database

Run migrations in Supabase SQL editor (in order):

- `database/schema.sql`
- `database/migrations/001` through `006`

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env           # fill in keys
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Deploy on Vercel

The repo is configured for a **single Vercel project**: React frontend (static) + FastAPI backend (Python serverless function).

### 1. Connect GitHub

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import `abdalrahmanali110-wq/Ai-booth-gen`
3. Leave **Root Directory** as `.` (repo root)
4. Vercel reads `vercel.json` automatically

### 2. Environment variables

Add these in **Project → Settings → Environment Variables** (Production):

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase service role key |
| `HUGGINGFACE_API_KEY` | Hugging Face token |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `GEMMA_MODEL` | e.g. `google/gemma-4-31b-it:free` |
| `IMAGE_MODEL` | e.g. `black-forest-labs/FLUX.1-schnell` |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Cloudinary secret |
| `DEFAULT_USER_ID` | UUID of your Supabase user |

Do **not** set `VITE_API_URL` on Vercel — the frontend calls the API on the same domain.

### 3. Plan requirement

Image generation and web search can take **1–3 minutes**. Set `maxDuration: 300` in `vercel.json` (already configured). You need a **Vercel Pro** plan for function timeouts above 10 seconds; Hobby tier will timeout during booth generation.

### 4. Deploy

Push to `main` — Vercel redeploys automatically.

Or from CLI:

```bash
npm i -g vercel
vercel login
vercel --prod
```

Your app will be live at `https://your-project.vercel.app`.

## Environment variables

See `backend/.env.example` and `frontend/.env.example`.
