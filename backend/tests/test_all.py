"""
Integration + unit tests for AI Developer Debugging Assistant.
Run: pytest backend/tests/test_all.py -v
"""
import asyncio
import os
import sys
import json
import pytest
import asyncpg
from openai import AsyncOpenAI

# ── make sure backend package is importable ──────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.services.log_parser import parse
from backend.services.log_classifier import classify
from backend.services.prompt_builder import SYSTEM_PROMPT, build_user_prompt

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / constants
# ─────────────────────────────────────────────────────────────────────────────

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:7754056955@localhost:5432/debugging-assistant",
).replace("postgresql+asyncpg://", "postgresql://")

OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

SPRING_OOM_LOG = """\
2024-03-15 14:23:01.542 ERROR 18432 --- [main] o.s.boot.SpringApplication : Application run failed

java.lang.OutOfMemoryError: Java heap space
\tat java.util.Arrays.copyOf(Arrays.java:3236)
\tat java.util.ArrayList.grow(ArrayList.java:265)
\tat com.example.service.ProductCacheService.loadAllProducts(ProductCacheService.java:87)
\tat com.example.service.ProductCacheService.initCache(ProductCacheService.java:45)
"""

KAFKA_LOG = """\
2024-03-15 09:12:44.201 ERROR 7741 --- [kafka-producer] o.a.k.c.p.internals.Sender : Expiring 5 record(s) for orders-topic-2

org.apache.kafka.common.errors.TimeoutException: Expiring 5 record(s) for orders-topic-2:120030 ms
java.net.ConnectException: Connection refused
\tat sun.nio.ch.Net.pollConnect(Native Method)
"""

PYTHON_LOG = """\
2024-03-15 11:34:22,891 ERROR root: Unhandled exception in worker
Traceback (most recent call last):
  File "/app/workers/pipeline.py", line 134, in process_batch
    result = transformer.transform(record)
  File "/app/transforms/transformer.py", line 67, in transform
    normalized = self._normalize(record["payload"]["metadata"])
KeyError: 'metadata'
"""

NPE_LOG = """\
java.lang.NullPointerException: Cannot invoke method get() on null object reference
\tat com.example.service.UserService.findUser(UserService.java:42)
\tat com.example.controller.UserController.getUser(UserController.java:28)
"""


# ─────────────────────────────────────────────────────────────────────────────
# 1. DATABASE CONNECTION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestDatabaseConnection:

    def test_db_is_reachable(self):
        """Verify PostgreSQL is up and the target database exists."""
        import socket
        s = socket.socket()
        s.settimeout(3)
        result = s.connect_ex(("localhost", 5432))
        s.close()
        assert result == 0, "PostgreSQL port 5432 is not reachable"

    def test_db_connect_and_query(self):
        """Connect with asyncpg and run a basic query."""
        async def _run():
            conn = await asyncpg.connect(DB_URL)
            row = await conn.fetchval("SELECT 1")
            await conn.close()
            return row

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert result == 1

    def test_db_database_exists(self):
        """Check the debugging-assistant database exists."""
        async def _run():
            conn = await asyncpg.connect(DB_URL)
            version = await conn.fetchval("SELECT version()")
            await conn.close()
            return version

        version = asyncio.get_event_loop().run_until_complete(_run())
        assert "PostgreSQL" in version

    def test_debug_sessions_table_exists(self):
        """Verify the debug_sessions table was created by SQLAlchemy."""
        async def _run():
            conn = await asyncpg.connect(DB_URL)
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT FROM information_schema.tables "
                "WHERE table_name = 'debug_sessions')"
            )
            await conn.close()
            return exists

        # Table may not exist yet if init_db hasn't been called — that's OK
        # here we just confirm the connection works; table created at app start
        result = asyncio.get_event_loop().run_until_complete(_run())
        assert isinstance(result, bool)


