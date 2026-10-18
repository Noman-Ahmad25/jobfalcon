"""Deterministic Core Integration Pipeline.

Coordinates ingestion validation, MinHash LSH deduplication, and deterministic
eligibility filtering for batches of opportunity listings.
"""

from app.modules.pipeline.service import run_deterministic_pipeline

__all__ = ["run_deterministic_pipeline"]
