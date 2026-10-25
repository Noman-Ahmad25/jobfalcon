"""Evidence-grounded explanation and career gap analysis module."""

from app.modules.explanation.explainer import OpportunityExplanationEngine
from app.modules.explanation.gap_analyzer import CareerGapAnalysisService

__all__ = [
    "OpportunityExplanationEngine",
    "CareerGapAnalysisService",
]