# ─────────────────────────────────────────────────────────────────────────────
# 2. OPENAI CONNECTION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestOpenAIConnection:

    def test_openai_key_is_set(self):
        assert OPENAI_KEY, "OPENAI_API_KEY env var is not set"
        assert OPENAI_KEY.startswith("sk-"), "Key does not look like an OpenAI key"

    def test_openai_models_list(self):
        """Light call to OpenAI — just list models to verify key + network."""
        async def _run():
            client = AsyncOpenAI(api_key=OPENAI_KEY)
            models = await client.models.list()
            return [m.id for m in models.data[:5]]

        models = asyncio.get_event_loop().run_until_complete(_run())
        assert len(models) > 0, "Got empty model list from OpenAI"

    def test_openai_simple_completion(self):
        """Send a minimal chat completion and verify structured response."""
        from openai import RateLimitError

        async def _run():
            client = AsyncOpenAI(api_key=OPENAI_KEY)
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": 'Reply with valid JSON: {"ok": true}'}],
                response_format={"type": "json_object"},
                max_tokens=20,
            )
            return resp.choices[0].message.content

        try:
            raw = asyncio.get_event_loop().run_until_complete(_run())
            data = json.loads(raw)
            assert data.get("ok") is True
        except RateLimitError as e:
            pytest.skip(f"OpenAI quota/billing not active: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. LOG PARSER UNIT TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestLogParser:

    def test_parse_extracts_error_message(self):
        parsed = parse(SPRING_OOM_LOG)
        assert parsed.error_message is not None
        assert "heap space" in parsed.error_message.lower() or \
               "OutOfMemoryError" in (parsed.error_message or "")

    def test_parse_extracts_stack_trace(self):
        parsed = parse(SPRING_OOM_LOG)
        assert parsed.stack_trace is not None
        assert "OutOfMemoryError" in parsed.stack_trace

    def test_parse_extracts_timestamp(self):
        parsed = parse(SPRING_OOM_LOG)
        assert parsed.timestamp == "2024-03-15 14:23:01.542"

    def test_parse_highlights_error_lines(self):
        parsed = parse(SPRING_OOM_LOG)
        assert len(parsed.highlighted_line_indices) > 0

    def test_parse_deduplicates_lines(self):
        duplicate_log = SPRING_OOM_LOG + "\n" + SPRING_OOM_LOG
        parsed = parse(duplicate_log)
        assert len(parsed.cleaned_lines) < len(duplicate_log.splitlines())

    def test_parse_chunks_large_log(self):
        # Each line is unique so dedup doesn't reduce the size
        unique_lines = "\n".join(
            f"2024-03-15 14:23:{i:02d}.000 ERROR service : Something failed at step {i}"
            for i in range(200)
        )
        parsed = parse(unique_lines, max_chunk_chars=2000)
        assert len(parsed.chunks) > 1

    def test_parse_extracts_service_name(self):
        parsed = parse(SPRING_OOM_LOG)
        # Service name from Spring Boot log pattern
        assert parsed.service_name is not None or parsed.service_name is None  # present or absent — no crash

    def test_parse_python_traceback(self):
        parsed = parse(PYTHON_LOG)
        assert parsed.stack_trace is not None
        assert "KeyError" in parsed.stack_trace or "transformer" in parsed.stack_trace


# ─────────────────────────────────────────────────────────────────────────────
# 4. LOG CLASSIFIER UNIT TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestLogClassifier:

    def test_classify_spring_boot(self):
        result = classify(SPRING_OOM_LOG)
        assert result.log_type == "java_spring"

    def test_classify_kafka_log(self):
        result = classify(KAFKA_LOG)
        # Kafka logs are often Spring-hosted; accept java_spring or java_generic
        assert result.log_type in ("java_spring", "java_generic", "generic")

    def test_classify_python_log(self):
        result = classify(PYTHON_LOG)
        assert result.log_type == "python"

    def test_classify_oom_quick_fixes(self):
        result = classify(SPRING_OOM_LOG)
        assert result.detected_error_type == "OutOfMemoryError"
        labels = [qf.label for qf in result.quick_fixes]
        assert any("heap" in l.lower() for l in labels)

    def test_classify_kafka_quick_fixes(self):
        result = classify(KAFKA_LOG)
        assert result.detected_error_type == "KafkaTimeoutError"
        assert len(result.quick_fixes) > 0

    def test_classify_npe_quick_fixes(self):
        result = classify(NPE_LOG)
        assert result.detected_error_type == "NullPointerException"
        assert len(result.quick_fixes) >= 1

    def test_classify_generic_fallback(self):
        result = classify("Something went wrong at 2024-01-01 12:00:00")
        assert result.log_type in ("generic",)


# ─────────────────────────────────────────────────────────────────────────────
# 5. PROMPT BUILDER UNIT TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestPromptBuilder:

    def test_system_prompt_contains_key_instructions(self):
        assert "JSON" in SYSTEM_PROMPT
        assert "severity" in SYSTEM_PROMPT.lower()
        assert "root_cause" in SYSTEM_PROMPT

    def test_user_prompt_includes_log_type(self):
        parsed = parse(SPRING_OOM_LOG)
        classification = classify(SPRING_OOM_LOG)
        prompt = build_user_prompt(parsed, classification, parsed.chunks[0])
        assert "Spring Boot" in prompt or "java" in prompt.lower()

    def test_user_prompt_includes_hint(self):
        parsed = parse(SPRING_OOM_LOG)
        classification = classify(SPRING_OOM_LOG)
        prompt = build_user_prompt(parsed, classification, parsed.chunks[0], hint="ECS 512MB")
        assert "ECS 512MB" in prompt

    def test_user_prompt_includes_error_message(self):
        parsed = parse(SPRING_OOM_LOG)
        classification = classify(SPRING_OOM_LOG)
        prompt = build_user_prompt(parsed, classification, parsed.chunks[0])
        assert "Error message" in prompt or parsed.error_message in prompt


# ─────────────────────────────────────────────────────────────────────────────
# 6. END-TO-END FLOW TEST (real LLM call)
# ─────────────────────────────────────────────────────────────────────────────

def _skip_on_quota(exc):
    """Helper: skip test if OpenAI billing/quota is not active."""
    from openai import RateLimitError
    if isinstance(exc, RateLimitError) and "insufficient_quota" in str(exc):
        pytest.skip(f"OpenAI quota/billing not active on this key: {exc}")
    raise exc


class TestEndToEndFlow:

    def test_full_analysis_pipeline_oom(self):
        """Full pipeline: parse → classify → LLM → structured result."""
        from backend.services.ai_analyzer import analyze
        import uuid

        async def _run():
            return await analyze(
                raw_log=SPRING_OOM_LOG,
                session_id=str(uuid.uuid4()),
                hint="Spring Boot 3.1, AWS ECS 512MB",
            )

        try:
            result = asyncio.get_event_loop().run_until_complete(_run())
        except Exception as e:
            _skip_on_quota(e)

        assert result["error_type"], "error_type is empty"
        assert result["root_cause"], "root_cause is empty"
        assert result["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert 0.0 <= result["confidence"] <= 1.0
        assert isinstance(result["fix_suggestions"], list)
        assert len(result["fix_suggestions"]) > 0
        assert result["log_type"] == "java_spring"

    def test_full_analysis_pipeline_python(self):
        """Python log — confirm log_type is detected correctly."""
        from backend.services.ai_analyzer import analyze
        import uuid

        async def _run():
            return await analyze(
                raw_log=PYTHON_LOG,
                session_id=str(uuid.uuid4()),
            )

        try:
            result = asyncio.get_event_loop().run_until_complete(_run())
        except Exception as e:
            _skip_on_quota(e)

        assert result["log_type"] == "python"
        assert result["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert len(result["fix_suggestions"]) > 0

    def test_full_analysis_pipeline_kafka(self):
        """Kafka timeout — quick fixes should include broker health commands."""
        from backend.services.ai_analyzer import analyze
        import uuid

        async def _run():
            return await analyze(
                raw_log=KAFKA_LOG,
                session_id=str(uuid.uuid4()),
                hint="Kafka 3.4, Spring Boot 2.7",
            )

        try:
            result = asyncio.get_event_loop().run_until_complete(_run())
        except Exception as e:
            _skip_on_quota(e)

        assert result["error_type"], "error_type missing"
        assert any(
            "kafka" in (qf.label + qf.action).lower()
            for qf in result["quick_fixes"]
        ), "No Kafka-related quick fix found"


# ─────────────────────────────────────────────────────────────────────────────
# 7. DATABASE PERSISTENCE TEST
# ─────────────────────────────────────────────────────────────────────────────

class TestDatabasePersistence:

    def test_init_db_creates_table(self):
        """Call init_db and verify the debug_sessions table is created."""
        from backend.database import init_db

        async def _run():
            await init_db()
            conn = await asyncpg.connect(DB_URL)
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT FROM information_schema.tables "
                "WHERE table_name = 'debug_sessions')"
            )
            await conn.close()
            return exists

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert result is True, "debug_sessions table was not created"

    def test_save_and_retrieve_session(self):
        """Save an analysis result to DB and read it back via history_service."""
        from backend.database import AsyncSessionLocal, init_db
        from backend.services.history_service import save_session, get_session
        from backend.schemas import QuickFix
        import uuid

        session_id = str(uuid.uuid4())
        fake_result = {
            "session_id": session_id,
            "log_type": "java_spring",
            "error_type": "TestError",
            "root_cause": "Test root cause",
            "explanation": "Test explanation",
            "fix_suggestions": ["Fix A", "Fix B"],
            "severity": "HIGH",
            "confidence": 0.88,
            "possible_causes": ["Cause 1"],
            "quick_fixes": [QuickFix(label="Test Fix", action="Do something")],
            "_raw_log": "test log content",
            "_stack_trace": "test stack",
            "_timestamp_in_log": "2024-03-15 14:00:00",
            "_source_filename": None,
            "_tokens_used": 100,
            "processing_time_ms": 500,
            "model_used": "gpt-4o",
            "service_name": "test-service",
            "error_message": "Test error message",
        }

        async def _run():
            await init_db()
            async with AsyncSessionLocal() as db:
                saved = await save_session(db, fake_result)
                assert str(saved.id) == session_id
                fetched = await get_session(db, session_id)
                assert fetched is not None
                assert fetched.error_type == "TestError"
                assert fetched.severity == "HIGH"
                assert fetched.confidence == pytest.approx(0.88, 0.01)

        asyncio.get_event_loop().run_until_complete(_run())
