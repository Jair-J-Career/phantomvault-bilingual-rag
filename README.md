# PhantomVault — Bilingual RAG

PhantomVault lets you upload a PDF and ask questions about it in English or Spanish. It answers back in whichever language you used. That's the core idea.

Under the hood there are two ways to query your document: a fast single-step RAG chain for simple questions, and a slower agentic pipeline that plans its own steps, detects your language, optionally translates the retrieved chunks, and then answers or summarizes depending on what you asked for.

---

## What it actually does

You drop a PDF in. The backend splits it into ~1000-character chunks, embeds them using Google's `gemini-embedding-001` model, and stores them in ChromaDB as an isolated collection tied to a session ID. That session ID gets sent back to the frontend, and from that point on every question you ask is scoped to that document only.

**Quick mode** runs a standard LangChain retrieval chain — retrieve the top 5 relevant chunks, stuff them into a prompt, call Gemini 2.5 Flash, done. Fast, but it doesn't do anything clever with language.

**Deep mode** uses a `PlannerAgent` that first asks Gemini to produce a JSON execution plan for your query, then runs each step in sequence:

1. `detect_language` — figures out whether you're asking in English, Spanish, or something else using a fast regex heuristic first, only falling back to an LLM call for ambiguous text
2. `retrieve` — similarity search against your document's ChromaDB collection
3. `translate_chunks` *(only if needed)* — if your query is in Spanish but the document is in English, the retrieved chunks get translated before the answer step
4. `answer` or `summarize` — generates the final response in your language

The frontend streams the agent steps in real time over SSE so you can watch the pipeline execute rather than staring at a spinner.

---

## Stack

| Layer | What |
|---|---|
| Backend | FastAPI + Uvicorn |
| LLM | Gemini 2.5 Flash (via `langchain-google-genai`) |
| Embeddings | `gemini-embedding-001` |
| Vector DB | ChromaDB (persistent, local) |
| Frontend | React 19 + Vite + Tailwind CSS |
| Infra | Docker Compose |

---

## Setup

### Prerequisites

- Python 3.11+
- Node 20+
- A Google AI Studio API key with access to Gemini models

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
GOOGLE_API_KEY=your_key_here
CHROMA_PERSIST_DIR=./chroma_data
UPLOAD_DIR=./temp_uploads
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
```

Start the server:

```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite proxy is not configured by default, so make sure your `VITE_API_BASE_URL` env var points to the backend if they're on different ports, or just leave it empty and the frontend will hit the same origin (works when proxied in Docker).

---

## Docker

The `docker-compose.yml` builds both services and connects them on an internal network. The frontend Nginx container waits for the backend health check to pass before accepting traffic.

```bash
# from the repo root
cp backend/.env.example backend/.env  # fill in your API key
docker compose up --build
```

The app will be at `http://localhost:80`.

Uploaded files and ChromaDB data are mounted as named volumes (`upload_data`, `chroma_data`) so they survive container restarts. Sessions older than 24 hours get cleaned up automatically on startup.

---

## Running tests

```bash
cd backend
pytest -v
```

The test suite covers:
- Upload validation (wrong content type, bad magic bytes, oversized files)
- Happy-path upload with mocked PDF loader and vector store
- `/ask` endpoint with a mocked RAG chain
- Agent endpoint (missing session → 404, sync run → full response)
- Language detector heuristics (English and Spanish)
- Planner fallback and plan validation

Tests use `httpx.AsyncClient` against the actual ASGI app with mocked external dependencies — no real Gemini calls, no real ChromaDB writes.

---

## Project structure

```
phantomvault-bilingual-rag/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── orchestrator.py     # PlannerAgent — plan + execute loop
│   │   │   ├── prompts/
│   │   │   │   └── planner.py      # system prompts for planner + answer
│   │   │   └── tools/
│   │   │       ├── language_detector.py
│   │   │       ├── retriever.py
│   │   │       ├── summarizer.py   # map-reduce summarization
│   │   │       └── translator.py
│   │   ├── api/
│   │   │   └── endpoints/
│   │   │       ├── agent.py        # POST /api/agent (sync + SSE)
│   │   │       ├── ask.py          # POST /api/ask (quick RAG)
│   │   │       ├── health.py       # GET /health, /ready
│   │   │       └── upload.py       # POST /api/upload
│   │   ├── services/
│   │   │   ├── cleanup.py
│   │   │   ├── document_processor.py
│   │   │   ├── embeddings.py
│   │   │   └── vector_store.py     # ChromaDB session manager
│   │   ├── config.py
│   │   ├── limiter.py
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── AgentSteps.jsx      # live step timeline
│       │   ├── MessageBubble.jsx
│       │   └── UploadPanel.jsx
│       ├── hooks/
│       │   └── useAgentStream.js   # fetch-based SSE hook
│       ├── services/
│       │   └── api.js
│       └── App.jsx
└── docker-compose.yml
```

---

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload a PDF, returns `session_id` |
| `POST` | `/api/ask` | Quick RAG question (requires `session_id`) |
| `POST` | `/api/agent` | Agentic query — set `stream: true` for SSE |
| `GET` | `/health` | Service health + Chroma status |
| `GET` | `/ready` | Readiness probe |

Rate limits: 5/min on upload, 20/min on `/ask`, 10/min on `/agent`.

### Upload response

```json
{
  "status": "File processed and memorized!",
  "session_id": "a3f92b...",
  "chunks": 47,
  "filename": "report.pdf"
}
```

### Agent request (streaming)

```json
{
  "session_id": "a3f92b...",
  "query": "¿Cuáles son las conclusiones?",
  "stream": true
}
```

SSE events look like:

```
data: {"type": "step", "tool": "detect_language", "output_summary": "Detected language: es", "latency_ms": 12, "status": "completed"}

data: {"type": "step", "tool": "retrieve", "output_summary": "Retrieved 5 chunks", "latency_ms": 88, "status": "completed"}

data: {"type": "step", "tool": "translate_chunks", "output_summary": "Translated 5 chunks to es", "latency_ms": 1204, "status": "completed"}

data: {"type": "step", "tool": "answer", "output_summary": "Las conclusiones principales son...", "latency_ms": 2341, "status": "completed"}

data: {"type": "done", "answer": "Las conclusiones principales son..."}
```

---

## Notes and known limitations

Sessions are in-memory for the singleton `VectorStoreManager`, but the ChromaDB collections are written to disk, so a server restart recovers existing sessions as long as the persist directory is intact. If you're running multiple backend workers, they won't share the in-memory singleton — either use a single worker or move to a shared ChromaDB server.

The language detector handles English, Spanish, Chinese, Arabic, and Russian. For anything else it falls back to a Gemini call. It's fast enough that it doesn't add meaningful latency for the common case.

PDFs with only scanned images won't work — PyPDF extracts text only, no OCR.

File cleanup runs at startup and removes uploads and ChromaDB collections older than 24 hours. There's no scheduled cleanup between restarts, so a long-running server will accumulate sessions until the next restart.
