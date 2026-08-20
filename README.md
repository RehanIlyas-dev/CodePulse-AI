# CodePulse AI

AI-powered static code analysis API. Submit code in any language, get an instant structural analysis (tree-sitter) combined with an LLM-generated review — complexity, security & maintainability scores, flagged issues with fixes, and refactored code.

## Tech Stack

### Backend (implemented)

| Layer           | Technology                                                  |
| --------------- | ----------------------------------------------------------- |
| API framework   | FastAPI (async)                                             |
| ORM / database  | SQLAlchemy 2.0 (async) + PostgreSQL (asyncpg)               |
| Static analysis | tree-sitter + tree-sitter-language-pack (~180 languages)    |
| LLM             | Groq API — `openai/gpt-oss-120b` (structured JSON output)   |
| Cache           | Redis (redis-py async)                                      |
| Validation      | Pydantic v2                                                 |
| Dependency mgmt | uv (pyproject.toml + uv.lock, venv at repo root)            |

### Frontend (planned)

- **React** + **Tailwind CSS** — not started yet.

## Features

- **Async job pipeline** — POST returns a `job_id` instantly (HTTP 202); analysis runs in a background task, progress streams live over WebSocket or via polling
- **Multi-language static analysis** — syntax-tree metrics (lines, functions, cyclomatic complexity) with syntax-error detection before AI runs
- **LLM code review** — time/space complexity, security & maintainability scores (0–100), typed issues (security / performance / bug / style) with line numbers and fix suggestions, refactored code
- **Resilient AI layer** — 3 attempts with exponential backoff, 4xx fail-fast, invalid-JSON retry with prompt correction, 30s timeout, structured logging
- **Result caching** — identical code+language short-circuits to `CACHE_HIT` (Redis, 24h TTL, no LLM call)
- **Readable reports** — every scan stores a plain-text human-readable summary alongside structured JSON
- **REST API** — create, list (paginated), fetch individual scans, poll job status

## Getting Started

### Prerequisites

- Python 3.14+ (uv manages it automatically)
- PostgreSQL running locally
- Redis running locally
- A Groq API key (https://console.groq.com)

### Setup

```bash
# 1. Install uv (dependency manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone & sync dependencies (creates .venv at repo root from pyproject.toml)
git clone <repo-url> && cd CodePulse-AI
uv sync

# 3. Environment variables (create backend/.env)
GROQ_API_KEY=your_groq_key
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/postgres
REDIS_URL=redis://localhost:6379/0
```

### Run

```bash
cd backend
../.venv/bin/uvicorn main:app --reload
```

Server starts at http://127.0.0.1:8000 — interactive docs at http://127.0.0.1:8000/docs.

## API Reference

| Method | Endpoint                    | Description                                     |
| ------ | --------------------------- | ----------------------------------------------- |
| GET    | `/`                         | Health check                                    |
| POST   | `/api/v1/analyze`           | Start analysis — returns `job_id` (HTTP 202)    |
| GET    | `/api/v1/jobs/{job_id}`     | Poll job status & result (Redis-backed)         |
| WS     | `/api/v1/ws/jobs/{job_id}`  | Live progress frames, then full result          |
| GET    | `/api/v1/scans`             | List scans (paginated: `?limit=&offset=`)       |
| GET    | `/api/v1/scans/{scan_id}`   | Fetch a single scan by UUID                     |

### Example: analyze code (async flow)

```bash
# 1. Submit — instant 202 with a job_id
curl -s -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"title":"My scan","language":"python","code":"def add(a,b):\n    return a+b\n"}'
# → {"job_id":"...","status":"PENDING","websocket_url":"/api/v1/ws/jobs/..."}

# 2. Poll until COMPLETED
curl -s http://127.0.0.1:8000/api/v1/jobs/<JOB_ID>
```

Or stream live via WebSocket (final frame carries the full result):

```python
import asyncio, json, websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:8000/api/v1/ws/jobs/<JOB_ID>") as ws:
        while True:
            m = json.loads(await ws.recv())
            print(f"{m['status']} {m['progress']}%")
            if m["status"] in ("COMPLETED", "CACHE_HIT", "FAILED"):
                break
asyncio.run(main())
```

### Result payload (from COMPLETED frame)

```json
{
  "id": "a31ea00f-5979-491a-9f11-cb8b1bea706e",
  "language": "python",
  "ast_metrics": { "total_lines": 2, "function_count": 1, "cyclomatic_complexity": 2, "has_syntax_errors": false },
  "time_complexity": "O(1)",
  "space_complexity": "O(1)",
  "security_score": 95,
  "maintainability_score": 90,
  "issues_list": [],
  "refactored_code": "def add(a, b):\n    return a + b",
  "summary_text": "CODE PULSE - CODE ANALYSIS REPORT\n...",
  "cached": false
}
```

## Project Structure

```
CodePulse-AI/
├── pyproject.toml               # uv project config (deps, python >=3.14)
├── uv.lock                      # locked, reproducible dependency versions
├── backend/
│   ├── main.py                  # FastAPI app, CORS, lifespan (DB + Redis startup)
│   ├── database.py              # Async engine, session factory, Base
│   └── app/
│       ├── api/endpoints.py     # /analyze, /jobs/{id}, ws/jobs/{id}, /scans
│       ├── core/redis.py        # Async Redis client
│       ├── models/scan.py       # CodeScan ORM model
│       ├── schemas/scan.py      # Pydantic request/response models
│       └── services/
│           ├── orchestrator.py      # Background analysis pipeline
│           ├── tree_sitter_engine.py   # Syntax-tree metrics (multi-language)
│           ├── llm_engine.py           # Groq call + retry/error handling
│           ├── cache_service.py        # analysis:<hash> Redis cache
│           ├── job_service.py          # job:<id> Redis state
│           ├── websocket_manager.py    # Live job progress broadcast
│           └── report_formatter.py     # Human-readable plain-text report
└── frontend/                    # React + Tailwind CSS (planned)
```

## Roadmap

- [X] Backend: analysis pipeline, persistence, retrieval, readable reports
- [X] Backend: multi-language static analysis (tree-sitter)
- [X] Backend: resilient LLM integration + Redis
- [X] Backend: async job pipeline (job_id + WebSocket progress)
- [X] Backend: Redis caching of LLM results (code-hash keyed)
- [ ] Frontend: React + Tailwind CSS UI
- [ ] Rate limiting
- [ ] Auth (API keys / user accounts)

## License

Private project.