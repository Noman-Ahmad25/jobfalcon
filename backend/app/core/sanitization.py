import re
import unicodedata

INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior)\s+instructions|"
    r"system\s*prompt|you\s+are\s+now\s+in\s+developer\s+mode|"
    r"<script.*?>.*?</script>|<!--.*?-->)",
    re.IGNORECASE | re.DOTALL,
)


def sanitize_untrusted_text(value: str) -> str:
    """Normalizes Unicode via NFKC, strips zero-width smuggling characters,

    and neutralizes overt prompt injection directives.
    """
    if not value:
        return ""
    # Normalize Unicode to eliminate homoglyph and tag smuggling
    normalized = unicodedata.normalize("NFKC", value)
    # Remove invisible control characters (preserving standard whitespace)
    cleaned = "".join(
        ch for ch in normalized if unicodedata.category(ch)[0] != "C" or ch in ("\n", "\t", " ")
    )
    # Neutralize overt prompt-breakout directives by bracketing as inert literal text
    sanitized = INJECTION_PATTERNS.sub("[REDACTED_SUSPICIOUS_DIRECTIVE]", cleaned)
    return sanitized.strip()
