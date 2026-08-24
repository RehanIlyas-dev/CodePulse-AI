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

## Run locally

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- PostgreSQL + Redis running locally (or use Docker Compose below)
- `LLM_API_KEY` from [opencode Zen](https://opencode.ai/zen)

```bash
git clone https://github.com/RehanIlyas-dev/CodePulse-AI && cd CodePulse-AI

# backend
cp backend/.env.example backend/.env        # fill in secrets
uv sync
cd backend && ../.venv/bin/uvicorn main:app --reload   # :8000, docs at /docs

# frontend (new terminal)
cd frontend && npm install && npm run dev   # :5173
```

### Full stack with Docker Compose

```bash
docker compose up --build     # db + redis + api (:8001) + web (:5174)
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
uv run pytest    # from repo root — ASGI in-process, real app lifespan, ~0.5s
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
│   ├── main.py                  # app factory, lifespan, Sentry init
│   ├── database.py              # async engine + session
│   ├── tests/                   # pytest suite
│   └── app/
│       ├── api/
│       │   ├── endpoints.py     # analyze / analyze-repo / jobs / ws / history
│       │   └── auth.py          # OAuth flow + refresh/logout/me
│       ├── core/                # redis, security (JWT), rate limiter,
│       │                        # guardrails, exception handlers
│       ├── models/              # User, CodeScan, RepoScan (SQLAlchemy)
│       ├── schemas/             # Pydantic v2 contracts
│       └── services/            # orchestrator, tree_sitter_engine, llm_engine,
│                                # project_parser, dependency_builder, workspace_manager,
│                                # cache_service, job_service, websocket_manager,
│                                # report_formatter
├── frontend/
│   └── src/
│       ├── App.jsx              # editor, repo input, live progress, routing
│       ├── api/client.js        # authed fetch + silent refresh
│       ├── api/websocket.js     # wss progress streaming
│       └── components/          # LoginScreen, ReportView, RepoReportView,
│                                # HistoryView, JobProgress, CodeEditor…
├── Dockerfile                   # backend image (uv + git)
├── docker-compose.yml           # postgres + redis + api + web
├── railway.toml                 # deploy config
└── .github/workflows/deploy.yml # CI: ruff + pytest (+ deploy hooks)
```

## License

Private project.

---

Made with ❤️ by [Rehan](https://github.com/RehanIlyas-dev)
