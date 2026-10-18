from __future__ import annotations

import re
import unicodedata
from typing import Optional

# Strip HTML tags
HTML_TAG_PATTERN = re.compile(r"<[^>]+>", re.DOTALL)
# Match non-alphanumeric and non-whitespace characters (punctuation, symbols)
NON_ALPHANUMERIC_PATTERN = re.compile(r"[^\w\s]", re.UNICODE)
# Match consecutive whitespace characters
WHITESPACE_PATTERN = re.compile(r"\s+", re.UNICODE)


def normalize_opportunity_text(text: Optional[str]) -> str:
    """Consistently normalizes text for shingling and MinHash signature generation.

    Performs:
    1. Unicode NFKC normalization (decomposes homoglyphs and normalizes accents).
    2. Removal of invisible control characters (except standard whitespace).
    3. Stripping of raw HTML / script markup.
    4. Lowercase conversion.
    5. Replacement of punctuation/symbols with spaces (preventing word concatenation).
    6. Whitespace collapsing and trimming.
    """
    if not text:
        return ""

    # 1. Unicode NFKC normalization
    normalized = unicodedata.normalize("NFKC", text)

    # 2. Strip invisible control characters (Category 'C' except standard whitespace)
    clean_chars = "".join(
        ch for ch in normalized
        if unicodedata.category(ch)[0] != "C" or ch in ("\n", "\t", " ")
    )

    # 3. Strip HTML markup
    no_html = HTML_TAG_PATTERN.sub(" ", clean_chars)

    # 4. Lowercase
    lowered = no_html.lower()

    # 5. Punctuation & symbols to spaces
    no_punct = NON_ALPHANUMERIC_PATTERN.sub(" ", lowered)

    # 6. Collapse multiple whitespace and trim
    collapsed = WHITESPACE_PATTERN.sub(" ", no_punct).strip()

    return collapsed


def build_opportunity_comparison_text(
    title: Optional[str],
    company_name: Optional[str],
    description_summary: Optional[str],
) -> str:
    """Constructs a composite normalized text string for opportunity deduplication.

    Avoids relying on title alone by combining title, company, and description.
    """
    parts = []
    if title:
        parts.append(title)
    if company_name:
        parts.append(company_name)
    if description_summary:
        parts.append(description_summary)

    combined = " ".join(parts)
    return normalize_opportunity_text(combined)


def generate_shingles(text: str, k: int = 3) -> list[str]:
    """Generates word-level n-gram shingles (default trigrams, k=3) from normalized text.

    Args:
        text: Normalized or raw text string.
        k: Shingle length in words (default 3 for trigram shingles).

    Returns:
        list[str]: Sequential list of word n-grams.
            - If text has 0 words: returns []
            - If text has between 1 and k-1 words: returns single shingle with all available words.
            - If text has >= k words: returns rolling n-grams of length k.
    """
    clean_text = normalize_opportunity_text(text)
    if not clean_text:
        return []

    words = clean_text.split()
    word_count = len(words)

    if word_count == 0:
        return []

    if word_count < k:
        return [" ".join(words)]

    return [" ".join(words[i : i + k]) for i in range(word_count - k + 1)]


def generate_shingle_set(text: str, k: int = 3) -> set[str]:
    """Generates a distinct set of word-level n-gram shingles."""
    return set(generate_shingles(text, k=k))
