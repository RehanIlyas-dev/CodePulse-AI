# CodePulse AI

AI-powered code analysis . Submit code or a whole GitHub repository / ZIP archive  and get an instant structural analysis (tree-sitter) combined with an LLM-generated review: complexity, security & maintainability scores, flagged issues with fixes, and refactored code. Analysis runs asynchronously with live progress over WebSocket.

## Tech Stack

### Backend (implemented)

| Layer           | Technology                                                          |
| --------------- | ------------------------------------------------------------------- |
| API framework   | FastAPI (async)                                                     |
| ORM / database  | SQLAlchemy 2.0 (async) + PostgreSQL (asyncpg)                       |
| Static analysis | tree-sitter + tree-sitter-language-pack (18 supported languages)    |
| LLM             | opencode Zen —`nemotron-3-ultra-free` (structured JSON output)   |
| Cache / jobs    | Redis (redis-py async)                                              |
| Validation      | Pydantic v2                                                         |
| Protection      | Rate limiter (Redis), payload guardrails, global exception handlers |
| Error tracking  | Sentry SDK (`sentry-sdk[fastapi]`)                                |
| Auth            | OAuth2 (Google + GitHub) via  JWT + httpOnly refresh               |
| Testing         | pytest + pytest-asyncio + httpx (ASGI in-process)                   |
| Dependency mgmt | uv (pyproject.toml + uv.lock, venv at repo root)                    |

### Frontend (implemented)

- **React** + **Tailwind CSS** + **Vite** — complete with login screen, history view, code editor, repository analyzer

## Features

- **Async jobs** — submit, get a `job_id` instantly (202), stream progress over WebSocket or poll
- **Multi-language analysis** — 18 languages; AST metrics (lines, functions, complexity) + LLM review (complexity, security & maintainability scores, issues with fixes, refactored code)
- **Repository analysis** — GitHub URL or `.zip` upload; per-file metrics + dependency graph + project audit; commit-aware caching so unchanged repos hit instantly
- **Authentication** — OAuth2 with Google & GitHub via opencode Zen; JWT access tokens (30 min) + httpOnly refresh cookies (30 days, rotated)
- **Per-user history** — signed-in users get private scan history; anonymous runs work but don't persist
- **Protection layer** — rate limiting (10 req/min/IP), size caps, minified-code detection, clean error shapes
- **WebSocket streaming** — live progress frames, then full result

## Getting Started

### Prerequisites

- Python 3.14+ (uv manages it automatically)
- PostgreSQL running locally (port 5432)
- Redis running locally (port 6379)
- opencode Zen API key (https://opencode.ai/zen)

### Setup

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

git clone <repo-url> && cd CodePulse-AI
uv sync

# backend/.env (create from template)
LLM_API_KEY=your_model_key
LLM_BASE_URL=https://opencode.ai/zen/v1
LLM_MODEL=nemotron-3-ultra-free
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/postgres
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=your_jwt_secret
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173,http://localhost:5174
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

### Run

```bash
cd backend
../.venv/bin/uvicorn main:app --reload
```

Server starts at http://127.0.0.1:8000 — interactive docs at http://127.0.0.1:8000/docs.

Frontend runs separately:

```bash
cd frontend
npm run dev   # runs on http://localhost:5173
```

### Test

```bash
uv run pytest    # from the repo root — 7 tests, ASGI in-process, ~0.5s
```

Covers health, guardrails (unsupported language / payload size), job 404s, DB round-trips for both scan tables, and the rate limiter (429 past 10 req/min). Tests run the app's real lifespan via `asgi-lifespan` and never touch the real Sentry dashboard.

## API Reference

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/` | Health check |
| POST | `/api/v1/analyze` | Analyze code snippet → `job_id` (202) |
| POST | `/api/v1/analyze-repo` | GitHub URL or `.zip` upload (multipart) |
| GET | `/api/v1/jobs/{job_id}` | Poll job status & result |
| WS | `/api/v1/ws/jobs/{job_id}?token=<jwt>` | Live progress → full result |
| GET | `/api/v1/scans` | List code scans (paginated) |
| GET | `/api/v1/scans/{scan_id}` | Fetch code scan by UUID |
| GET | `/api/v1/repo-scans` | List repo scans (paginated) |
| GET | `/api/v1/repo-scans/{scan_id}` | Fetch repo scan by UUID |

**Auth** (all `Authorization: Bearer <jwt>` unless noted):

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login/{provider}` | Start OAuth (google\|github) |
| GET | `/auth/callback/{provider}` | OAuth callback → 307 to `FRONTEND_URL/#token=...` |
| POST | `/auth/refresh` | Refresh access token (reads httpOnly cookie) |
| POST | `/auth/logout` | Clear refresh cookie |
| GET | `/auth/me` | Current user profile |

**Auth notes:** Rate-limited (10 req/min/IP) on POST `/analyze` & `/analyze-repo`; OAuth: Google, GitHub (via opencode Zen); JWT access 30 min; httpOnly refresh cookie 30 days (rotated); WebSocket: append `?token=<jwt>`.

## Project Structure

```
CodePulse-AI/
├── pyproject.toml       
├── uv.lock             
├── pytest.ini            
├── backend/
│   ├── main.py           
│   ├── database.py      
│   ├── demo_test.py        
│   ├── tests/
│   │   ├── conftest.py      
│   │   └── test_api.py      
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
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── api/client.js
│   │   ├── api/websocket.js
│   │   ├── components/
│   │   │   ├── CodeEditor.jsx
│   │   │   ├── RepoInput.jsx
│   │   │   ├── JobProgress.jsx
│   │   │   ├── ReportView.jsx
│   │   │   ├── RepoReportView.jsx
│   │   │   ├── LoginScreen.jsx
│   │   │   ├── HistoryView.jsx
│   │   │   └── EmptyState.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── pytest.ini
├── AGENTS.md
└── README.md
```

## Roadmap

- [X] Backend: analysis pipeline, persistence, retrieval, readable reports
- [X] Backend: multi-language static analysis (tree-sitter, 18 languages)
- [X] Backend: resilient LLM integration + Redis
- [X] Backend: async job pipeline (job_id + WebSocket progress)
- [X] Backend: Redis caching (code-hash + commit-aware repo caching)
- [X] Backend: repository analysis (GitHub URL / ZIP upload)
- [X] Backend: protection layer (rate limiting, guardrails, error handlers)
- [X] Backend: Sentry error tracking + pytest suite
- [X] Frontend: React + Tailwind CSS UI (login screen, history, editor, repo analyzer)
- [X] Auth (OAuth with Google/GitHub + JWT + httpOnly refresh cookies)
- [ ] CI/CD pipelines (GitHub Actions)
- [ ] Production deployment (Docker, Fly.io / Railway / Render)
- [ ] Sentry error tracking in production

## License

Private project.
