# VoicePilot AI

Agentic voice business assistant. React + TypeScript frontend, FastAPI backend, PostgreSQL (Docker) or SQLite (local), RAG over your own documents, safe tool calling, browser voice input and output.

## Run in VS Code (no Docker)

You need Python 3.12+ and Node 20+.

### 1. Backend (Terminal 1)

```
cd backend
python -m venv .venv
.venv\Scripts\activate          (Windows)
source .venv/bin/activate       (Mac/Linux)
pip install -r requirements.txt
copy ..\.env.example .env       (Windows)   or   cp ../.env.example .env
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

`python -m app.seed` prints the admin email and a random password. Save it. Open http://localhost:8000/docs to see the API.

### 2. Frontend (Terminal 2)

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## How frontend and backend are linked

`frontend/vite.config.ts` proxies every `/api/*` request to `http://localhost:8000`. `frontend/src/services/apiClient.ts` is the only place that calls the backend, attaches the JWT, and refreshes it on a 401. The browser never touches the database.

Server entry point: `backend/app/main.py`. Start it with `uvicorn app.main:app --reload --port 8000`.

## Docker (PostgreSQL)

```
docker compose up --build
```

Open http://localhost:5173. Nginx serves the frontend and forwards `/api` to the backend.

## Enable the real AI

Edit `backend/.env`: set `LLM_API_KEY` (any OpenAI-compatible provider, change `LLM_BASE_URL` and `LLM_MODEL` for others). Without a key the agent runs in a limited offline mode: calculator, time, and retrieval from your documents.

## Enable Google, GitHub, Microsoft login

Redirect URIs to register with each provider (dev):

```
http://localhost:5173/api/auth/google/callback
http://localhost:5173/api/auth/github/callback
http://localhost:5173/api/auth/microsoft/callback
```

Put the client ID and secret in `backend/.env`, restart the backend. Buttons stay disabled with "Not configured" until then.

## Tests

```
cd backend
pytest -q
cd ../frontend
npm run build
```

## Voice

Speech recognition and speech synthesis use the browser Web Speech API. Use Chrome or Edge. Mic access needs localhost or HTTPS.

## Project layout

```
backend/app/main.py                 FastAPI entry point
backend/app/api/                    auth, conversations, agent, documents, tools, analytics, admin
backend/app/agents/agent.py         agent loop: memory, RAG, tool calling
backend/app/tools/registry.py       validated tools with permission checks and logging
backend/app/services/rag/           extraction, chunking, embeddings, similarity search
backend/app/services/ai/            LLM provider abstraction
backend/app/models/entities.py      database tables
frontend/src/pages/                 Login, Dashboard, VoiceAgent, KnowledgeBase, Admin
```

## Status

Built: email/password auth, JWT with rotating refresh tokens, login lockout, OAuth (Google/GitHub/Microsoft) with safe account linking, roles, admin panel with audit log, conversations, agent, RAG, tools, voice, dashboard, Docker.

Next phases: Alembic migrations (tables are currently created on startup), email verification, password reset, magic link, phone OTP, 2FA, pgvector, streaming responses, frontend tests.
