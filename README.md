# CodePulse AI

AI-powered static code analysis API. Submit code in any language, get an instant structural analysis (tree-sitter) combined with an LLM-generated review — complexity, security & maintainability scores, flagged issues with fixes, and refactored code.

## Tech Stack

### Backend (implemented)

| Layer           | Technology                                                  |
| --------------- | ----------------------------------------------------------- |
| API framework   | FastAPI (async)                                             |
| ORM / database  | SQLAlchemy 2.0 (async) + PostgreSQL (asyncpg)               |
| Static analysis | tree-sitter + tree-sitter-language-pack (~180 languages)    |
| LLM             | Groq API —`openai/gpt-oss-120b` (structured JSON output) |
| Cache           | Redis (redis-py async)                                      |
| Validation      | Pydantic v2                                                 |

### Frontend (planned)

- **React** + **Tailwind CSS** — not started yet.

## Features

- **Multi-language static analysis** — syntax-tree metrics (lines, functions, cyclomatic complexity) with syntax-error detection before AI runs
- **LLM code review** — time/space complexity, security & maintainability scores (0–100), typed issues (security / performance / bug / style) with line numbers and fix suggestions, refactored code
- **Resilient AI layer** — 3 attempts with exponential backoff, 4xx fail-fast, invalid-JSON retry with prompt correction, 30s timeout, structured logging
- **Readable reports** — every scan stores a plain-text human-readable summary alongside structured JSON
- **REST API** — create, list (paginated), and fetch individual scans

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL running locally
- Redis running locally
- A Groq API key (https://console.groq.com)

### Setup

```bash
# 1. Clone & enter the repo
git clone <repo-url> && cd CodePulse-AI

# 2. Backend virtualenv + dependencies
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Environment variables (create .env in backend/)
GROQ_API_KEY=your_groq_key
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/codepulse
REDIS_URL=redis://localhost:6379/0
```

### Run

```bash
uvicorn main:app --reload
```

Server starts at http://127.0.0.1:8000 — interactive docs at http://127.0.0.1:8000/docs.

## API Reference

| Method | Endpoint                    | Description                                  |
| ------ | --------------------------- | -------------------------------------------- |
| GET    | `/`                       | Health check                                 |
| POST   | `/api/v1/analyze`         | Analyze code — returns & stores a full scan |
| GET    | `/api/v1/scans`           | List scans (paginated:`?limit=&offset=`)   |
| GET    | `/api/v1/scans/{scan_id}` | Fetch a single scan by UUID                  |

### Example: analyze code

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"title":"My scan","language":"python","code":"def add(a,b):\n    return a+b\n"}'
```

### Response (excerpt)

```json
{
  "id": "a31ea00f-5979-491a-9f11-cb8b1bea706e",
  "title": "My scan",
  "language": "python",
  "ast_metrics": { "total_lines": 2, "function_count": 1, "cyclomatic_complexity": 2, "has_syntax_errors": false },
  "time_complexity": "O(1)",
  "space_complexity": "O(1)",
  "security_score": 95,
  "maintainability_score": 90,
  "issues": [],
  "refactored_code": "def add(a, b):\n    return a + b",
  "summary_text": "CODE PULSE - CODE ANALYSIS REPORT\n..."
}
```

## Project Structure

```
CodePulse-AI/
├── backend/
│   ├── main.py                     # FastAPI app, CORS, lifespan (DB + Redis startup)
│   ├── database.py                 # Async engine, session factory, Base
│   ├── requirements.txt
│   └── app/
│       ├── api/endpoints.py        # /analyze, /scans, /scans/{id}
│       ├── core/redis.py           # Async Redis client
│       ├── models/scan.py          # CodeScan ORM model
│       ├── schemas/scan.py         # Pydantic request/response models
│       └── services/
│           ├── tree_sitter_engine.py   # Syntax-tree metrics (multi-language)
│           ├── llm_engine.py           # Groq call + retry/error handling
│           └── report_formatter.py     # Human-readable plain-text report
└── frontend/                       # React + Tailwind CSS (planned)
```

## Roadmap

- [X] Backend: analysis pipeline, persistence, retrieval, readable reports
- [X] Backend: multi-language static analysis (tree-sitter)
- [X] Backend: resilient LLM integration + Redis
- [ ] Frontend: React + Tailwind CSS UI
- [ ] Redis caching of LLM results (code-hash keyed)
- [ ] Rate limiting
- [ ] Auth (API keys / user accounts)

## License

Private project.
