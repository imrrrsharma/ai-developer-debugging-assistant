"""
Parses raw log text: removes noise, extracts error blocks, deduplicates, chunks large inputs.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# Patterns that are noise (progress bars, debug heartbeats, etc.)
_NOISE_PATTERNS = [
    re.compile(r"^\s*$"),                                         # blank lines
    re.compile(r"^\s*#{2,}.*#{2,}\s*$"),                         # banner separators
    re.compile(r"^\d{4}-\d{2}-\d{2}.*\bDEBUG\b.*$"),            # debug-level lines
    re.compile(r"^\d{4}-\d{2}-\d{2}.*\bTRACE\b.*$"),            # trace-level lines
    re.compile(r"^\s*at sun\.reflect\."),                         # JDK internal frames
    re.compile(r"^\s*at com\.sun\.proxy"),                        # proxy frames
    re.compile(r"^\s*\.\.\. \d+ more\s*$"),                      # "... 5 more" truncation markers
]

# Lines that indicate the start of an error block
_ERROR_START_PATTERNS = [
    re.compile(r"\b(ERROR|FATAL|CRITICAL|Exception|Error|Traceback|WARN)\b"),
    re.compile(r"^\s+at [\w\.$]+\("),     # Java stack frame
    re.compile(r"^  File \".*\", line \d+"),  # Python traceback frame
]

# Timestamp pattern (ISO-ish)
_TIMESTAMP_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
)

# Service/logger name from common log formats
_SERVICE_RE = re.compile(
    r"(?:\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[^ ]*)\s+\w+\s+[\d]+\s+---\s+\[([^\]]+)\]|"  # Spring
    r"\((\w[\w.-]*)\)\s+\w+:|"                                                                   # Node/Python named logger
    r"logger=(['\"]?[\w.]+['\"]?)"
)

# Error message extraction
_ERROR_MSG_RE = re.compile(
    r"(?:Exception|Error):\s*(.+?)(?:\n|$)|"
    r"FATAL[:\s]+(.+?)(?:\n|$)|"
    r"Caused by:\s*[\w.]+:\s*(.+?)(?:\n|$)"
)


@dataclass
class ParsedLog:
    raw: str
    cleaned_lines: List[str]
    error_blocks: List[str]
    error_message: Optional[str]
    stack_trace: Optional[str]
    service_name: Optional[str]
    timestamp: Optional[str]
    highlighted_line_indices: List[int]   # indices into cleaned_lines
    chunks: List[str] = field(default_factory=list)


def parse(raw_log: str, max_chunk_chars: int = 12_000) -> ParsedLog:
    lines = raw_log.splitlines()
    cleaned, highlighted = _clean_lines(lines)
    error_blocks = _extract_error_blocks(cleaned)
    error_message = _extract_error_message(raw_log)
    stack_trace = _extract_stack_trace(raw_log)
    service_name = _extract_service(raw_log)
    timestamp = _extract_timestamp(raw_log)

    relevant_text = "\n".join(error_blocks) if error_blocks else "\n".join(cleaned)
    chunks = _chunk(relevant_text, max_chunk_chars)

    return ParsedLog(
        raw=raw_log,
        cleaned_lines=cleaned,
        error_blocks=error_blocks,
        error_message=error_message,
        stack_trace=stack_trace,
        service_name=service_name,
        timestamp=timestamp,
        highlighted_line_indices=highlighted,
        chunks=chunks,
    )


def _clean_lines(lines: List[str]) -> Tuple[List[str], List[int]]:
    seen: set = set()
    cleaned: List[str] = []
    highlighted: List[int] = []

    for line in lines:
        if any(p.search(line) for p in _NOISE_PATTERNS):
            continue
        normalized = line.rstrip()
        if normalized in seen:
            continue
        seen.add(normalized)
        idx = len(cleaned)
        cleaned.append(normalized)
        if any(p.search(normalized) for p in _ERROR_START_PATTERNS):
            highlighted.append(idx)

    return cleaned, highlighted


def _extract_error_blocks(lines: List[str]) -> List[str]:
    """Return contiguous blocks that contain or follow an error marker."""
    blocks: List[str] = []
    current: List[str] = []
    in_block = False

    for line in lines:
        is_error = any(p.search(line) for p in _ERROR_START_PATTERNS)
        is_frame = bool(re.match(r"^\s+(at |File |Caused by:)", line))

        if is_error:
            in_block = True
            current.append(line)
        elif in_block and (is_frame or line.startswith(" ")):
            current.append(line)
        else:
            if current:
                blocks.append("\n".join(current))
                current = []
            in_block = False

    if current:
        blocks.append("\n".join(current))

    return blocks


def _extract_error_message(text: str) -> Optional[str]:
    m = _ERROR_MSG_RE.search(text)
    if not m:
        return None
    return next((g for g in m.groups() if g), None)


def _extract_stack_trace(text: str) -> Optional[str]:
    # Grab from the first "Exception/Error/Traceback" to the end of its block
    patterns = [
        re.compile(r"((?:Traceback \(most recent call last\):.*?)(?=\n\n|\Z))", re.DOTALL),
        re.compile(r"((?:[\w.]+(?:Exception|Error):.*?)(?=\n\n|\Z))", re.DOTALL),
    ]
    for p in patterns:
        m = p.search(text)
        if m:
            return m.group(1).strip()
    return None


def _extract_timestamp(text: str) -> Optional[str]:
    m = _TIMESTAMP_RE.search(text)
    return m.group(1) if m else None


def _extract_service(text: str) -> Optional[str]:
    m = _SERVICE_RE.search(text)
    if not m:
        return None
    return next((g.strip("'\"") for g in m.groups() if g), None)


def _chunk(text: str, max_chars: int) -> List[str]:
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    lines = text.splitlines(keepends=True)
    current = ""
    for line in lines:
        if len(current) + len(line) > max_chars and current:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks
