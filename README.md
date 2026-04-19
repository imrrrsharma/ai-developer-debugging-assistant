# 🐛 AI Developer Debugging Assistant

> Paste your logs. Get the root cause, fix suggestions, and severity — instantly.

A production-ready web application that analyzes application logs, stack traces, and error messages using **GPT-4o**. Built for real-world enterprise systems: Spring Boot, Kafka, microservices, Python pipelines, and Node.js services.

![Tech Stack](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/Frontend-React_18-61DAFB?style=flat-square&logo=react)
![OpenAI](https://img.shields.io/badge/LLM-GPT--4o-412991?style=flat-square&logo=openai)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-4169E1?style=flat-square&logo=postgresql)

---

## What It Does

Upload or paste any application log and get back a structured analysis:

| Field | Description |
|---|---|
| **Error Type** | Classified exception or error name |
| **Root Cause** | Precise single cause of the failure |
| **Explanation** | Technical breakdown of why it happened |
| **Fix Suggestions** | Ordered, actionable remediation steps |
| **Severity** | `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |
| **Confidence** | How certain the model is (0–100%) |
| **Quick Fixes** | One-click buttons with copyable commands |

### Supported Log Formats

- **Java Spring Boot** — HikariCP, Tomcat, Spring context errors
- **Java Generic** — any JVM stack trace
- **Node.js** — V8 stack traces, `ECONNREFUSED`, module errors
- **Python** — Traceback, `KeyError`, `ImportError`, pipeline failures
- **Generic** — any structured or unstructured log

### Instant Pattern Detection (no LLM needed)

`NullPointerException` · `OutOfMemoryError` · Kafka `TimeoutException` · DB connection failures · `StackOverflowError` · `ClassNotFoundException` · Python `ModuleNotFoundError` · Node.js `ECONNREFUSED` · `ConcurrentModificationException`

---

## Tech Stack

```
Backend   →  Python 3.12, FastAPI, SQLAlchemy 2.0 (async), asyncpg
Database  →  PostgreSQL 16
LLM       →  OpenAI GPT-4o (openai SDK v1.x)
Cache     →  Redis 7 (optional)
Frontend  →  React 18, Vite 6, CSS Modules (zero UI library deps)
Container →  Docker + docker-compose
```

---

## Project Structure

```
AI-Developer-Debugging-Assistant/
├── backend/
│   ├── main.py                  # FastAPI app, CORS, lifespan hooks
│   ├── config.py                # Env-driven settings (pydantic-settings)
│   ├── database.py              # Async engine + session factory
│   ├── models.py                # DebugSession ORM model
│   ├── schemas.py               # Request / response Pydantic schemas
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── services/
│   │   ├── log_parser.py        # Noise removal, dedup, chunking, extraction
│   │   ├── log_classifier.py    # Log-type detection + 9 error fingerprints
│   │   ├── ai_analyzer.py       # OpenAI call, multi-chunk merge logic
│   │   ├── prompt_builder.py    # System + dynamic user prompt construction
│   │   └── history_service.py   # DB CRUD for past sessions
│   └── routes/
│       ├── analyze.py           # POST /analyze-log  POST /upload-log
│       └── history.py           # GET /history  GET /history/{id}
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Root — state, theme, orchestration
│   │   ├── App.module.css       # CSS variables, light/dark theme
│   │   ├── api/client.js        # Typed fetch wrappers
│   │   └── components/
│   │       ├── LogInput         # Textarea + drag-and-drop file upload
│   │       ├── AnalysisResult   # Full result display with collapsible sections
│   │       ├── HistoryPanel     # Paginated sidebar session list
│   │       └── SeverityBadge    # Color-coded severity pill
│   ├── vite.config.js
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
├── examples/                    # Sample logs for testing
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Getting Started

### Prerequisites

- [Docker & docker-compose](https://docs.docker.com/get-docker/) — easiest path
- **Or** Python 3.12+ and Node.js 20+ for local dev
- OpenAI API key → [platform.openai.com](https://platform.openai.com/)

---

### Option 1 — Docker (Recommended)

```bash
# 1. Clone the repo
git clone https://github.com/imrrrsharma/ai-developer-debugging-assistant.git
cd ai-developer-debugging-assistant

# 2. Set up environment
cp .env.example .env
# Open .env and set your OPENAI_API_KEY

# 3. Start everything
docker-compose up --build
```

| Service  | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

### Option 2 — Local Development

#### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example ../.env
# Edit .env — set OPENAI_API_KEY and DATABASE_URL

# Start PostgreSQL (if not using Docker)
# Make sure PostgreSQL is running on localhost:5432

# Run the API server
cd ..
uvicorn backend.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend

npm install
npm run dev
# → http://localhost:3000
```

> The Vite dev server proxies `/api` to `http://localhost:8000` automatically — no CORS issues.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```env
# Required
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/debugassistant

# Optional — defaults shown
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=4096
OPENAI_TEMPERATURE=0.2
MAX_LOG_SIZE_MB=10
DEBUG=false

# Optional — Redis caching
# REDIS_URL=redis://localhost:6379/0
```

---

## API Reference

### `POST /api/v1/analyze-log`

Analyze pasted log text.

**Request**
```json
{
  "log_content": "java.lang.OutOfMemoryError: Java heap space\n\tat ...",
  "hint": "Spring Boot 3.1, AWS ECS 512MB"
}
```

**Response**
```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "log_type": "java_spring",
  "error_type": "OutOfMemoryError",
  "root_cause": "The JVM heap ran out of memory while loading the entire product catalog...",
  "explanation": "ProductCacheService attempts to load all products into memory...",
  "fix_suggestions": [
    "Implement lazy/paginated cache loading: load products in batches of 500",
    "Increase the ECS task memory to at least 2 GB and set -Xmx1536m"
  ],
  "severity": "CRITICAL",
  "confidence": 0.93,
  "possible_causes": ["Unbounded ArrayList loading on startup", "ECS memory limit too low"],
  "quick_fixes": [
    { "label": "Increase heap size", "action": "...", "command": "-Xmx4g -Xms1g" }
  ],
  "highlighted_lines": [0, 2, 3],
  "processing_time_ms": 2341,
  "model_used": "gpt-4o"
}
```

### `POST /api/v1/upload-log`

Upload a `.log` / `.txt` file (multipart/form-data). Max size: `MAX_LOG_SIZE_MB` (default 10 MB).

```bash
curl -X POST http://localhost:8000/api/v1/upload-log \
  -F "file=@examples/spring_boot_oom.log" \
  -F "hint=Spring Boot 3.1"
```

### `GET /api/v1/history?page=1&page_size=20`

Returns paginated list of past analysis sessions.

### `GET /api/v1/history/{session_id}`

Returns full detail (including raw log) for a specific session.

---

## Testing with Example Logs

The `examples/` directory contains ready-to-use test logs:

| File | Scenario |
|---|---|
| `spring_boot_oom.log` | Java OutOfMemoryError during startup |
| `kafka_timeout.log` | Kafka producer timeout + broker unreachable |
| `python_error.log` | Python KeyError + Redis connection failure |
| `db_connection.log` | HikariPool PostgreSQL auth failure |

```bash
# Test via curl
curl -X POST http://localhost:8000/api/v1/analyze-log \
  -H "Content-Type: application/json" \
  -d "{\"log_content\": \"$(cat examples/spring_boot_oom.log | tr '\n' ' ')\"}"
```

---

## How It Works

```
Raw Log
   │
   ▼
log_parser.py
  ├─ Remove noise (DEBUG/TRACE lines, blank lines, JDK internal frames)
  ├─ Deduplicate identical lines
  ├─ Extract: error message, stack trace, timestamp, service name
  └─ Chunk large logs (>12,000 chars) for LLM token limits
   │
   ▼
log_classifier.py
  ├─ Detect log type (Spring Boot / Node.js / Python / Generic)
  └─ Fingerprint known errors → instant quick-fix buttons
   │
   ▼
prompt_builder.py
  └─ Build system prompt + dynamic user prompt with extracted context
   │
   ▼
ai_analyzer.py (GPT-4o)
  ├─ Call LLM with response_format: json_object
  ├─ Merge multi-chunk results (worst severity wins, suggestions unioned)
  └─ Fallback parser if JSON extraction fails
   │
   ▼
Structured JSON Response → Saved to PostgreSQL → Returned to UI
```

---

## License

MIT
