from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Sequence

from app.modules.deduplication.minhash import compute_minhash_signature
from app.modules.ingestion.adapter import BaseOpportunityAdapter
from app.schemas.opportunity import PolymorphicOpportunity


class JSONFixtureOpportunityAdapter(BaseOpportunityAdapter):
    """Adapter for reading structured career opportunity fixtures from local JSON files.

    Useful for air-gapped testing, offline demonstrations, and reproducible integration tests.
    """

    def __init__(
        self,
        fixture_path: Optional[str | Path] = None,
        source_name: str = "json_fixture",
    ) -> None:
        self._source_name = source_name
        if fixture_path is None:
            # Default to backend/app/data/fixtures/sample_opportunities.json
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.fixture_path = base_dir / "data" / "fixtures" / "sample_opportunities.json"
        else:
            self.fixture_path = Path(fixture_path)

    @property
    def source_name(self) -> str:
        return self._source_name

    def fetch_opportunities(self) -> Sequence[PolymorphicOpportunity]:
        if not self.fixture_path.exists():
            raise FileNotFoundError(f"Fixture file not found at: {self.fixture_path}")

        with open(self.fixture_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        if not isinstance(raw_data, list):
            raise ValueError(f"Expected a JSON list of opportunities, got {type(raw_data).__name__}")

        opportunities: list[PolymorphicOpportunity] = []
        for item in raw_data:
            # Ensure minhash_signature_hex is present; compute deterministically if missing
            if not item.get("minhash_signature_hex"):
                summary_text = item.get("sanitized_summary", "")
                _, hex_digest = compute_minhash_signature(summary_text)
                item["minhash_signature_hex"] = hex_digest

            opp = PolymorphicOpportunity.model_validate(item)
            opportunities.append(opp)

        return opportunities
