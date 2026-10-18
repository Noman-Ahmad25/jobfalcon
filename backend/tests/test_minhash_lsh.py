from __future__ import annotations

import pytest

from app.modules.deduplication.lsh import MinHashLSHIndex
from app.modules.deduplication.minhash import (
    MinHashSignatureGenerator,
    compute_minhash_signature,
    exact_jaccard_similarity,
    minhash_jaccard_similarity,
)
from app.modules.deduplication.normalization import generate_shingle_set


def test_exact_jaccard_similarity_mathematics():
    """Verify exact Jaccard index calculation across edge cases."""
    # Disjoint sets
    set_a = {"apple", "banana", "cherry"}
    set_b = {"dog", "elephant", "fox"}
    assert exact_jaccard_similarity(set_a, set_b) == 0.0

    # Identical sets
    assert exact_jaccard_similarity(set_a, set_a) == 1.0

    # Partial overlap (2 in common, 4 total unique -> 2/4 = 0.5)
    set_c = {"banana", "cherry", "dragonfruit", "elderberry"}
    # intersection: {'banana', 'cherry'} (2)
    # union: {'apple', 'banana', 'cherry', 'dragonfruit', 'elderberry'} (5) -> 2/5 = 0.4
    assert exact_jaccard_similarity(set_a, set_c) == 0.4

    # Empty sets
    assert exact_jaccard_similarity(set(), set()) == 1.0
    assert exact_jaccard_similarity(set_a, set()) == 0.0


def test_minhash_signature_properties():
    """Verify that MinHash produces 128 integer permutations and a 64-char hex digest."""
    text = "We are seeking a senior Python engineer with experience in FastAPI and PostgreSQL."
    sig, hex_digest = compute_minhash_signature(text, k=3, num_perm=128)

    assert len(sig) == 128
    assert all(isinstance(v, int) for v in sig)
    assert len(hex_digest) == 64
    assert isinstance(hex_digest, str)


def test_minhash_repeatability_and_determinism():
    """Verify that 100 runs on identical text generate identical signature vectors and digests."""
    text = "Join our distributed platform team building scalable microservices with Python and Redis."
    base_sig, base_digest = compute_minhash_signature(text)

    for _ in range(100):
        sig, digest = compute_minhash_signature(text)
        assert sig == base_sig
        assert digest == base_digest


def test_minhash_identical_text_similarity():
    """Identical text descriptions must evaluate to 1.0 similarity."""
    text = "Senior Software Engineer, Core Infrastructure. Python, Docker, Kubernetes."
    sig_a, _ = compute_minhash_signature(text)
    sig_b, _ = compute_minhash_signature(text)

    sim = minhash_jaccard_similarity(sig_a, sig_b)
    assert sim == 1.0


def test_minhash_minor_wording_changes():
    """Syndicated postings with minor variations (e.g. disclaimer/footer) maintain high similarity >= 0.85."""
    body = (
        "Apex Systems is hiring a Backend Software Engineer to design, implement, and maintain scalable cloud services. "
        "In this role, you will work with cross-functional teams of frontend engineers, data scientists, and product managers "
        "to deliver high-performance microservices and RESTful APIs using Python, FastAPI, and PostgreSQL. "
        "Key Responsibilities include designing robust asynchronous REST APIs using FastAPI and Pydantic, "
        "optimizing database queries and schema migrations in PostgreSQL, and implementing automated testing with pytest. "
        "Qualifications: Bachelor degree in Computer Science or equivalent practical experience, 3+ years of professional "
        "software engineering experience with Python, and proven experience with relational databases and Redis caching."
    )
    posting_a = f"{body} Apply online via Lever applicant tracking system."
    posting_b = f"{body} Apply online via Greenhouse ATS career portal."

    sig_a, _ = compute_minhash_signature(posting_a)
    sig_b, _ = compute_minhash_signature(posting_b)

    sim = minhash_jaccard_similarity(sig_a, sig_b)
    assert sim >= 0.85, f"Expected similarity >= 0.85 for minor syndication variation, got {sim}"


