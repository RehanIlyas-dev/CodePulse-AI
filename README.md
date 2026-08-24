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
│   ├── main.py                          # FastAPI app, lifespan (DDL + Redis init), Sentry init
│   ├── database.py                      # async engine + session factory
│   ├── demo_test.py                     # manual end-to-end demo script
│   ├── tests/
│   │   ├── conftest.py                  # LifesManager fixture, SENTRY_DSN blanking
│   │   └── test_api.py                  # 7 API + DB round-trip tests
│   └── app/
│       ├── api/
│       │   ├── endpoints.py             # analyze / analyze-repo / jobs / ws / history endpoints
│       │   └── auth.py                  # OAuth2 login/callback/refresh/logout/me (Google + GitHub)
│       ├── core/
│       │   ├── security.py              # JWT issue/verify, bearer deps, ephemeral-secret fallback
│       │   ├── redis.py                 # async client; pings at startup, nulls on failure
│       │   ├── rate_limiter.py          # 10 req/min/IP sliding window (fails open)
│       │   ├── guardrails.py            # payload size caps, minified/zip checks
│       │   └── exceptions.py            # global handlers with CORS echo
│       ├── models/
│       │   ├── user.py                  # OAuth user model
│       │   ├── scan.py                  # CodeScan table (JSONB metrics/issues)
│       │   └── repo_scan.py             # RepoScan table (files + aggregate audit)
│       ├── schemas/
│       │   └── scan.py                  # Pydantic v2 request/response contracts
│       └── services/
│           ├── orchestrator.py          # code & repo pipelines (background tasks)
│           ├── tree_sitter_engine.py    # AST metrics for 18 languages
│           ├── project_parser.py        # repo file discovery (clone/zip → sources)
│           ├── dependency_builder.py    # import graph across repo files
│           ├── workspace_manager.py     # git clone / zip extract / cleanup
│           ├── llm_engine.py            # opencode Zen client, retries, JSON repair
│           ├── cache_service.py         # analysis/repo caches (SHA-keyed, TTL 24h)
│           ├── job_service.py           # job:<uuid> state in Redis (fail-soft)
│           ├── websocket_manager.py     # live progress broadcasting
│           └── report_formatter.py      # plain-text report builder
├── frontend/
│   ├── Dockerfile                       # node build → nginx static serve
│   ├── vercel.json                      # vite preset + SPA rewrites
│   ├── package.json
│   ├── vite.config.js                   # react + tailwind plugins
│   ├── index.html
│   ├── public/
│   │   └── favicon.svg                  # brand pulse mark
│   └── src/
│       ├── main.jsx                     # entry
│       ├── App.jsx                      # layout, editor, tabs, live status
│       ├── App.css
│       ├── index.css                    # Tailwind theme tokens (--color-brand-*)
│       ├── api/
│       │   ├── client.js                # authed fetch + silent refresh wrapper
│       │   └── websocket.js             # wss:// progress streaming
│       └── components/
│           ├── LoginScreen.jsx          # Google/GitHub sign-in
│           ├── CodeEditor.jsx           # snippet input
│           ├── RepoInput.jsx            # github url / zip upload
│           ├── JobProgress.jsx          # live progress bar
│           ├── ReportView.jsx           # code scan report
│           ├── RepoReportView.jsx       # per-file + project audit view
│           ├── HistoryView.jsx          # private scan history (tabs)
│           └── EmptyState.jsx           # empty placeholder
├── Dockerfile                           # backend image: uv sync + git
├── docker-compose.yml                   # postgres + redis + api (:8001) + web (:5174)
├── railway.toml                         # Railway deploy config (sh -c start command)
├── .github/
│   └── workflows/
│       └── deploy.yml                   # CI: uv sync → ruff → pytest (+ deploy hooks)
└── pyproject.toml                       # deps + uv.lock (repo-root managed)

### Author

Made with ❤️ by [Rehan](https://github.com/RehanIlyas-dev)
