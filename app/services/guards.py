"""
Input validation and prompt-injection guard for RAGDocs.
Called at the top of every /chat/query and /chat/stream handler.
"""
import re

INJECTION_PATTERNS = [
    r'ignore\s+(previous|all|above)\s+(instructions|prompts)',
    r'system\s*[:：]',
    r'<\s*\|?\s*(system|admin|user)\s*\|?\s*>',
    r'disregard\s+the\s+(above|previous)',
    r'you\s+are\s+now\s+a',
    r'forget\s+(everything|all)',
    r'new\s+instructions?\s*[:：]',
    r'act\s+as\s+(if|a)\s',
    r'jailbreak',
    r'prompt\s+injection',
    r'override\s+(your\s+)?(instructions|training|guidelines)',
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

MAX_QUERY_LENGTH = 2000


def validate_query(query: str) -> tuple[bool, str]:
    """Return (is_safe, reason). reason is empty string when safe."""
    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Query too long ({len(query)} chars; max {MAX_QUERY_LENGTH})"
    for pattern in _COMPILED:
        if pattern.search(query):
            return False, "Query contains patterns associated with prompt injection"
    return True, ""