def test_minhash_reordered_paragraphs():
    """Postings with reordered sections maintain high Jaccard similarity."""
    section_1 = (
        "Core Technical Requirements: Proficiency in Python 3.12+, FastAPI, and asynchronous concurrency. "
        "Experience with relational data modeling in PostgreSQL, containerization using Docker, and Git workflows."
    )
    section_2 = (
        "Primary Engineering Responsibilities: Architecting high-throughput data ingestion microservices, "
        "writing comprehensive unit and integration test suites using pytest, and participating in design reviews."
    )
    section_3 = (
        "Benefits and Compensation: Competitive annual salary, comprehensive health and dental coverage, "
        "401k employer match, and flexible remote-first working arrangements with home office stipends."
    )

    text_a = f"{section_1} {section_2} {section_3}"
    text_b = f"{section_3} {section_1} {section_2}"

    sig_a, _ = compute_minhash_signature(text_a)
    sig_b, _ = compute_minhash_signature(text_b)

    sim = minhash_jaccard_similarity(sig_a, sig_b)
    assert sim >= 0.85, f"Expected similarity >= 0.85 for reordered paragraphs, got {sim}"



def test_minhash_unrelated_listings():
    """Unrelated job descriptions exhibit very low similarity (<= 0.15)."""
    text_python = (
        "Senior Backend Engineer building distributed event-driven microservices with Python, Kafka, "
        "Docker, and Kubernetes. Strong knowledge of data structures and distributed systems required."
    )
    text_marketing = (
        "Content Marketing Specialist responsible for social media campaigns, SEO copywriting, "
        "and brand storytelling. Bachelor's degree in Journalism or Communications required."
    )

    sig_py, _ = compute_minhash_signature(text_python)
    sig_mkt, _ = compute_minhash_signature(text_marketing)

    sim = minhash_jaccard_similarity(sig_py, sig_mkt)
    assert sim <= 0.15, f"Expected low similarity for unrelated roles, got {sim}"


def test_minhash_estimate_vs_exact_jaccard_convergence():
    """MinHash estimated Jaccard similarity converges within statistical bounds of exact Jaccard."""
    text_a = "Senior Software Engineer Python FastAPI PostgreSQL Docker Kubernetes Cloud Microservices"
    text_b = "Junior Software Engineer Python Django PostgreSQL Docker AWS Microservices"

    shingles_a = generate_shingle_set(text_a, k=3)
    shingles_b = generate_shingle_set(text_b, k=3)
    exact_j = exact_jaccard_similarity(shingles_a, shingles_b)

    sig_a, _ = compute_minhash_signature(text_a)
    sig_b, _ = compute_minhash_signature(text_b)
    est_j = minhash_jaccard_similarity(sig_a, sig_b)

    # For K=128, standard error is sqrt(J*(1-J)/128) <= 0.045; bound within 0.10
    assert abs(est_j - exact_j) <= 0.10, f"MinHash estimate {est_j} deviated too far from exact {exact_j}"


def test_lsh_index_insert_and_query():
    """Verify that MinHashLSHIndex retrieves near-duplicate candidates meeting the threshold."""
    lsh = MinHashLSHIndex(threshold=0.85, num_perm=128, num_bands=16)

    job_original = (
        "Software Engineer at Acme Corp. Build web services using Python, FastAPI, and Postgres. "
        "Experience with Docker and Linux server administration required."
    )
    job_duplicate = (
        "Software Engineer at Acme Corp. Build web services using Python, FastAPI, and Postgres. "
        "Experience with Docker and Linux server administration required. Apply on Ashby."
    )
    job_unrelated = (
        "Account Executive at Global Sales Inc. Close enterprise software contracts and maintain CRM."
    )

    sig_orig, _ = compute_minhash_signature(job_original)
    sig_dup, _ = compute_minhash_signature(job_duplicate)
    sig_unrel, _ = compute_minhash_signature(job_unrelated)

    lsh.insert("job-001", sig_orig)
    lsh.insert("job-unrelated", sig_unrel)

    # Query with duplicate
    matches = lsh.query(sig_dup)
    assert len(matches) == 1
    matched_id, similarity = matches[0]
    assert matched_id == "job-001"
    assert similarity >= 0.85

    # Query with unrelated listing returns empty
    unrelated_matches = lsh.query(sig_unrel)
    # job-unrelated matches itself (1.0)
    assert any(m[0] == "job-unrelated" for m in unrelated_matches)
    assert not any(m[0] == "job-001" for m in unrelated_matches)


def test_lsh_index_removal():
    """Verify key removal removes entries from LSH index."""
    lsh = MinHashLSHIndex(threshold=0.85, num_perm=128, num_bands=16)
    sig, _ = compute_minhash_signature("Test job listing")

    lsh.insert("job-temp", sig)
    assert len(lsh) == 1
    assert "job-temp" in lsh

    lsh.remove("job-temp")
    assert len(lsh) == 0
    assert "job-temp" not in lsh
    assert lsh.query(sig) == []
