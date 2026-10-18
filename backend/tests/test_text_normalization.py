from __future__ import annotations

import pytest

from app.modules.deduplication.normalization import (
    build_opportunity_comparison_text,
    generate_shingle_set,
    generate_shingles,
    normalize_opportunity_text,
)


def test_unicode_nfkc_normalization():
    """Verify that decomposed and composed Unicode representations normalize identically."""
    # Composed e with acute accent (\u00e9) vs decomposed e (\u0065) + combining acute (\u0301)
    composed = "Senior Software Engineer - Montr\u00e9al"
    decomposed = "Senior Software Engineer - Montr\u0065\u0301al"

    norm_composed = normalize_opportunity_text(composed)
    norm_decomposed = normalize_opportunity_text(decomposed)

    assert norm_composed == norm_decomposed
    assert "montréal" in norm_composed



def test_fullwidth_character_normalization():
    """Verify that fullwidth characters (e.g., from Asian keyboards) normalize to standard ASCII."""
    fullwidth = "Ｐｙｔｈｏｎ Ｂａｃｋｅｎｄ Ｅｎｇｉｎｅｅｒ"
    normalized = normalize_opportunity_text(fullwidth)
    assert normalized == "python backend engineer"


def test_zero_width_and_control_character_stripping():
    """Verify that zero-width smuggling characters and invisible control codes are stripped."""
    sneaky_text = "Senior\u200b Python\u200c Developer\ufeff"
    normalized = normalize_opportunity_text(sneaky_text)
    assert normalized == "senior python developer"
    assert "\u200b" not in normalized
    assert "\u200c" not in normalized
    assert "\ufeff" not in normalized


def test_punctuation_and_whitespace_normalization():
    """Verify punctuation is replaced with spaces (not concatenating words) and whitespace collapses."""
    raw = "FastAPI/Docker, Redis... \n\n\t Postgres & Python!"
    normalized = normalize_opportunity_text(raw)
    assert normalized == "fastapi docker redis postgres python"


def test_html_markup_stripping():
    """Verify that raw HTML tags from web scrapers are stripped cleanly."""
    html_text = "<p>Join our <strong>Engineering</strong> team!</p><br/><ul><li>Python</li></ul>"
    normalized = normalize_opportunity_text(html_text)
    assert "<" not in normalized
    assert ">" not in normalized
    assert normalized == "join our engineering team python"


def test_empty_and_none_text_normalization():
    """Empty strings and None should return empty string without raising exceptions."""
    assert normalize_opportunity_text("") == ""
    assert normalize_opportunity_text(None) == ""
    assert normalize_opportunity_text("   \n\t  ") == ""


def test_trigram_shingle_generation():
    """Verify correct 3-word n-gram shingle generation."""
    text = "Python FastAPI Docker Kubernetes"
    shingles = generate_shingles(text, k=3)
    assert shingles == [
        "python fastapi docker",
        "fastapi docker kubernetes",
    ]
    shingle_set = generate_shingle_set(text, k=3)
    assert len(shingle_set) == 2
    assert "python fastapi docker" in shingle_set


def test_short_text_shingling():
    """Texts with fewer than k words should produce a single shingle with all available words."""
    one_word = generate_shingles("Python", k=3)
    assert one_word == ["python"]

    two_words = generate_shingles("Backend Engineer", k=3)
    assert two_words == ["backend engineer"]


def test_empty_text_shingling():
    """Empty strings return empty shingle list and empty shingle set."""
    assert generate_shingles("", k=3) == []
    assert generate_shingle_set("", k=3) == set()


def test_build_opportunity_comparison_text_composite():
    """Composite comparison text combines title, company, and description."""
    comp_text = build_opportunity_comparison_text(
        title="Backend Engineer",
        company_name="Acme Corp",
        description_summary="Build high throughput APIs with FastAPI.",
    )
    assert comp_text == "backend engineer acme corp build high throughput apis with fastapi"
