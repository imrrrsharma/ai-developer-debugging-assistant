# AI Developer Debugging Assistant

Production-ready web application that analyzes application logs, stack traces, and error messages using GPT-4 to deliver root cause analysis, fix suggestions, and severity classification.

---

## Project Structure

```
AI-Developer-Debugging-Assistant/
├── backend/
│   ├── main.py                  # FastAPI app entry point, lifespan, CORS, routing
│   ├── config.py                # Pydantic Settings (env-driven)
│   ├── database.py              # Async SQLAlchemy engine + session + init_db()
│   ├── models.py                # DebugSession ORM model (PostgreSQL)
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── requirements.txt
│   ├── Dockerfile
│   └── services/
│       ├── log_parser.py        # Noise removal, error block extraction, chunking
│       ├── log_classifier.py    # Log-type detection + known-error fingerprinting
│       ├── ai_analyzer.py       # OpenAI call, multi-chunk merge, response parsing
│       ├── prompt_builder.py    # System prompt + dynamic user prompt construction
│       └── history_service.py   # DB CRUD for DebugSession
│   └── routes/
│       ├── analyze.py           # POST /api/v1/analyze-log, POST /api/v1/upload-log
│       └── history.py           # GET /api/v1/history, GET /api/v1/history/{id}
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   ├── nginx.conf
│   ├── Dockerfile
│   └── src/
│       ├── main.jsx
│       ├── App.jsx              # Root: theme toggle, layout, state orchestration
│       ├── App.module.css       # CSS variables (light/dark), global layout
│       └── components/
│           ├── LogInput.jsx     # Textarea + drag-drop file upload
│           ├── LogInput.module.css
│           ├── AnalysisResult.jsx   # Full structured result display
│           ├── AnalysisResult.module.css
│           ├── HistoryPanel.jsx     # Paginated sidebar history
│           ├── HistoryPanel.module.css
│           └── SeverityBadge.jsx    # Color-coded severity pill
│       └── api/
│           └── client.js        # Typed fetch wrappers for all API endpoints
├── examples/
│   ├── spring_boot_oom.log
│   ├── kafka_timeout.log
│   ├── python_error.log
│   ├── db_connection.log
│   └── sample_api_request_response.json
├── docker-compose.yml
├── .env.example
└── CLAUDE.md
```

---

## Tech Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Backend    | Python 3.12, FastAPI, asyncio           |
| ORM        | SQLAlchemy 2.0 (async) + asyncpg        |
| Database   | PostgreSQL 16                           |
| Cache      | Redis 7 (optional)                      |
| LLM        | OpenAI GPT-4o via `openai` SDK v1.x     |
| Frontend   | React 18, Vite 6, CSS Modules           |
| Container  | Docker + docker-compose                 |

---

## API Endpoints

| Method | Path                         | Description                        |
|--------|------------------------------|------------------------------------|
| POST   | `/api/v1/analyze-log`        | Analyze pasted log text            |
| POST   | `/api/v1/upload-log`         | Upload a log file (multipart/form) |
| GET    | `/api/v1/history`            | Paginated history list             |
| GET    | `/api/v1/history/{id}`       | Full detail for a past session     |
| GET    | `/health`                    | Liveness probe                     |

---

## Local Development Setup

### 1. Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 running locally (or use Docker)
- OpenAI API key

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy and fill environment variables
cp ../.env.example ../.env

# Start the API server
cd ..
uvicorn backend.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev     # http://localhost:3000
```

### 4. Docker (full stack)

```bash
cp .env.example .env
# Edit .env: set OPENAI_API_KEY

docker-compose up --build
# Backend:  http://localhost:8000
# Frontend: http://localhost:3000
```

---

## Environment Variables

| Variable           | Required | Default         | Description                        |
|--------------------|----------|-----------------|------------------------------------|
| `OPENAI_API_KEY`   | Yes      | —               | OpenAI secret key                  |
| `OPENAI_MODEL`     | No       | `gpt-4o`        | Model name                         |
| `DATABASE_URL`     | Yes      | see .env.example| asyncpg connection string          |
| `REDIS_URL`        | No       | —               | Redis (optional caching)           |
| `DEBUG`            | No       | `false`         | Enable SQLAlchemy echo + debug logs|
| `MAX_LOG_SIZE_MB`  | No       | `10`            | Max upload size                    |

---

## Key Design Decisions

### Log Processing Pipeline

```
Raw log → log_parser.py → log_classifier.py → prompt_builder.py → ai_analyzer.py → DB
          (clean/chunk)    (type + patterns)   (system+user msg)   (LLM + merge)
```

1. **Noise removal** strips DEBUG/TRACE lines, blank lines, and JDK internal frames before sending to the LLM.
2. **Large log chunking** splits logs exceeding `MAX_CHUNK_TOKENS` and merges results (worst severity wins, suggestions unioned).
3. **Known error fingerprinting** in `log_classifier.py` adds instant quick-fix buttons without an LLM call for NullPointerException, OOM, Kafka timeout, DB connection issues, etc.
4. **`response_format: json_object`** is set on the OpenAI call so the model always returns parseable JSON — with a regex fallback extractor.

### Frontend Architecture

- **CSS Variables** in `App.module.css` drive the full light/dark theme with a single `data-theme` attribute on the root element.
- **CSS Modules** scope all styles; no third-party UI library dependency.
- **Vite proxy** forwards `/api` to the backend in dev so no CORS configuration is needed on the frontend side.
- History is refreshed automatically after each analysis by incrementing a `historyKey` state that forces HistoryPanel to remount.

---

## Detected Error Patterns (no LLM needed)

| Pattern                       | Quick Fixes Provided                              |
|-------------------------------|---------------------------------------------------|
| `NullPointerException`        | Null check, `-XX:+ShowCodeDetailsInExceptionMessages` |
| `OutOfMemoryError`            | Heap increase, GC logging, heap dump flags        |
| DB connection refused         | Config check, connectivity test CLI command       |
| Kafka `TimeoutException`      | `request.timeout.ms`, broker health check         |
| `StackOverflowError`          | Recursion inspection, `-Xss` flag                 |
| `ClassNotFoundException`      | Classpath check, rebuild artifact                 |
| Python `ModuleNotFoundError`  | `pip install`, venv activation                    |
| Node.js `ECONNREFUSED`        | URL check, curl test                              |
| `ConcurrentModificationException` | Iterator.remove(), CopyOnWriteArrayList      |

---

## Sample API Call

```bash
curl -X POST http://localhost:8000/api/v1/analyze-log \
  -H "Content-Type: application/json" \
  -d '{
    "log_content": "java.lang.OutOfMemoryError: Java heap space\n\tat java.util.ArrayList.grow(ArrayList.java:265)\n\tat com.example.service.ProductCacheService.loadAllProducts(ProductCacheService.java:87)",
    "hint": "Spring Boot 3.1, AWS ECS 512MB"
  }'
```

See [examples/sample_api_request_response.json](examples/sample_api_request_response.json) for a full response.
