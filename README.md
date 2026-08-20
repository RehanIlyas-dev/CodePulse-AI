# CodePulse AI

AI-powered  code analysis API. Submit code — or a whole GitHub repository / ZIP archive — and get an instant structural analysis (tree-sitter) combined with an LLM-generated review: complexity, security & maintainability scores, flagged issues with fixes, and refactored code. Analysis runs asynchronously with live progress over WebSocket.

## Tech Stack

### Backend (implemented)

| Layer                 | Technology                                                          |
| --------------------- | ------------------------------------------------------------------- |
| API framework         | FastAPI (async)                                                     |
| ORM / database        | SQLAlchemy 2.0 (async) + PostgreSQL (asyncpg)                       |
| Static analysis       | tree-sitter + tree-sitter-language-pack (22 supported languages)    |
| LLM                   | Groq API —`openai/gpt-oss-120b` (structured JSON output)         |
| Cache / jobs          | Redis (redis-py async)                                              |
| Validation            | Pydantic v2                                                         |
| Protection            | Rate limiter (Redis), payload guardrails, global exception handlers |
| Dependency management | uv (pyproject.toml + uv.lock, venv at repo root)                    |

### Frontend (planned)

- **React** + **Tailwind CSS** — not started yet (planned on a separate branch).

## Features

- **Async jobs** — submit, get a `job_id` instantly (202), stream progress over WebSocket or poll
- **Multi-language analysis** — 22 languages; AST metrics (lines, functions, complexity) + LLM review (complexity, security & maintainability scores, issues with fixes, refactored code)
- **Repository analysis** — GitHub URL or `.zip` upload; per-file metrics + dependency graph + project audit; commit-aware caching so unchanged repos hit instantly
- **Protection layer** — rate limiting (10 req/min/IP), size caps, minified-code detection, clean error shapes

## Getting Started

### Prerequisites

- Python 3.14+ (uv manages it automatically)
- PostgreSQL running locally (port 5432)
- Redis running locally (port 6379)
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

| Method | Endpoint                         | Description                                            |
| ------ | -------------------------------- | ------------------------------------------------------ |
| GET    | `/`                            | Health check                                           |
| POST   | `/api/v1/analyze`              | Analyze a code snippet — returns`job_id` (HTTP 202) |
| POST   | `/api/v1/analyze-repo`         | Analyze a GitHub URL or`.zip` upload (multipart)     |
| GET    | `/api/v1/jobs/{job_id}`        | Poll job status & result (Redis-backed)                |
| WS     | `/api/v1/ws/jobs/{job_id}`     | Live progress frames, then full result                 |
| GET    | `/api/v1/scans`                | List code scans (paginated:`?limit=&offset=`)        |
| GET    | `/api/v1/scans/{scan_id}`      | Fetch a single code scan by UUID                       |
| GET    | `/api/v1/repo-scans`           | List repo scans (paginated)                            |
| GET    | `/api/v1/repo-scans/{scan_id}` | Fetch a single repo scan by UUID                       |

Both POST endpoints are rate-limited (10 requests/minute/IP) and validated by payload guardrails.

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

### Example: analyze a repository

```bash
# By GitHub URL (cached per commit SHA — same commit = instant CACHE_HIT)
curl -s -X POST http://127.0.0.1:8000/api/v1/analyze-repo \
  -F "github_url=https://github.com/RehanIlyas-dev/insta-daemon"

# By ZIP upload
curl -s -X POST http://127.0.0.1:8000/api/v1/analyze-repo \
  -F "file=@/path/to/project.zip"
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

Repo scan jobs return `{files: {...}, summary: {...}}` plus a full-project `summary_text`.

## Project Structure

```
CodePulse-AI/
├── pyproject.toml           
├── uv.lock                 
├── backend/
│   ├── main.py               
│   ├── database.py          
│   └── app/
│       ├── api/endpoints.py   
│       ├── core/
│       │   ├── redis.py      
│       │   ├── exceptions.py  
│       │   ├── rate_limiter.py  
│       │   └── guardrails.py   
│       ├── models/scan.py    
│       ├── models/repo_scan.py 
│       ├── schemas/scan.py    
│       └── services/
│           ├── orchestrator.py     
│           ├── tree_sitter_engine.py 
│           ├── project_parser.py   
│           ├── dependency_builder.py 
│           ├── workspace_manager.py 
│           ├── llm_engine.py       
│           ├── cache_service.py   
│           ├── job_service.py     
│           ├── websocket_manager.py  
│           └── report_formatter.py   
└── frontend/
```

## Roadmap

- [X] Backend: analysis pipeline, persistence, retrieval, readable reports
- [X] Backend: multi-language static analysis (tree-sitter, 22 languages)
- [X] Backend: resilient LLM integration + Redis
- [X] Backend: async job pipeline (job_id + WebSocket progress)
- [X] Backend: Redis caching (code-hash + commit-aware repo caching)
- [X] Backend: repository analysis (GitHub URL / ZIP upload)
- [X] Backend: protection layer (rate limiting, guardrails, error handlers)
- [ ] Frontend: React + Tailwind CSS UI
- [ ] Auth (OAuth with Google/GitHub + JWT)

## License

Private project.
