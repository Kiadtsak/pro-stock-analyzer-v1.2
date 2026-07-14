# Blackend/CashFlowModel.py  (PATCHED VERSION)
"""
แก้บั๊กหลัก:
1. FCF: CapEx ในข้อมูลเป็นค่าลบอยู่แล้ว -> ต้อง OCF + CapEx (ไม่ใช่ -)
2. WACC: fallback เมื่อ interest_paid=0, ใช้ 10-Y Treasury spread เป็น proxy
3. Cost of Equity: รับ market_return ที่สมเหตุสมผลกว่า + รองรับ override
4. PE Ratio: กันหารด้วย 0 / EPS ลบ
5. เพิ่ม safety guard ทุก division
6. quick_ratio, PBV_Ratio: ตรวจ key names ให้ตรงกับข้อมูลจริง
7. dcf_model_multiyear: รองรับข้อมูลไม่ครบโดย interpolate/fallback
"""
from __future__ import annotations
import numpy as np
from Backend.Settings import TAX_RATE, RISK_FREE_RATE, BETA
from typing import Dict, Optional, List


class CashFlowModel:
    def __init__(
        self,
        income_data: Optional[Dict] = None,
        balance_data: Optional[Dict] = None,
        cashflow_data: Optional[Dict] = None,
    ):
        self.income = income_data or {}
        self.balance = balance_data or {}
        self.cashflow = cashflow_data or {}

    # ---------------- Safe helpers ---------------- #

    def _num(self, d: Dict, key: str, default: float = 0.0) -> float:
        """ดึงค่าตัวเลขแบบปลอดภัย รองรับคีย์ที่ขาดหายหรือเป็น None"""
        v = d.get(key, default)
        if v is None:
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def _safe_div(self, num: float, den: float, default: float = 0.0) -> float:
        """หารแบบกัน zero/None"""
        try:
            if den == 0 or den is None:
                return default
            return num / den
        except (TypeError, ZeroDivisionError):
            return default

    # ================= Cost of Capital ================= #

    def cost_of_equity(self, market_return: Optional[List[float]] = None) -> float:
        """
        CAPM: Ke = Rf + β × (Rm - Rf)
        ใช้ค่าเฉลี่ย S&P 500 return ~10% เป็น default (ไม่ใช่ [7,8,9,10]%)
        """
        if market_return is None:
            rm = 0.10  # S&P 500 long-term avg ~10%
        else:
            rm = float(np.mean(market_return))
        return RISK_FREE_RATE + BETA * (rm - RISK_FREE_RATE)

    def interest_paid(self) -> float:
        """
        Interest Paid จากงบกระแสเงินสด (มักเป็นค่าลบ = cash out)
        คืนเป็นค่าบวก (จำนวนที่จ่ายจริง)
        Fallback: Interest Expense จาก Income Statement
        """
        # ใช้ Interest Paid ตรงๆ ก่อน
        ip = self._num(self.cashflow, "Interest Paid", 0.0)
        if ip != 0:
            return abs(ip)

        # Fallback จาก Income Statement
        ie = self._num(self.income, "Interest Expense", 0.0)
        return abs(ie)

    def wacc(self) -> float:
        """
        WACC = (E/V) × Ke + (D/V) × Kd × (1-T)
        - ถ้าไม่มีข้อมูลดอกเบี้ย ใช้ Kd proxy = Risk Free + 2% credit spread
        - ถ้า Equity หรือ Debt ขาดข้อมูล ใช้ค่า default ที่สมเหตุสมผล
        """
        equity = self._num(self.balance, "Total Shareholder Equity", 0.0)
        if equity <= 0:
            equity = self._num(self.balance, "Total Equity", 0.0)
        debt = self._num(self.balance, "Total Debt", 0.0)

        # ถ้าทั้งสองไม่มี -> return default
        if equity <= 0 and debt <= 0:
            return 0.10

        # Cost of Debt
        interest = self.interest_paid()
        if debt > 0 and interest > 0:
            cost_debt = interest / debt
        else:
            # Fallback: Rf + credit spread (corporate BBB avg ~2%)
            cost_debt = RISK_FREE_RATE + 0.02

        # กัน cost of debt ที่ผิดปกติ
        cost_debt = min(max(cost_debt, 0.01), 0.15)
        cost_debt_after_tax = cost_debt * (1 - TAX_RATE)

        total = equity + debt
        ke = self.cost_of_equity()
        wacc = (equity / total) * ke + (debt / total) * cost_debt_after_tax
        return round(wacc, 4)

    # ================= Cash Flow ================= #

    def Operating_Cash_Flow(self) -> float:
        """
        OCF จากงบ CF โดยตรง (ถ้ามี) แทนการสร้างใหม่
        ถ้าไม่มี: NI + D&A + SBC + Other Non-Cash + ΔWC
        """
        ocf_direct = self._num(self.cashflow, "Operating Cash Flow", 0.0)
        if ocf_direct != 0:
            return ocf_direct

        # Fallback: คำนวณเอง
        ni = self._num(self.income, "Net Income", 0.0)
        da = self._num(self.income, "Depreciation and Amortization", 0.0)
        sbc = self._num(self.cashflow, "Stock Based Compensation", 0.0)
        onc = self._num(self.cashflow, "Other Non Cash Items", 0.0)
        wc = self._num(self.cashflow, "Change in Working Capital", 0.0)
        return ni + da + sbc + onc + wc

    def Free_Cash_Flow(self) -> float:
        """
        🔴 BUG FIX: CapEx จาก FMP/FinanceToolkit เป็นค่าลบอยู่แล้ว
        FCF = OCF + CapEx (ไม่ใช่ - CapEx)
        
        ถ้ามี Free Cash Flow ในงบ CF อยู่แล้ว -> ใช้ตรงๆ
        """
        fcf_direct = self._num(self.cashflow, "Free Cash Flow", 0.0)
        if fcf_direct != 0:
            return fcf_direct

        ocf = self.Operating_Cash_Flow()
        capex = self._num(self.cashflow, "Capital Expenditure", 0.0)
        # CapEx เป็นค่าลบอยู่แล้ว -> บวกตรงๆ
        return ocf + capex

    def unlevered_free_cash_flow(self) -> float:
        """
        UFCF = EBIT×(1-T) + D&A - CapEx - ΔWC
        CapEx เป็นลบ -> บวกตรงๆ, ΔWC (เพิ่ม = cash out)
        """
        op_inc = self._num(self.income, "Operating Income", 0.0)
        da = self._num(self.income, "Depreciation and Amortization", 0.0)
        capex = self._num(self.cashflow, "Capital Expenditure", 0.0)
        wc = self._num(self.cashflow, "Change in Working Capital", 0.0)
        # capex เป็นลบอยู่แล้ว -> บวกเข้า / wc ในงบ CF เป็น source(+) ใช้จริง(-)
        return op_inc * (1 - TAX_RATE) + da + capex - wc

    # ================= Growth ================= #

    def growth_rate_cagr(self, start: float, end: float, years: int) -> float:
        """CAGR แบบกัน negative base และ zero division"""
        if start is None or end is None or start <= 0 or end <= 0 or years <= 0:
            return 0.0
        try:
            return float(np.power(end / start, 1 / years) - 1)
        except Exception:
            return 0.0

    # ================= DCF (Vectorized) ================= #

    def dcf_model_multiyear(self, ufcf_series: List[float], years: int = 10) -> np.ndarray:
        """
        DCF แบบ vectorized
        - ถ้า UFCF ไม่ครบ N ปี -> ใช้ที่มี + extrapolate ด้วย CAGR
        - ป้องกัน wacc <= g (terminal value ระเบิด)
        """
        ufcf = np.array([float(x) for x in ufcf_series if x is not None], dtype=float)
        if len(ufcf) == 0:
            raise ValueError("UFCF series ว่าง")

        wacc = self.wacc()
        if wacc <= 0:
            wacc = 0.10

        # ถ้าไม่ครบ -> extrapolate
        if len(ufcf) < years:
            # CAGR จากสิ่งที่มี
            if len(ufcf) >= 2:
                g = self.growth_rate_cagr(ufcf[0], ufcf[-1], len(ufcf) - 1)
            else:
                g = 0.05
            last = ufcf[-1]
            extra = []
            for _ in range(years - len(ufcf)):
                last = last * (1 + g)
                extra.append(last)
            ufcf = np.concatenate([ufcf, np.array(extra)])

        ufcf = ufcf[:years]

        t = np.arange(1, years + 1)
        discount_factor = np.power(1 + wacc, t)
        discounted = ufcf / discount_factor

        # Terminal Value (กัน g >= wacc)
        g = self.growth_rate_cagr(ufcf[0], ufcf[-1], years)
        g = min(max(g, -0.05), wacc - 0.01)  # clip
        terminal = (ufcf[-1] * (1 + g)) / (wacc - g)
        terminal_discounted = terminal / np.power(1 + wacc, years)

        return np.append(discounted, terminal_discounted)

    def intrinsic_value_per_share(self, ufcf_series: List[float]) -> float:
        dcf = self.dcf_model_multiyear(ufcf_series)
        # 🔴 BUG FIX: ชื่อคีย์มี space เกิน "weighted_average_shares " -> ใช้ชื่อจริง
        shares = self._num(self.income, "weighted_average_shares", 0.0)#"Weighted Average Shares", 0.0)
        if shares <= 0:
            shares = self._num(self.income, "Weighted Average Shares Diluted", 1.0)
        return round(self._safe_div(float(dcf.sum()), shares, 0.0), 2)

    # ================= Efficiency ================= #

    def asset_turnover(self) -> float:
        rev = self._num(self.income, "Revenue")
        ta = self._num(self.balance, "Total Assets")
        return self._safe_div(rev, ta)

    def inventory_turnover(self) -> float:
        cogs = self._num(self.income, "Cost of Goods Sold")
        inv = self._num(self.balance, "Inventory")
        return self._safe_div(cogs, inv)

    def receivables_turnover(self) -> float:
        rev = self._num(self.income, "Revenue")
        ar = self._num(self.balance, "Accounts Receivable")
        return self._safe_div(rev, ar)

    def days_inventory_outstanding(self) -> float:
        it = self.inventory_turnover()
        return self._safe_div(365.0, it)

    def days_sales_outstanding(self) -> float:
        rt = self.receivables_turnover()
        return self._safe_div(365.0, rt)

    def working_capital_turnover(self) -> float:
        ca = self._num(self.balance, "Total Current Assets")
        cl = self._num(self.balance, "Total Current Liabilities")
        rev = self._num(self.income, "Revenue")
        wc = ca - cl
        return self._safe_div(rev, wc)

    # ================= Profitability ================= #

    def ROE(self) -> float:
        ni = self._num(self.income, "Net Income")
        eq = self._num(self.balance, "Total Shareholder Equity")
        if eq <= 0:
            eq = self._num(self.balance, "Total Equity")
        return self._safe_div(ni, eq) * 100

    def ROA(self) -> float:
        ni = self._num(self.income, "Net Income")
        ta = self._num(self.balance, "Total Assets")
        return self._safe_div(ni, ta) * 100

    def gross_profit_margin(self) -> float:
        gp = self._num(self.income, "Gross Profit")
        rev = self._num(self.income, "Revenue")
        return self._safe_div(gp, rev) * 100

    def operation_profit_margin(self) -> float:
        op = self._num(self.income, "Operating Income")
        rev = self._num(self.income, "Revenue")
        return self._safe_div(op, rev) * 100

    def net_profit_margin(self) -> float:
        ni = self._num(self.income, "Net Income")
        rev = self._num(self.income, "Revenue")
        return self._safe_div(ni, rev) * 100

    def ebitda_margin(self) -> float:
        ebitda = self._num(self.income, "EBITDA")
        rev = self._num(self.income, "Revenue")
        return self._safe_div(ebitda, rev) * 100

    # ================= Valuation ================= #

    def Owners_Earnings(self) -> float:
        """
        Buffett's Owner Earnings = NI + D&A + CapEx - ΔWC (approx)
        Note: CapEx เป็นลบ -> บวกตรงๆ
        """
        ni = self._num(self.income, "Net Income")
        da = self._num(self.cashflow, "Depreciation and Amortization")
        capex = self._num(self.cashflow, "Capital Expenditure")
        wc = self._num(self.cashflow, "Change in Working Capital")
        return ni + da + capex - wc

    def EPS_Ratio(self) -> float:
        """ใช้ EPS จากข้อมูลจริงก่อน ถ้าไม่มี -> คำนวณเอง"""
        eps = self._num(self.income, "EPS")
        if eps != 0:
            return eps
        ni = self._num(self.income, "Net Income")
        shares = self._num(self.income, "Weighted Average Shares")
        return self._safe_div(ni, shares)

    def PE_Ratio(self) -> float:
        """P/E = Price / EPS (กัน EPS <= 0)"""
        price = self._num(self.income, "price")
        eps = self.EPS_Ratio()
        if eps <= 0:
            return 0.0
        return self._safe_div(price, eps)

    def PBV_Ratio(self) -> float:
        """P/B = Price / (Equity per share)"""
        equity = self._num(self.balance, "Total Shareholder Equity")
        if equity <= 0:
            equity = self._num(self.balance, "Total Equity")
        shares = self._num(self.income, "Weighted Average Shares")
        price = self._num(self.income, "price")

        if equity <= 0 or shares <= 0 or price <= 0:
            return 0.0

        book_value = equity / shares
        return self._safe_div(price, book_value)

    # ================= Liquidity ================= #

    def current_ratio(self) -> float:
        ca = self._num(self.balance, "Total Current Assets")
        cl = self._num(self.balance, "Total Current Liabilities")
        return self._safe_div(ca, cl)

    def quick_ratio(self) -> float:
        ca = self._num(self.balance, "Total Current Assets")
        inv = self._num(self.balance, "Inventory")
        cl = self._num(self.balance, "Total Current Liabilities")
        return self._safe_div(ca - inv, cl)

    def cash_ratio(self) -> float:
        cash = self._num(self.balance, "Cash and Cash Equivalents")
        sti = self._num(self.balance, "Short Term Investments")
        cl = self._num(self.balance, "Total Current Liabilities")
        return self._safe_div(cash + sti, cl)

    # ================= NEW: Solvency ================= #

    def debt_to_equity(self) -> float:
        debt = self._num(self.balance, "Total Debt")
        eq = self._num(self.balance, "Total Shareholder Equity")
        if eq <= 0:
            eq = self._num(self.balance, "Total Equity")
        return self._safe_div(debt, eq)

    def debt_to_assets(self) -> float:
        debt = self._num(self.balance, "Total Debt")
        ta = self._num(self.balance, "Total Assets")
        return self._safe_div(debt, ta)

    def interest_coverage(self) -> float:
        ebit = self._num(self.income, "EBIT")
        ie = self._num(self.income, "Interest Expense")
        return self._safe_div(ebit, ie)

    # ================= NEW: Risk / Altman Z-Score ================= #

    def altman_z_score(self) -> float:
        """
        Altman Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E
        A = Working Capital / Total Assets
        B = Retained Earnings / Total Assets
        C = EBIT / Total Assets
        D = Equity / Total Liabilities  (market value ideal)
        E = Revenue / Total Assets
        """
        ta = self._num(self.balance, "Total Assets")
        if ta <= 0:
            return 0.0

        ca = self._num(self.balance, "Total Current Assets")
        cl = self._num(self.balance, "Total Current Liabilities")
        re = self._num(self.balance, "Retained Earnings")
        ebit = self._num(self.income, "EBIT")
        eq = self._num(self.balance, "Total Shareholder Equity")
        if eq <= 0:
            eq = self._num(self.balance, "Total Equity")
        tl = self._num(self.balance, "Total Liabilities")
        rev = self._num(self.income, "Revenue")

        A = self._safe_div(ca - cl, ta)
        B = self._safe_div(re, ta)
        C = self._safe_div(ebit, ta)
        D = self._safe_div(eq, tl)
        E = self._safe_div(rev, ta)

        return 1.2 * A + 1.4 * B + 3.3 * C + 0.6 * D + 1.0 * E