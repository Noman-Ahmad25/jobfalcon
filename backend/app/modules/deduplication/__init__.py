"""Deterministic Near-Duplicate Opportunity Detection Subsystem.

Combines Unicode normalization, word trigram shingling, 128-permutation MinHash
signatures, and Locality-Sensitive Hashing (LSH) for sub-linear syndicated listing detection.
"""

from app.modules.deduplication.lsh import MinHashLSHIndex
from app.modules.deduplication.minhash import (
    MinHashSignatureGenerator,
    compute_minhash_signature,
    exact_jaccard_similarity,
    minhash_jaccard_similarity,
)
from app.modules.deduplication.normalization import (
    build_opportunity_comparison_text,
    generate_shingle_set,
    generate_shingles,
    normalize_opportunity_text,
)
from app.modules.deduplication.service import (
    DeduplicationService,
    deduplicate_opportunities,
)

__all__ = [
    # Normalization & Shingling
    "normalize_opportunity_text",
    "build_opportunity_comparison_text",
    "generate_shingles",
    "generate_shingle_set",
    # MinHash
    "MinHashSignatureGenerator",
    "compute_minhash_signature",
    "exact_jaccard_similarity",
    "minhash_jaccard_similarity",
    # LSH
    "MinHashLSHIndex",
    # Service
    "DeduplicationService",
    "deduplicate_opportunities",
]
