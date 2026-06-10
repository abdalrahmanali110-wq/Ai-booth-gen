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

## Environment variables

See `backend/.env.example` and `frontend/.env.example`.
