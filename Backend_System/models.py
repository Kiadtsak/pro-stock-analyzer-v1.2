from pydantic import BaseModel
from typing import List, Dict, Optional

class CommitRequest(BaseModel):
    symbol: str

class RatioSeries(BaseModel):
    years: List[int]
    values: List[float]

class RatiosResponse(BaseModel):
    symbol: str
    series: Dict[str, RatioSeries]  # เช่น {"PE": {...}, "ROIC": {...}}

class FinancialsResponse(BaseModel):
    symbol: str
    income_statement: Dict[str, Dict[str, float]]
    balance_sheet: Dict[str, Dict[str, float]]
    cash_flow_statement: Dict[str, Dict[str, float]]

class ValuationRequest(BaseModel):
    symbol: str
    growth: float
    discount: float
    terminal: float

class ValuationResponse(BaseModel):
    symbol: str
    intrinsic_value: float
    assumptions: Dict[str, float]
