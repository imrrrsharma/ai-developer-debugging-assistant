"""
Sends prompt to OpenAI and parses the structured JSON response.
"""
import json
import logging
import time
from typing import Any, Dict, Optional

from openai import AsyncOpenAI

from backend.config import settings
from backend.services.log_parser import ParsedLog, parse
from backend.services.log_classifier import classify, ClassificationResult
from backend.services.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from backend.schemas import AnalysisResponse, QuickFix

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        kwargs = {"api_key": settings.OPENAI_API_KEY}
        if settings.LLM_BASE_URL:
            kwargs["base_url"] = settings.LLM_BASE_URL
        _client = AsyncOpenAI(**kwargs)
    return _client


_SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


async def analyze(
    raw_log: str,
    session_id: str,
    hint: str = "",
    source_filename: Optional[str] = None,
) -> Dict[str, Any]:
    t0 = time.monotonic()

    parsed: ParsedLog = parse(raw_log)
    classification: ClassificationResult = classify(raw_log)

    # Analyze each chunk; merge results (worst severity wins, suggestions concatenated)
    all_results: list[Dict] = []
    total_tokens = 0

    for chunk in parsed.chunks:
        user_prompt = build_user_prompt(parsed, classification, chunk, hint)
        result, tokens = await _call_llm(user_prompt)
        all_results.append(result)
        total_tokens += tokens

    merged = _merge_results(all_results)

    # Supplement quick_fixes from classifier (well-known patterns)
    classifier_qf = [qf.model_dump() for qf in classification.quick_fixes]
    # Deduplicate by label
    existing_labels = {q["label"] for q in merged.get("quick_fixes", [])}
    for qf in classifier_qf:
        if qf["label"] not in existing_labels:
            merged.setdefault("quick_fixes", []).append(qf)
            existing_labels.add(qf["label"])

    processing_ms = int((time.monotonic() - t0) * 1000)

    return {
        "session_id": session_id,
        "log_type": classification.log_type,
        "error_type": merged.get("error_type", "UnknownError"),
        "root_cause": merged.get("root_cause", ""),
        "explanation": merged.get("explanation", ""),
        "fix_suggestions": merged.get("fix_suggestions", []),
        "severity": merged.get("severity", "MEDIUM"),
        "confidence": float(merged.get("confidence", 0.5)),
        "possible_causes": merged.get("possible_causes", []),
        "quick_fixes": [QuickFix(**q) for q in merged.get("quick_fixes", [])],
        "highlighted_lines": parsed.highlighted_line_indices,
        "service_name": parsed.service_name,
        "error_message": parsed.error_message,
        "processing_time_ms": processing_ms,
        "model_used": settings.OPENAI_MODEL,
        # Internal fields for DB storage
        "_tokens_used": total_tokens,
        "_stack_trace": parsed.stack_trace,
        "_timestamp_in_log": parsed.timestamp,
        "_raw_log": raw_log,
        "_source_filename": source_filename,
    }


async def _call_llm(user_prompt: str) -> tuple[Dict, int]:
    client = _get_client()
    try:
        create_kwargs = dict(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=settings.OPENAI_TEMPERATURE,
        )
        if settings.LLM_JSON_MODE:
            create_kwargs["response_format"] = {"type": "json_object"}
        response = await client.chat.completions.create(**create_kwargs)
        raw = response.choices[0].message.content or "{}"
        tokens = response.usage.total_tokens if response.usage else 0
        return _safe_parse(raw), tokens
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return _fallback_result(str(exc)), 0


def _safe_parse(raw: str) -> Dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON object from the response
        import re
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    return _fallback_result("Failed to parse LLM response")


def _fallback_result(reason: str) -> Dict:
    return {
        "error_type": "AnalysisError",
        "root_cause": f"Could not complete analysis: {reason}",
        "explanation": "The AI analysis step encountered an error. Please check your API key and try again.",
        "fix_suggestions": ["Check OPENAI_API_KEY environment variable", "Retry with a smaller log snippet"],
        "severity": "MEDIUM",
        "confidence": 0.0,
        "possible_causes": [reason],
        "quick_fixes": [],
    }


def _merge_results(results: list[Dict]) -> Dict:
    if not results:
        return _fallback_result("No chunks to analyze")
    if len(results) == 1:
        return results[0]

    # Worst severity wins
    merged = results[0].copy()
    for r in results[1:]:
        r_sev = _SEVERITY_ORDER.get(r.get("severity", "MEDIUM"), 1)
        m_sev = _SEVERITY_ORDER.get(merged.get("severity", "MEDIUM"), 1)
        if r_sev > m_sev:
            merged["severity"] = r["severity"]
            merged["root_cause"] = r["root_cause"]
            merged["explanation"] = r["explanation"]

        # Union suggestions
        existing = set(merged.get("fix_suggestions", []))
        for s in r.get("fix_suggestions", []):
            if s not in existing:
                merged.setdefault("fix_suggestions", []).append(s)
                existing.add(s)

        existing_causes = set(merged.get("possible_causes", []))
        for c in r.get("possible_causes", []):
            if c not in existing_causes:
                merged.setdefault("possible_causes", []).append(c)
                existing_causes.add(c)

        # Average confidence
        merged["confidence"] = (
            (merged.get("confidence", 0.5) + r.get("confidence", 0.5)) / 2
        )

    return merged
