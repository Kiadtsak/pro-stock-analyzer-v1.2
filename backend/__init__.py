"""
Pro Stock Analyzer — Professional financial ratio analysis system.

18 categories, 200+ formulas, bilingual output.
"""
__version__ = "1.0.0"

from backend.engine import (
    AnalysisEngine,
    AnalysisResult,
    YearResult,
    analyze_financials,
)
from backend.loader import (
    list_available_symbols,
    load_financials,
    validate_data,
)
from backend.ratios import CATEGORY_LABELS, REGISTRY

__all__ = [
    "AnalysisEngine", "AnalysisResult", "YearResult",
    "analyze_financials",
    "load_financials", "list_available_symbols", "validate_data",
    "REGISTRY", "CATEGORY_LABELS",
]
