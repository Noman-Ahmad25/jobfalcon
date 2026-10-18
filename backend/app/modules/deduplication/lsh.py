from __future__ import annotations

import hashlib
import struct
from collections import defaultdict
from typing import Any, Optional

from app.modules.deduplication.minhash import minhash_jaccard_similarity


class MinHashLSHIndex:
    """Locality-Sensitive Hashing (LSH) index for sub-linear near-duplicate candidate retrieval.

    Divides a 128-permutation MinHash signature into b bands of r rows each (b * r = 128).
    Candidate collisions are harvested across band buckets, then verified against the
    provisional Jaccard similarity threshold (default 0.85).

    Attributes:
        threshold: Provisional Jaccard similarity threshold (default 0.85).
        num_perm: Number of permutations in MinHash signature (default 128).
        num_bands: Number of bands b (default 16, resulting in r = 8 rows per band).
    """

    def __init__(
        self,
        threshold: float = 0.85,
        num_perm: int = 128,
        num_bands: int = 16,
    ) -> None:
        if not (0.0 <= threshold <= 1.0):
            raise ValueError("Threshold must be between 0.0 and 1.0.")
        if num_perm % num_bands != 0:
            raise ValueError(f"num_perm ({num_perm}) must be evenly divisible by num_bands ({num_bands}).")

        self.threshold = threshold
        self.num_perm = num_perm
        self.num_bands = num_bands
        self.rows_per_band = num_perm // num_bands

        # Hash tables: list of dicts, one table per band: table[band_idx][bucket_hash] = set of keys
        self._hash_tables: list[dict[str, set[str]]] = [
            defaultdict(set) for _ in range(self.num_bands)
        ]
        # Registry of stored signatures: key -> signature vector
        self._signatures: dict[str, list[int]] = {}
        # Optional metadata registry
        self._metadata: dict[str, dict[str, Any]] = {}

    def insert(
        self,
        key: str,
        signature: list[int],
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Inserts a key and its MinHash signature into the LSH index."""
        if len(signature) != self.num_perm:
            raise ValueError(f"Signature length ({len(signature)}) does not match num_perm ({self.num_perm}).")

        if key in self._signatures:
            self.remove(key)

        self._signatures[key] = signature
        if metadata:
            self._metadata[key] = metadata

        r = self.rows_per_band
        for band_idx in range(self.num_bands):
            band_slice = signature[band_idx * r : (band_idx + 1) * r]
            bucket_hash = self._hash_band(band_slice)
            self._hash_tables[band_idx][bucket_hash].add(key)

    def query(
        self,
        signature: list[int],
        min_similarity: Optional[float] = None,
    ) -> list[tuple[str, float]]:
        """Queries the index for near-duplicate candidates.

        Returns:
            list[tuple[str, float]]: List of (key, estimated_jaccard_similarity) sorted descending.
        """
        if len(signature) != self.num_perm:
            raise ValueError(f"Signature length ({len(signature)}) does not match num_perm ({self.num_perm}).")

        target_threshold = self.threshold if min_similarity is None else min_similarity
        r = self.rows_per_band

        # 1. Harvest candidate keys across all bands
        candidate_keys: set[str] = set()
        for band_idx in range(self.num_bands):
            band_slice = signature[band_idx * r : (band_idx + 1) * r]
            bucket_hash = self._hash_band(band_slice)
            bucket = self._hash_tables[band_idx].get(bucket_hash)
            if bucket:
                candidate_keys.update(bucket)

        # 2. Verify candidate keys against target threshold
        matches: list[tuple[str, float]] = []
        for cand_key in candidate_keys:
            cand_sig = self._signatures[cand_key]
            sim = minhash_jaccard_similarity(signature, cand_sig)
            if sim >= target_threshold:
                matches.append((cand_key, sim))

        # Sort matches by similarity score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def remove(self, key: str) -> None:
        """Removes a key from the LSH index."""
        if key not in self._signatures:
            return

        signature = self._signatures.pop(key)
        self._metadata.pop(key, None)

        r = self.rows_per_band
        for band_idx in range(self.num_bands):
            band_slice = signature[band_idx * r : (band_idx + 1) * r]
            bucket_hash = self._hash_band(band_slice)
            table = self._hash_tables[band_idx]
            if bucket_hash in table:
                table[bucket_hash].discard(key)
                if not table[bucket_hash]:
                    del table[bucket_hash]

    def has_key(self, key: str) -> bool:
        """Checks if a key exists in the index."""
        return key in self._signatures

    def get_signature(self, key: str) -> Optional[list[int]]:
        """Retrieves the stored signature for a key."""
        return self._signatures.get(key)

    def __contains__(self, key: str) -> bool:
        return key in self._signatures

    def __len__(self) -> int:
        return len(self._signatures)

    def _hash_band(self, band_slice: list[int]) -> str:
        """Computes a deterministic bucket hash for a band slice."""
        packed = struct.pack(f"<{len(band_slice)}Q", *band_slice)
        return hashlib.sha256(packed).hexdigest()
