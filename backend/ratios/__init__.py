"""
Ratio registry — maps category names to their calculator classes.

To add a new category:
  1. Create backend/ratios/my_category.py with a MyCategoryRatios class
  2. Import it here + add to REGISTRY

Every calculator inherits from RatioBase and implements compute()
returning a dict of {ratio_name: value}.
"""
from backend.ratios.banking import BankingRatios
from backend.ratios.base import RatioBase, get, sdiv, sfloat, spct, sround
from backend.ratios.buffett import BuffettRatios
from backend.ratios.cash_flow import CashFlowRatios
from backend.ratios.cost_of_capital import CostOfCapitalRatios
from backend.ratios.dividend import DividendRatios
from backend.ratios.efficiency import EfficiencyRatios
from backend.ratios.growth import GrowthRatios
from backend.ratios.insurance import InsuranceRatios
from backend.ratios.intrinsic_value import IntrinsicValueRatios
from backend.ratios.leverage import LeverageRatios
from backend.ratios.liquidity import LiquidityRatios
from backend.ratios.profitability import ProfitabilityRatios
from backend.ratios.quality import QualityRatios
from backend.ratios.reit import REITRatios
from backend.ratios.risk import RiskRatios
from backend.ratios.semiconductor import SemiconductorRatios
from backend.ratios.software_saas import SaaSRatios
from backend.ratios.valuation import ValuationRatios

# ═══════════════════════════════════════════════════════════════════════════
# REGISTRY — all 18 categories
# ═══════════════════════════════════════════════════════════════════════════

REGISTRY: dict[str, type[RatioBase]] = {
    # Core financial categories
    "profitability":    ProfitabilityRatios,
    "efficiency":       EfficiencyRatios,
    "liquidity":        LiquidityRatios,
    "leverage":         LeverageRatios,
    "cash_flow":        CashFlowRatios,
    "growth":           GrowthRatios,
    "valuation":        ValuationRatios,
    "quality":          QualityRatios,
    "buffett":          BuffettRatios,
    "cost_of_capital":  CostOfCapitalRatios,
    "intrinsic_value":  IntrinsicValueRatios,
    "dividend":         DividendRatios,
    "risk":             RiskRatios,

    # Industry-specific
    "banking":          BankingRatios,
    "reit":             REITRatios,
    "software_saas":    SaaSRatios,
    "semiconductor":    SemiconductorRatios,
    "insurance":        InsuranceRatios,
}


CATEGORY_LABELS = {
    "profitability":    ("Profitability", "อัตราส่วนความสามารถทำกำไร"),
    "efficiency":       ("Efficiency", "อัตราส่วนประสิทธิภาพ"),
    "liquidity":        ("Liquidity", "อัตราส่วนสภาพคล่อง"),
    "leverage":         ("Leverage", "อัตราส่วนหนี้สิน"),
    "cash_flow":        ("Cash Flow", "อัตราส่วนกระแสเงินสด"),
    "growth":           ("Growth", "อัตราการเติบโต"),
    "valuation":        ("Valuation", "อัตราส่วนราคาเทียบมูลค่า"),
    "quality":          ("Quality", "อัตราส่วนคุณภาพงบ"),
    "buffett":          ("Buffett", "อัตราส่วนแบบ Buffett"),
    "cost_of_capital":  ("Cost of Capital", "ต้นทุนทางการเงิน"),
    "intrinsic_value":  ("Intrinsic Value", "มูลค่าที่แท้จริง"),
    "dividend":         ("Dividend", "อัตราส่วนเงินปันผล"),
    "risk":             ("Risk", "อัตราส่วนความเสี่ยง"),
    "banking":          ("Banking", "อัตราส่วนธนาคาร"),
    "reit":             ("REIT", "อัตราส่วนกองทุนอสังหาฯ"),
    "software_saas":    ("Software/SaaS", "อัตราส่วน SaaS"),
    "semiconductor":    ("Semiconductor", "อัตราส่วนเซมิคอนดักเตอร์"),
    "insurance":        ("Insurance", "อัตราส่วนประกันภัย"),
}


__all__ = [
    "REGISTRY",
    "CATEGORY_LABELS",
    "RatioBase",
    "get", "sfloat", "sdiv", "spct", "sround",
] + [cls.__name__ for cls in REGISTRY.values()]
