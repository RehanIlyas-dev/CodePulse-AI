# CodePulse-AI

**AI-powered code analysis platform** — submit a code snippet, a GitHub repository, or a ZIP archive and receive an instant structural analysis combined with an LLM-generated audit: complexity, security & maintainability scores, flagged issues with fixes, refactored code, and a readable report.

🔗 **Live:** [code-pulse-ai-eight.vercel.app](https://code-pulse-ai-eight.vercel.app) · [API docs](https://codepulse-ai-production.up.railway.app/docs)

---

## How it works

1. **Submit** — the API validates payload guardrails, parses AST metrics synchronously (tree-sitter), creates a job, returns `job_id` immediately.
2. **Analyze** — a background task runs the LLM audit (OpenAI-compatible gateway, structured JSON with regex fallback), persists the scan for signed-in users, and caches the result.
3. **Watch** — the frontend streams live progress over WebSocket (`PARSING_AST → RUNNING_AI_AUDIT → COMPLETED`), with HTTP polling as fallback.
4. **Reuse** — identical input hits a 24h cache; repositories are keyed by commit SHA, so unchanged repos return `CACHE_HIT` instantly at zero LLM cost.

## Tech stack

| Layer                        | Technology                                                                             |
| ---------------------------- | -------------------------------------------------------------------------------------- |
| Backend                      | FastAPI (async), Python 3.14, uv-managed deps                                          |
| Static analysis              | tree-sitter + tree-sitter-language-pack (18 languages)                                 |
| AI audit                     | opencode Zen gateway —`nemotron-3-ultra-free`, httpx client                         |
| Database                     | PostgreSQL (Supabase, asyncpg + SQLAlchemy 2.0)                                        |
| Cache / jobs / rate limiting | Redis (redis-py asyncio)                                                               |
| Auth                         | OAuth2 (Google + GitHub) → JWT access tokens + httpOnly rotating refresh cookies      |
| Error tracking               | Sentry (FastAPI/Starlette/asyncpg integrations)                                        |
| Frontend                     | React 19, Tailwind CSS 4, Vite, native WebSocket client                                |
| Testing                      | pytest + pytest-asyncio (ASGI in-process, real lifespan)                               |
| CI/CD                        | GitHub Actions (uv sync, ruff, pytest against Postgres+Redis services) → deploy hooks |

## Features

- **Async analysis jobs** — instant `202 + job_id`; live WebSocket progress or polling
- **18 languages** — Python, JS/TS, Rust, Go, Java, C#, C/C++, Ruby, PHP, Swift, Kotlin, Bash, Lua, Scala, Perl, R
- **Repository analysis** — GitHub URL (commit-SHA-aware caching) or ZIP upload (content-addressed caching); per-file audits ranked by complexity (max 20 files, concurrency-limited)
- **Per-user private history** — code scans & repo scans behind auth; anonymous runs work without persisting
- **Auth** — Google/GitHub OAuth, silent token refresh, protected profile endpoint
- **Protection layer** — Redis sliding-window rate limiting (10 req/min/IP), 500 KB snippet cap, minified-code detection, 10 MB zip cap, CORS allow-list, Sentry-backed error reporting that never leaks internals
- **Graceful degradation** — if Redis is down, caching/jobs/rate-limiting disable themselves; the API keeps serving

## The challenges this project solves

| Challenge | Solution |
|-----------|----------|
| **Static analyzers are precise but shallow; LLMs understand code but hallucinate metrics** | Hybrid engine — tree-sitter computes ground-truth AST facts, the LLM audits on top of measured reality |
| **Deep analysis takes 30–90s — too long for blocking HTTP** | Fully async pipeline: instant `202 + job_id`, live WebSocket progress, HTTP polling fallback |
| **LLMs return prose, not structured data** | Pydantic-validated JSON contracts + regex extraction + corrective-hint retries (3× backoff) |
| **Re-analyzing identical code wastes time and tokens** | Multi-layer caching: content-hash (snips), commit-SHA-aware (repos), content-addressed (ZIPs) → instant `CACHE_HIT` |
| **Hundreds of files can't fit a context window** | Complexity-ranked top-20 file selection, semaphore-limited concurrency (3), dependency graph for context |
| **History must be private per user** | OAuth JWTs + `user_id` scoping; anonymous use allowed without persistence |
| **Raw LLM output isn't actionable** | Deterministic reports: scores /100, prioritized fixes, refactored code |
| **Public AI endpoints get abused** | Rate limiting (10/min/IP), size caps, minified-code rejection, CORS allow-list, no internal leaks |

## Run locally

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- PostgreSQL + Redis running locally (or use Docker Compose below)
- `LLM_API_KEY` from [opencode Zen](https://opencode.ai/zen)

```bash
git clone https://github.com/RehanIlyas-dev/CodePulse-AI && cd CodePulse-AI

# backend
cp backend/.env.example backend/.env      
uv sync
cd backend && ../.venv/bin/uvicorn main:app --reload   

# frontend (new terminal)
cd frontend && npm install && npm run dev
```

### Full stack with Docker Compose

```bash
docker compose up --build
```

### Environment variables (`backend/.env`)

| Variable                                                 | Example                                         | Notes                                                   |
| -------------------------------------------------------- | ----------------------------------------------- | ------------------------------------------------------- |
| `DATABASE_URL`                                         | `postgresql+asyncpg://user:pass@host:5432/db` | `+asyncpg` driver required                            |
| `REDIS_URL`                                            | `redis://localhost:6379/0`                    | optional — degrades gracefully                         |
| `JWT_SECRET`                                           | `openssl rand -hex 32`                        | ephemeral random fallback if unset (warns)              |
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`       | opencode Zen creds                              | defaults baked in for base/model                        |
| `GOOGLE_CLIENT_ID/SECRET`, `GITHUB_CLIENT_ID/SECRET` | OAuth apps                                      | callback URIs under`/api/v1/auth/callback/{provider}` |
| `FRONTEND_URL`, `CORS_ORIGINS`, `API_PUBLIC_BASE`  | your origins                                    | comma-separated for multiple                            |
| `SENTRY_DSN`                                           | optional                                        | empty disables reporting                                |

## Testing

```bash
uv run pytest    # from repo root 
```

Covers health, guardrails, job 404s, DB round-trips for both scan tables, and rate limiting. Tests never touch real Sentry.

## Deployment

| Piece    | Platform                     | Notes                                                                        |
| -------- | ---------------------------- | ---------------------------------------------------------------------------- |
| Backend  | Railway (Dockerfile builder) | `railway.toml` sets the start command; image installs git for repo cloning |
| Frontend | Vercel                       | Root Directory =`frontend`; `VITE_API_URL` baked at build time           |
| Database | Supabase                     | use the**session pooler** host (IPv4) — direct hosts are IPv6-only    |

Pushes to `main` trigger GitHub Actions (lint + tests) and platform auto-deploys.

## Project structure

```
CodePulse-AI/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── demo_test.py
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_api.py
│   └── app/
│       ├── api/
│       │   ├── endpoints.py
│       │   └── auth.py
│       ├── core/
│       │   ├── security.py
│       │   ├── redis.py
│       │   ├── rate_limiter.py
│       │   ├── guardrails.py
│       │   └── exceptions.py
│       ├── models/
│       │   ├── user.py
│       │   ├── scan.py
│       │   └── repo_scan.py
│       ├── schemas/
│       │   └── scan.py
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
│   ├── Dockerfile
│   ├── vercel.json
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── public/
│   │   └── favicon.svg
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── App.css
│       ├── index.css
│       ├── api/
│       │   ├── client.js
│       │   └── websocket.js
│       └── components/
│           ├── LoginScreen.jsx
│           ├── CodeEditor.jsx
│           ├── RepoInput.jsx
│           ├── JobProgress.jsx
│           ├── ReportView.jsx
│           ├── RepoReportView.jsx
│           ├── HistoryView.jsx
│           └── EmptyState.jsx
├── Dockerfile
├── docker-compose.yml
├── railway.toml
├── .github/
│   └── workflows/
│       └── deploy.yml
└── pyproject.toml
```

### Author

Made with ❤️ by [Rehan](https://github.com/RehanIlyas-dev)
