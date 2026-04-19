"""
Builds structured prompts for the LLM. Keeps system and user prompts separate.
"""
from backend.services.log_parser import ParsedLog
from backend.services.log_classifier import ClassificationResult

SYSTEM_PROMPT = """You are a senior software engineer with 15+ years of experience debugging distributed systems, \
Java Spring Boot, microservices, Kafka, cloud environments (AWS/GCP/Azure), Python, and Node.js.

Your task is to analyze application logs or stack traces provided by the user.

You MUST respond with valid JSON only — no markdown fences, no prose outside the JSON.

The JSON schema is:
{
  "error_type": "<concise exception/error name>",
  "root_cause": "<precise single root cause, 1-3 sentences>",
  "explanation": "<detailed technical explanation of why this occurred, 3-6 sentences>",
  "fix_suggestions": ["<actionable fix 1>", "<actionable fix 2>", ...],
  "severity": "<one of: LOW | MEDIUM | HIGH | CRITICAL>",
  "confidence": <float 0.0-1.0>,
  "possible_causes": ["<cause 1>", "<cause 2>", ...]
}

Severity guide:
- CRITICAL: data loss, service completely down, security breach
- HIGH: service degraded, significant user impact, performance crisis
- MEDIUM: partial failure, non-critical feature broken
- LOW: warnings, minor issues, cosmetic errors

Rules:
1. Be precise and technical. Avoid generic advice.
2. fix_suggestions must be actionable — include config keys, code patterns, or CLI commands where possible.
3. possible_causes must be distinct; list the most likely first.
4. confidence reflects how certain you are given the information available (0.95 = very confident).
5. Never output anything outside the JSON object."""


def build_user_prompt(
    parsed: ParsedLog,
    classification: ClassificationResult,
    chunk: str,
    hint: str = "",
) -> str:
    parts = [f"Log type detected: {classification.log_type_label}"]

    if hint:
        parts.append(f"System hint from user: {hint}")

    if parsed.service_name:
        parts.append(f"Service/Module: {parsed.service_name}")

    if parsed.timestamp:
        parts.append(f"Timestamp: {parsed.timestamp}")

    if parsed.error_message:
        parts.append(f"\nError message:\n{parsed.error_message}")

    parts.append(f"\nLog content to analyze:\n---\n{chunk}\n---")

    if classification.detected_error_type:
        parts.append(f"\nPre-detected error pattern: {classification.detected_error_type}")

    return "\n".join(parts)
