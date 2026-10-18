from __future__ import annotations

import hashlib
import random
import struct
from typing import Optional, Sequence

from app.modules.deduplication.normalization import generate_shingles

# Standard Mersenne prime 2^61 - 1 used for 64-bit hashing
MERSENNE_PRIME = (1 << 61) - 1
MAX_HASH = MERSENNE_PRIME


class MinHashSignatureGenerator:
    """Deterministic MinHash signature generator using linear congruential hash permutations.

    Attributes:
        num_perm: Number of hash permutations (default 128 as specified in architecture).
        seed: Deterministic integer seed ensuring identical permutations across all instances.
    """

    def __init__(self, num_perm: int = 128, seed: int = 42) -> None:
        if num_perm <= 0:
            raise ValueError("num_perm must be a positive integer.")

        self.num_perm = num_perm
        self.seed = seed

        # Generate deterministic pseudo-random coefficients a and b
        rng = random.Random(seed)
        # a must be non-zero and odd (coprime to powers of 2)
        self._a: list[int] = [rng.randint(1, MERSENNE_PRIME - 1) | 1 for _ in range(num_perm)]
        self._b: list[int] = [rng.randint(0, MERSENNE_PRIME - 1) for _ in range(num_perm)]

    def compute_signature(self, shingles: Sequence[str]) -> list[int]:
        """Computes the MinHash signature vector (length = num_perm) for an iterable of shingles.

        Returns:
            list[int]: Vector of minimum hashed values across all permutations.
        """
        if not shingles:
            # Sentinel vector representing an empty set
            return [MAX_HASH] * self.num_perm

        # Unique shingles hashed to 64-bit integers once via SHA-256
        unique_shingles = set(shingles)
        shingle_hashes = [
            int.from_bytes(hashlib.sha256(s.encode("utf-8")).digest()[:8], "little")
            for s in unique_shingles
        ]

        sig = [MAX_HASH] * self.num_perm
        p = MERSENNE_PRIME
        a_coeffs = self._a
        b_coeffs = self._b

        for h in shingle_hashes:
            for i in range(self.num_perm):
                permuted = (a_coeffs[i] * h + b_coeffs[i]) % p
                if permuted < sig[i]:
                    sig[i] = permuted

        return sig

    def compute_hex_digest(self, signature: list[int]) -> str:
        """Derives a deterministic 64-character SHA-256 hexadecimal digest of the signature vector.

        Matches the schema contract minhash_signature_hex: str (length 64).
        """
        raw_bytes = struct.pack(f"<{len(signature)}Q", *signature)
        return hashlib.sha256(raw_bytes).hexdigest()

    def generate_from_text(self, text: str, k: int = 3) -> tuple[list[int], str]:
        """Convenience method: normalizes text, shingles into trigrams, and generates signature + hex digest.

        Returns:
            tuple[list[int], str]: (signature_vector, hex_digest)
        """
        shingles = generate_shingles(text, k=k)
        sig = self.compute_signature(shingles)
        hex_digest = self.compute_hex_digest(sig)
        return sig, hex_digest


# Module-level default generator singleton (num_perm=128, seed=42)
_DEFAULT_GENERATOR = MinHashSignatureGenerator(num_perm=128, seed=42)


def compute_minhash_signature(text: str, k: int = 3, num_perm: int = 128) -> tuple[list[int], str]:
    """Generates a 128-permutation MinHash signature and hex digest from text."""
    if num_perm == 128:
        return _DEFAULT_GENERATOR.generate_from_text(text, k=k)
    gen = MinHashSignatureGenerator(num_perm=num_perm, seed=42)
    return gen.generate_from_text(text, k=k)


def exact_jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Calculates the exact Jaccard similarity between two sets of shingles.

    J(A, B) = |A ∩ B| / |A ∪ B|
    """
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0

    intersection_len = len(set_a.intersection(set_b))
    union_len = len(set_a.union(set_b))

    if union_len == 0:
        return 1.0

    return float(intersection_len) / float(union_len)


def minhash_jaccard_similarity(sig_a: list[int], sig_b: list[int]) -> float:
    """Estimates Jaccard similarity from two MinHash signatures.

    J_hat(A, B) = (1 / N) * sum(I[sig_a[i] == sig_b[i]])
    """
    if len(sig_a) != len(sig_b):
        raise ValueError(f"Signatures must have identical lengths ({len(sig_a)} vs {len(sig_b)}).")

    if not sig_a:
        return 1.0

    # If both are empty sentinels
    all_sentinel_a = all(v == MAX_HASH for v in sig_a)
    all_sentinel_b = all(v == MAX_HASH for v in sig_b)
    if all_sentinel_a and all_sentinel_b:
        return 1.0
    if all_sentinel_a or all_sentinel_b:
        return 0.0

    matching = sum(1 for a, b in zip(sig_a, sig_b) if a == b)
    return float(matching) / float(len(sig_a))
