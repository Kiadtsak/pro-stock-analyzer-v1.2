"""
backend/narrator.py — Deep bilingual analyst report generator.

Takes an AnalysisResult and produces a comprehensive 12-section report
using 80-100 of the 200+ calculated ratios.

Every section includes:
  - Interpretation with concrete numbers
  - Health score (0-100) for that dimension
  - List of metrics used (transparency)
  - Bilingual output (TH + EN)
"""
from __future__ import annotations

from backend.engine import AnalysisResult

# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _fmt(v: float | None, suffix: str = "", decimals: int = 2) -> str:
    """Format a number for display, handling None."""
    if v is None:
        return "N/A"
    if isinstance(v, (int, float)):
        if abs(v) >= 1_000_000_000:
            return f"{v/1_000_000_000:.{decimals}f}B{suffix}"
        if abs(v) >= 1_000_000:
            return f"{v/1_000_000:.{decimals}f}M{suffix}"
        return f"{v:.{decimals}f}{suffix}"
    return str(v)


def _pct(v: float | None) -> str:
    return _fmt(v, "%")


def _tier(value: float | None, thresholds: list[tuple[float, str, str]]) -> tuple[str, str]:
    """
    Classify a value into tier (EN, TH labels).

    thresholds: [(threshold, en_label, th_label), ...] sorted descending
    Returns (en, th) for the first threshold matched.
    """
    if value is None:
        return ("N/A", "ไม่มีข้อมูล")
    for thresh, en, th in thresholds:
        if value >= thresh:
            return (en, th)
    return thresholds[-1][1], thresholds[-1][2]


def _get(d: dict, *keys: str) -> float | None:
    """Safe get across possible key names."""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


# ═══════════════════════════════════════════════════════════════════════════
# DeepNarrator
# ═══════════════════════════════════════════════════════════════════════════

class DeepNarrator:
    """Generate a comprehensive analyst report from an AnalysisResult."""

    def __init__(self, result: AnalysisResult):
        self.r = result
        self.latest = result.latest_by_category
        self.metrics_used: list[str] = []

    # ═══════════════════════════════════════════════════════
    # Main entry point
    # ═══════════════════════════════════════════════════════
    def generate(self) -> dict:
        sections = [
            self._exec_summary(),
            self._business_quality(),
            self._profitability_deep(),
            self._growth_analysis(),
            self._cash_generation(),
            self._valuation_deep(),
            self._financial_health(),
            self._balance_sheet(),
        ]

        # Sector-specific (only if applicable)
        sector_section = self._sector_specific()
        if sector_section:
            sections.append(sector_section)

        sections.extend([
            self._risk_factors(),
            self._bull_bear_cases(),
            self._verdict(),
        ])

        return {
            "symbol": self.r.symbol,
            "name": self.r.name,
            "signal": self.r.signal,
            "signal_th": self.r.signal_th,
            "composite_score": self.r.composite_score,
            "total_available_ratios": self.r.total_ratios,
            "ratios_used_in_analysis": len(set(self.metrics_used)),
            "sections": sections,
            "markdown_th": self._render_markdown(sections, "th"),
            "markdown_en": self._render_markdown(sections, "en"),
        }

    # ═══════════════════════════════════════════════════════
    # SECTION 1: Executive Summary
    # ═══════════════════════════════════════════════════════
    def _exec_summary(self) -> dict:
        r = self.r
        prof = self.latest.get("profitability", {})
        val = self.latest.get("valuation", {})
        iv = self.latest.get("intrinsic_value", {})
        growth = self.latest.get("growth", {})

        roe = prof.get("ROE")
        pe = val.get("P/E Ratio")
        mos = iv.get("Margin of Safety (DCF)")
        rev_growth = growth.get("Revenue Growth YoY")

        self.metrics_used += ["ROE", "P/E Ratio", "Margin of Safety (DCF)", "Revenue Growth YoY"]

        content_en = (
            f"{r.symbol} ({r.name}) receives a **{r.signal}** rating with a composite "
            f"score of **{r.composite_score}/100** based on {r.total_ratios} financial ratios. "
            f"The company operates in the {r.sector or 'unspecified'} sector, "
            f"currently trading at ${_fmt(r.current_price)} per share. "
            f"Key headline metrics: ROE of {_pct(roe)}, revenue growth of {_pct(rev_growth)} YoY, "
            f"and P/E ratio of {_fmt(pe, 'x')}. "
        )
        if mos is not None:
            if mos > 0:
                content_en += f"Discounted cash flow analysis suggests the stock trades **{_fmt(mos*100, '%')} below** intrinsic value."
            else:
                content_en += f"Discounted cash flow analysis suggests the stock trades **{_fmt(-mos*100, '%')} above** intrinsic value."

        content_th = (
            f"{r.symbol} ({r.name}) ได้รับ signal **{r.signal_th}** ด้วยคะแนน "
            f"**{r.composite_score}/100** จากการวิเคราะห์ {r.total_ratios} อัตราส่วนทางการเงิน "
            f"บริษัทอยู่ในกลุ่มอุตสาหกรรม {r.sector or 'ไม่ระบุ'} "
            f"ราคาปัจจุบัน ${_fmt(r.current_price)} ต่อหุ้น "
            f"ตัวเลขหลัก: ROE {_pct(roe)} · การเติบโตของรายได้ {_pct(rev_growth)} YoY · P/E {_fmt(pe, 'x')} "
        )
        if mos is not None:
            if mos > 0:
                content_th += f"การประเมิน DCF ชี้ว่าราคาปัจจุบัน**ต่ำกว่ามูลค่าจริง {_fmt(mos*100, '%')}**"
            else:
                content_th += f"การประเมิน DCF ชี้ว่าราคาปัจจุบัน**สูงกว่ามูลค่าจริง {_fmt(-mos*100, '%')} (แพง)**"

        return {
            "id": "exec_summary",
            "title_en": "Executive Summary",
            "title_th": "บทสรุปสำหรับผู้บริหาร",
            "content_en": content_en,
            "content_th": content_th,
            "metrics_used": ["ROE", "P/E", "MoS (DCF)", "Revenue Growth"],
        }

    # ═══════════════════════════════════════════════════════
    # SECTION 2: Business Quality (Buffett-style)
    # ═══════════════════════════════════════════════════════
    def _business_quality(self) -> dict:
        buffett = self.latest.get("buffett", {})
        prof = self.latest.get("profitability", {})

        roe = prof.get("ROE")
        roe_10y = buffett.get("10Y Average ROE")
        roe_consistency = buffett.get("ROE Consistency")
        moat = buffett.get("Moat Score (0-4)")
        gross_margin = prof.get("Gross Profit Margin")
        op_margin = prof.get("Operating Profit Margin")
        cash_conv = buffett.get("Cash Conversion Ratio")

        self.metrics_used += ["ROE", "10Y Average ROE", "ROE Consistency", "Moat Score (0-4)",
                              "Gross Profit Margin", "Operating Profit Margin", "Cash Conversion Ratio"]

        # Interpretations
        roe_tier_en, roe_tier_th = _tier(roe, [
            (25, "exceptional", "ยอดเยี่ยม"),
            (15, "strong", "ดี"),
            (10, "adequate", "พอใช้"),
            (0, "weak", "อ่อนแอ"),
        ])
        gm_tier_en, gm_tier_th = _tier(gross_margin, [
            (60, "exceptional pricing power", "อำนาจกำหนดราคาสูงมาก"),
            (40, "strong pricing power", "อำนาจกำหนดราคาแข็งแกร่ง"),
            (25, "moderate margins", "มาร์จิ้นปานกลาง"),
            (0, "commodity-like margins", "มาร์จิ้นระดับสินค้าโภคภัณฑ์"),
        ])
        moat_tier_en, moat_tier_th = _tier(moat, [
            (4, "wide moat (4/4 signals)", "คูเมืองกว้าง (4/4)"),
            (3, "solid moat (3/4 signals)", "คูเมืองแข็ง (3/4)"),
            (2, "some moat characteristics (2/4)", "มีบางลักษณะของคูเมือง (2/4)"),
            (0, "limited moat evidence", "หลักฐานคูเมืองน้อย"),
        ])

        score = self._quality_score([roe, gross_margin, op_margin, moat, cash_conv])

        content_en = (
            f"NBusiness quality assessment reveals {roe_tier_en} returns on equity at {_pct(roe)}, "
            f"with a 10-year average ROE of {_pct(roe_10y)}. "
            f"The company demonstrates {gm_tier_en} with gross margin of {_pct(gross_margin)} "
            f"and operating margin of {_pct(op_margin)}. "
            f"Buffett-style moat analysis shows {moat_tier_en}, indicating the company "
            f"{'likely enjoys durable competitive advantages' if (moat or 0) >= 3 else 'faces competitive pressure'}. "
            f"Cash conversion ratio of {_fmt(cash_conv)} suggests earnings are "
            f"{'high quality (backed by real cash flow)' if (cash_conv or 0) >= 1 else 'partially accrual-based'}."
        )

        content_th = (
            f"คุณภาพธุรกิจแสดงให้เห็นว่า ROE อยู่ในระดับ**{roe_tier_th}** ({_pct(roe)}) "
            f"โดยเฉลี่ย 10 ปีที่ {_pct(roe_10y)} "
            f"บริษัทมี{gm_tier_th} — Gross margin {_pct(gross_margin)} และ Operating margin {_pct(op_margin)} "
            f"การประเมินคูเมือง (Moat) แบบ Buffett แสดง{moat_tier_th} "
            f"บ่งชี้ว่าบริษัท{'มีข้อได้เปรียบที่ยั่งยืน' if (moat or 0) >= 3 else 'เผชิญแรงกดดันจากการแข่งขัน'} "
            f"Cash conversion ratio {_fmt(cash_conv)} แสดงว่ากำไร"
            f"{'มีคุณภาพสูง (รองรับด้วยกระแสเงินสดจริง)' if (cash_conv or 0) >= 1 else 'มีส่วนที่มาจากรายการทางบัญชี'}"
        )

        return {
            "id": "business_quality",
            "title_en": "Business Quality Assessment",
            "title_th": "การประเมินคุณภาพธุรกิจ",
            "content_en": content_en,
            "content_th": content_th,
            "score": score,
            "metrics_used": ["ROE", "10Y ROE Avg", "ROE Consistency", "Moat Score",
                             "Gross Margin", "Operating Margin", "Cash Conversion"],
        }

    # ═══════════════════════════════════════════════════════
    # SECTION 3: Profitability Deep Dive
    # ═══════════════════════════════════════════════════════
    def _profitability_deep(self) -> dict:
        prof = self.latest.get("profitability", {})

        metrics = {
            "Gross Margin": prof.get("Gross Profit Margin"),
            "Operating Margin": prof.get("Operating Profit Margin"),
            "EBIT Margin": prof.get("EBIT Margin"),
            "EBITDA Margin": prof.get("EBITDA Margin"),
            "Net Margin": prof.get("Net Profit Margin"),
            "ROE": prof.get("ROE"),
            "ROA": prof.get("ROA"),
            "ROIC": prof.get("ROIC"),
            "ROCE": prof.get("ROCE"),
            "Cash ROA": prof.get("Cash ROA"),
            "FCF ROE": prof.get("FCF Return on Equity"),
            "NOPAT": prof.get("NOPAT"),
        }
        for k in metrics:
            self.metrics_used.append(k if k != "Gross Margin" else "Gross Profit Margin")

        roic = metrics["ROIC"]
        roa = metrics["ROA"]

        content_en = (
            f"Margin structure analysis: Revenue converts to gross profit at "
            f"{_pct(metrics['Gross Margin'])}, then operating profit at {_pct(metrics['Operating Margin'])}, "
            f"and finally net income at {_pct(metrics['Net Margin'])}. "
            f"The company's return on invested capital (ROIC) of {_pct(roic)} "
            f"{'substantially exceeds' if (roic or 0) > 15 else 'is close to'} typical cost of capital, "
            f"{'suggesting strong value creation' if (roic or 0) > 15 else 'suggesting limited excess returns'}. "
            f"Asset productivity as measured by ROA is {_pct(roa)}, "
            f"while cash-based returns (Cash ROA {_pct(metrics['Cash ROA'])}, "
            f"FCF ROE {_pct(metrics['FCF ROE'])}) confirm the profitability picture. "
            f"NOPAT stands at {_fmt(metrics['NOPAT'], '$')}."
        )

        content_th = (
            f"โครงสร้างมาร์จิ้น: รายได้แปลงเป็นกำไรขั้นต้น {_pct(metrics['Gross Margin'])} "
            f"→ กำไรจากการดำเนินงาน {_pct(metrics['Operating Margin'])} "
            f"→ กำไรสุทธิ {_pct(metrics['Net Margin'])} "
            f"ROIC {_pct(roic)} {'สูงกว่า' if (roic or 0) > 15 else 'ใกล้เคียง'}ต้นทุนเงินทุนโดยทั่วไป "
            f"{'สะท้อนการสร้างมูลค่าที่แข็งแกร่ง' if (roic or 0) > 15 else 'บ่งชี้ว่าผลตอบแทนส่วนเกินมีจำกัด'} "
            f"ROA อยู่ที่ {_pct(roa)} และผลตอบแทนจากกระแสเงินสด (Cash ROA {_pct(metrics['Cash ROA'])}, "
            f"FCF ROE {_pct(metrics['FCF ROE'])}) ยืนยันภาพรวมความสามารถทำกำไร "
            f"NOPAT อยู่ที่ {_fmt(metrics['NOPAT'], ' USD')}"
        )

        score = self._profitability_score(metrics)

        return {
            "id": "profitability_deep",
            "title_en": "Profitability Deep Dive",
            "title_th": "การวิเคราะห์ความสามารถทำกำไรเชิงลึก",
            "content_en": content_en,
            "content_th": content_th,
            "metrics": {k: v for k, v in metrics.items() if v is not None},
            "score": score,
            "metrics_used": list(metrics.keys()),
        }

    # ═══════════════════════════════════════════════════════
    # SECTION 4: Growth Analysis
    # ═══════════════════════════════════════════════════════
    def _growth_analysis(self) -> dict:
        g = self.latest.get("growth", {})

        rev_g = g.get("Revenue Growth YoY")
        ni_g = g.get("Net Income Growth YoY")
        eps_g = g.get("EPS Growth YoY")
        fcf_g = g.get("FCF Growth YoY")
        equity_g = g.get("Equity (Book Value) Growth YoY")
        sgr = g.get("Sustainable Growth Rate")
        igr = g.get("Internal Growth Rate")
        retention = g.get("Retention Ratio")

        self.metrics_used += ["Revenue Growth YoY", "Net Income Growth YoY", "EPS Growth YoY",
                              "FCF Growth YoY", "Sustainable Growth Rate", "Internal Growth Rate"]

        rev_tier_en, rev_tier_th = _tier(rev_g, [
            (30, "hypergrowth", "โตแบบก้าวกระโดด"),
            (15, "strong growth", "โตอย่างแข็งแกร่ง"),
            (5, "steady growth", "โตอย่างสม่ำเสมอ"),
            (0, "flat", "ทรงตัว"),
            (-100, "declining", "หดตัว"),
        ])

        # Sustainability check
        sustainability_note_en = ""
        sustainability_note_th = ""
        if rev_g is not None and sgr is not None:
            if rev_g > sgr * 1.5:
                sustainability_note_en = (f" Current revenue growth ({_pct(rev_g)}) significantly exceeds "
                                          f"the sustainable growth rate ({_pct(sgr)}), suggesting the company "
                                          f"may need external financing or higher retention to maintain this pace.")
                sustainability_note_th = (f" อัตราการเติบโตของรายได้ปัจจุบัน ({_pct(rev_g)}) "
                                          f"เกิน Sustainable Growth Rate ({_pct(sgr)}) มากพอสมควร "
                                          f"อาจต้องอาศัยการระดมทุนจากภายนอกหรือเพิ่มการเก็บกำไรเพื่อรักษาโมเมนตัม")

        content_en = (
            f"Growth profile: Revenue expanded {_pct(rev_g)} YoY, classified as {rev_tier_en}. "
            f"Bottom-line growth was {_pct(ni_g)} for net income and {_pct(eps_g)} for EPS "
            f"(divergence indicates {'share dilution' if eps_g and ni_g and eps_g < ni_g else 'buyback impact' if eps_g and ni_g and eps_g > ni_g else 'stable share count'}). "
            f"Free cash flow grew {_pct(fcf_g)}, while book value expanded {_pct(equity_g)}. "
            f"Sustainable Growth Rate (ROE × Retention) is {_pct(sgr)}, "
            f"while Internal Growth Rate (fundable without debt) is {_pct(igr)}. "
            f"Retention ratio of {_pct(retention)} shows the company reinvests {_pct(retention)} of earnings."
            f"{sustainability_note_en}"
        )

        content_th = (
            f"โปรไฟล์การเติบโต: รายได้เพิ่มขึ้น {_pct(rev_g)} YoY จัดว่า{rev_tier_th} "
            f"กำไรสุทธิเติบโต {_pct(ni_g)} · EPS เติบโต {_pct(eps_g)} "
            f"({'มีการเพิ่มทุน' if eps_g and ni_g and eps_g < ni_g else 'มีการซื้อหุ้นคืน' if eps_g and ni_g and eps_g > ni_g else 'จำนวนหุ้นคงที่'}) "
            f"FCF เติบโต {_pct(fcf_g)} · Book value เติบโต {_pct(equity_g)} "
            f"Sustainable Growth Rate (ROE × Retention) = {_pct(sgr)} "
            f"และ Internal Growth Rate (ใช้แค่กำไรสะสม) = {_pct(igr)} "
            f"Retention ratio {_pct(retention)} หมายถึงบริษัทเก็บกำไร {_pct(retention)} เพื่อลงทุนต่อ"
            f"{sustainability_note_th}"
        )

        return {
            "id": "growth_analysis",
            "title_en": "Growth Analysis",
            "title_th": "การวิเคราะห์การเติบโต",
            "content_en": content_en,
            "content_th": content_th,
            "score": self._growth_score([rev_g, ni_g, eps_g, fcf_g]),
            "metrics_used": ["Revenue Growth", "Net Income Growth", "EPS Growth",
                             "FCF Growth", "SGR", "IGR", "Retention Ratio"],
        }

    # ═══════════════════════════════════════════════════════
    # SECTION 5: Cash Generation & Earnings Quality
    # ═══════════════════════════════════════════════════════
    def _cash_generation(self) -> dict:
        cf = self.latest.get("cash_flow", {})
        buffett = self.latest.get("buffett", {})

        ocf = cf.get("Operating Cash Flow (OCF)")
        fcf = cf.get("Free Cash Flow (FCF)")
        ufcf = cf.get("Unlevered Free Cash Flow (UFCF)")
        oe = cf.get("Owner Earnings (Buffett)")

        fcf_margin = cf.get("FCF Margin")
        ocf_to_ni = cf.get("OCF to Net Income")
        accrual = cf.get("Accrual Ratio")
        capex_to_ocf = cf.get("CapEx to OCF")
        capex_to_da = cf.get("CapEx to Depreciation")

        div_to_fcf = cf.get("Dividends to FCF")
        buyback_to_fcf = cf.get("Buybacks to FCF")
        total_return = cf.get("Total Shareholder Return to FCF")

        self.metrics_used += ["Operating Cash Flow (OCF)", "Free Cash Flow (FCF)",
                              "Owner Earnings (Buffett)", "FCF Margin", "OCF to Net Income",
                              "Accrual Ratio", "CapEx to OCF", "CapEx to Depreciation",
                              "Dividends to FCF", "Buybacks to FCF"]

        # Earnings quality
        eq_note_en = "clean, cash-backed" if (ocf_to_ni or 0) >= 1 else "partially accrual-based"
        eq_note_th = "สะอาด รองรับด้วยกระแสเงินสด" if (ocf_to_ni or 0) >= 1 else "มีส่วนที่มาจากการบัญชี"

        # CapEx interpretation
        capex_note_en = ("growth investment mode" if (capex_to_da or 0) > 1.2
                         else "maintenance mode" if (capex_to_da or 0) > 0.7
                         else "underinvestment")
        capex_note_th = ("อยู่ในโหมดลงทุนขยาย" if (capex_to_da or 0) > 1.2
                         else "อยู่ในโหมดบำรุงรักษา" if (capex_to_da or 0) > 0.7
                         else "ลงทุนน้อยกว่าการเสื่อมค่า")

        content_en = (
            f"Cash generation: Operating cash flow of {_fmt(ocf, '$')} converts to "
            f"free cash flow of {_fmt(fcf, '$')} after CapEx of {_pct(capex_to_ocf)} of OCF. "
            f"Unlevered FCF is {_fmt(ufcf, '$')} and Buffett-style Owner Earnings are {_fmt(oe, '$')}. "
            f"FCF margin of {_pct(fcf_margin)} reflects the company's ability to convert revenue to cash. "
            f"Earnings quality: OCF/Net Income ratio of {_fmt(ocf_to_ni)} indicates {eq_note_en} earnings. "
            f"Accrual ratio of {_fmt(accrual)} — {'low (positive quality signal)' if abs(accrual or 0) < 0.05 else 'elevated (monitor)'}. "
            f"CapEx to D&A ratio of {_fmt(capex_to_da)} shows the company is in {capex_note_en}. "
            f"Capital return: {_pct(div_to_fcf)} of FCF paid as dividends, "
            f"{_pct(buyback_to_fcf)} used for buybacks (total {_pct(total_return)})."
        )

        content_th = (
            f"การสร้างกระแสเงินสด: OCF {_fmt(ocf, ' USD')} → FCF {_fmt(fcf, ' USD')} "
            f"หลังหักการลงทุน CapEx คิดเป็น {_pct(capex_to_ocf)} ของ OCF "
            f"UFCF อยู่ที่ {_fmt(ufcf, ' USD')} · Owner Earnings แบบ Buffett = {_fmt(oe, ' USD')} "
            f"FCF margin {_pct(fcf_margin)} สะท้อนความสามารถแปลงรายได้เป็นเงินสด "
            f"คุณภาพกำไร: OCF/Net Income = {_fmt(ocf_to_ni)} แสดงว่ากำไร{eq_note_th} "
            f"Accrual ratio {_fmt(accrual)} — {'ต่ำ (สัญญาณคุณภาพดี)' if abs(accrual or 0) < 0.05 else 'สูง (ควรระวัง)'} "
            f"CapEx to D&A {_fmt(capex_to_da)} แสดงว่าบริษัท{capex_note_th} "
            f"การคืนทุน: จ่ายเงินปันผล {_pct(div_to_fcf)} ของ FCF · "
            f"ซื้อหุ้นคืน {_pct(buyback_to_fcf)} (รวมทั้งหมด {_pct(total_return)})"
        )

        return {
            "id": "cash_generation",
            "title_en": "Cash Generation & Earnings Quality",
            "title_th": "การสร้างกระแสเงินสดและคุณภาพกำไร",
            "content_en": content_en,
            "content_th": content_th,
            "score": self._cash_score(ocf_to_ni, fcf_margin, accrual),
            "metrics_used": ["OCF", "FCF", "UFCF", "Owner Earnings", "FCF Margin",
                             "OCF/NI", "Accrual Ratio", "CapEx/OCF", "CapEx/D&A",
                             "Div/FCF", "Buybacks/FCF"],
        }

    # ═══════════════════════════════════════════════════════
    # SECTION 6: Valuation Deep Dive
    # ═══════════════════════════════════════════════════════
    def _valuation_deep(self) -> dict:
        v = self.latest.get("valuation", {})
        iv = self.latest.get("intrinsic_value", {})
        wacc_data = self.latest.get("cost_of_capital", {})

        pe = v.get("P/E Ratio")
        peg = v.get("P/E to Growth (PEG)")
        pb = v.get("P/B Ratio")
        ps = v.get("P/S Ratio")
        ev_ebitda = v.get("EV / EBITDA")
        ev_fcf = v.get("EV / FCF")
        fcf_yield = v.get("FCF Yield")
        earnings_yield = v.get("Earnings Yield")

        dcf = iv.get("Intrinsic Value (DCF)")
        oe_dcf = iv.get("Intrinsic Value (Owner Earnings DCF)")
        graham = iv.get("Intrinsic Value (Graham Number)")
        ten_cap = iv.get("Intrinsic Value (Ten Cap)")
        mos_dcf = iv.get("Margin of Safety (DCF)")
        mos_graham = iv.get("Margin of Safety (Graham)")
        implied_g = iv.get("Implied Growth (Reverse DCF)")

        wacc = wacc_data.get("WACC")
        cost_equity = wacc_data.get("Cost of Equity (CAPM)")

        self.metrics_used += ["P/E Ratio", "P/E to Growth (PEG)", "P/B Ratio", "P/S Ratio",
                              "EV / EBITDA", "EV / FCF", "FCF Yield", "Earnings Yield",
                              "Intrinsic Value (DCF)", "Intrinsic Value (Owner Earnings DCF)",
                              "Intrinsic Value (Graham Number)", "Intrinsic Value (Ten Cap)",
                              "Margin of Safety (DCF)", "Implied Growth (Reverse DCF)",
                              "WACC", "Cost of Equity (CAPM)"]

        pe_tier_en, pe_tier_th = _tier(pe, [
            (40, "very expensive", "แพงมาก"),
            (25, "premium", "พรีเมียม"),
            (15, "reasonable", "สมเหตุสมผล"),
            (0, "cheap", "ถูก"),
        ])

        peg_note_en = ""
        peg_note_th = ""
        if peg is not None:
            if peg < 1:
                peg_note_en = f" PEG ratio of {_fmt(peg)} suggests the stock is cheap relative to its growth."
                peg_note_th = f" PEG {_fmt(peg)} บ่งชี้ว่าราคาถูกเมื่อเทียบกับการเติบโต"
            elif peg > 2:
                peg_note_en = f" PEG ratio of {_fmt(peg)} suggests the stock is expensive relative to its growth."
                peg_note_th = f" PEG {_fmt(peg)} บ่งชี้ว่าราคาแพงเมื่อเทียบกับการเติบโต"

        content_en = (
            f"Multiple valuation methods yield different intrinsic value estimates: "
            f"**Two-stage DCF: ${_fmt(dcf)}**, "
            f"Owner Earnings DCF: ${_fmt(oe_dcf)}, "
            f"Graham Number: ${_fmt(graham)}, "
            f"Ten Cap (Buffett): ${_fmt(ten_cap)}. "
            f"At current price of ${_fmt(self.r.current_price)}, "
            f"margin of safety vs DCF is {_pct((mos_dcf or 0) * 100)} "
            f"and vs Graham is {_pct((mos_graham or 0) * 100)}. "
            f"Trading multiples: P/E {_fmt(pe, 'x')} ({pe_tier_en}), P/B {_fmt(pb, 'x')}, "
            f"P/S {_fmt(ps, 'x')}, EV/EBITDA {_fmt(ev_ebitda, 'x')}, EV/FCF {_fmt(ev_fcf, 'x')}."
            f"{peg_note_en} "
            f"Yields: earnings yield {_pct(earnings_yield)}, FCF yield {_pct(fcf_yield)}. "
            f"Reverse DCF implies market expects {_pct((implied_g or 0) * 100)} annual growth for 5 years. "
            f"Discount rate assumptions: WACC {_pct(wacc)}, cost of equity {_pct(cost_equity)}."
        )

        content_th = (
            f"การประเมินมูลค่าหลายวิธีให้ผลต่างกัน: "
            f"**DCF สองขั้น: ${_fmt(dcf)}**, "
            f"Owner Earnings DCF: ${_fmt(oe_dcf)}, "
            f"Graham Number: ${_fmt(graham)}, "
            f"Ten Cap (Buffett): ${_fmt(ten_cap)} "
            f"ณ ราคาปัจจุบัน ${_fmt(self.r.current_price)} "
            f"Margin of safety เทียบ DCF = {_pct((mos_dcf or 0) * 100)} "
            f"เทียบ Graham = {_pct((mos_graham or 0) * 100)} "
            f"Multiples: P/E {_fmt(pe, 'x')} ({pe_tier_th}) · P/B {_fmt(pb, 'x')} · "
            f"P/S {_fmt(ps, 'x')} · EV/EBITDA {_fmt(ev_ebitda, 'x')} · EV/FCF {_fmt(ev_fcf, 'x')}"
            f"{peg_note_th} "
            f"Yield: Earnings yield {_pct(earnings_yield)} · FCF yield {_pct(fcf_yield)} "
            f"Reverse DCF บ่งชี้ว่าตลาดคาดว่าบริษัทจะเติบโต {_pct((implied_g or 0) * 100)} ต่อปีเป็นเวลา 5 ปี "
            f"สมมติฐาน: WACC {_pct(wacc)} · Cost of Equity {_pct(cost_equity)}"
        )

        return {
            "id": "valuation_deep",
            "title_en": "Valuation Deep Dive",
            "title_th": "การประเมินมูลค่าเชิงลึก",
            "content_en": content_en,
            "content_th": content_th,
            "score": self._valuation_score(mos_dcf, peg, pe),
            "metrics_used": ["P/E", "PEG", "P/B", "P/S", "EV/EBITDA", "EV/FCF",
                             "FCF Yield", "DCF IV", "Owner Earnings DCF", "Graham",
                             "Ten Cap", "MoS (DCF)", "Implied Growth", "WACC"],
        }

    # ═══════════════════════════════════════════════════════
    # SECTION 7: Financial Health (Altman/Piotroski/Beneish)
    # ═══════════════════════════════════════════════════════
    def _financial_health(self) -> dict:
        q = self.latest.get("quality", {})

        z = q.get("Altman Z-Score")
        z_priv = q.get("Altman Z' Score (Private)")
        f = q.get("Piotroski F-Score")
        m = q.get("Beneish M-Score")
        sloan = q.get("Sloan Accruals")

        # Individual F-Score flags
        flags = {k.replace("F-Score: ", ""): v for k, v in q.items()
                 if k.startswith("F-Score:")}

        self.metrics_used += ["Altman Z-Score", "Altman Z' Score (Private)",
                              "Piotroski F-Score", "Beneish M-Score", "Sloan Accruals"]
        self.metrics_used += list(flags.keys())

        # Interpretations
        z_zone_en, z_zone_th = _tier(z, [
            (3.0, "SAFE zone", "โซนปลอดภัย"),
            (1.81, "GREY zone (monitor)", "โซนเทา (ควรระวัง)"),
            (0, "DISTRESS zone", "โซนอันตราย"),
        ])

        f_zone_en, f_zone_th = _tier(f, [
            (8, "excellent (8-9)", "ยอดเยี่ยม (8-9)"),
            (5, "adequate (5-7)", "พอใช้ (5-7)"),
            (0, "weak (0-4)", "อ่อนแอ (0-4)"),
        ])

        m_note_en = ""
        m_note_th = ""
        if m is not None:
            if m < -2.22:
                m_note_en = f" Beneish M-Score of {_fmt(m)} suggests low probability of earnings manipulation."
                m_note_th = f" Beneish M-Score {_fmt(m)} บ่งชี้โอกาสต่ำที่จะมีการตกแต่งงบ"
            elif m > -1.78:
                m_note_en = f" Beneish M-Score of {_fmt(m)} raises manipulation concerns — investigate further."
                m_note_th = f" Beneish M-Score {_fmt(m)} มีสัญญาณการตกแต่งงบ ควรวิเคราะห์เพิ่ม"

        # F-Score flag breakdown
        passed_flags = [k for k, v in flags.items() if v == 1]
        failed_flags = [k for k, v in flags.items() if v == 0]

        content_en = (
            f"**Altman Z-Score: {_fmt(z)}** ({z_zone_en}). "
            f"Private company variant Z': {_fmt(z_priv)}. "
            f"**Piotroski F-Score: {_fmt(f, decimals=0)}/9** ({f_zone_en}). "
        )
        if passed_flags:
            content_en += f"Passed tests: {', '.join(passed_flags[:5])}"
            if len(passed_flags) > 5:
                content_en += f" and {len(passed_flags) - 5} more"
            content_en += ". "
        if failed_flags:
            content_en += f"Failed tests: {', '.join(failed_flags)}."
        content_en += (
            f" Sloan Accruals ratio of {_fmt(sloan)} — "
            f"{'low (high earnings quality)' if abs(sloan or 0) < 0.05 else 'elevated'}. "
            f"{m_note_en}"
        )

        content_th = (
            f"**Altman Z-Score: {_fmt(z)}** ({z_zone_th}) "
            f"Z' สำหรับบริษัทเอกชน: {_fmt(z_priv)} "
            f"**Piotroski F-Score: {_fmt(f, decimals=0)}/9** ({f_zone_th}) "
        )
        if passed_flags:
            content_th += f"ผ่านการทดสอบ: {', '.join(passed_flags[:5])}"
            if len(passed_flags) > 5:
                content_th += f" และอีก {len(passed_flags) - 5} รายการ"
            content_th += " "
        if failed_flags:
            content_th += f"ไม่ผ่าน: {', '.join(failed_flags)} "
        content_th += (
            f"Sloan Accruals {_fmt(sloan)} — "
            f"{'ต่ำ (คุณภาพกำไรสูง)' if abs(sloan or 0) < 0.05 else 'สูง (ควรตรวจสอบ)'}"
            f"{m_note_th}"
        )

        return {
            "id": "financial_health",
            "title_en": "Financial Health Scores",
            "title_th": "คะแนนสุขภาพทางการเงิน",
            "content_en": content_en,
            "content_th": content_th,
            "scores": {
                "altman_z": z,
                "altman_z_zone_en": z_zone_en,
                "altman_z_zone_th": z_zone_th,
                "piotroski_f": f,
                "beneish_m": m,
                "f_flags": flags,
            },
            "score": self._health_score(z, f, m),
            "metrics_used": ["Altman Z", "Altman Z'", "Piotroski F (+9 flags)",
                             "Beneish M", "Sloan Accruals"],
        }

    # ═══════════════════════════════════════════════════════
    # SECTION 8: Balance Sheet Strength
    # ═══════════════════════════════════════════════════════
    def _balance_sheet(self) -> dict:
        lev = self.latest.get("leverage", {})
        liq = self.latest.get("liquidity", {})
        risk = self.latest.get("risk", {})

        de = lev.get("Debt to Equity (D/E)")
        da = lev.get("Debt to Assets (D/A)")
        net_debt = lev.get("Net Debt")
        net_debt_ebitda = lev.get("Net Debt to EBITDA")
        interest_cov = lev.get("Interest Coverage (EBIT)")

        cr = liq.get("Current Ratio")
        qr = liq.get("Quick Ratio (Acid Test)")
        cash_r = liq.get("Cash Ratio")
        nwc = liq.get("Net Working Capital")

        cash_runway = risk.get("Cash Runway (Years)")

        self.metrics_used += ["Debt to Equity (D/E)", "Debt to Assets (D/A)", "Net Debt",
                              "Net Debt to EBITDA", "Interest Coverage (EBIT)",
                              "Current Ratio", "Quick Ratio (Acid Test)", "Cash Ratio",
                              "Net Working Capital"]

        de_tier_en, de_tier_th = _tier(de, [
            (2.0, "high leverage (>2x)", "หนี้สูง (>2x)"),
            (1.0, "moderate leverage (1-2x)", "หนี้ปานกลาง (1-2x)"),
            (0.5, "conservative (0.5-1x)", "หนี้อนุรักษ์ (0.5-1x)"),
            (0, "very low debt (<0.5x)", "หนี้ต่ำมาก (<0.5x)"),
        ])
        cr_tier_en, cr_tier_th = _tier(cr, [
            (2.0, "strong liquidity", "สภาพคล่องแข็งแกร่ง"),
            (1.5, "healthy liquidity", "สภาพคล่องดี"),
            (1.0, "adequate liquidity", "สภาพคล่องพอใช้"),
            (0, "liquidity concern", "สภาพคล่องน่ากังวล"),
        ])

        content_en = (
            f"Capital structure: Debt-to-equity of {_fmt(de, 'x')} classifies the company "
            f"as {de_tier_en}. Total debt to assets is {_pct(da)}, "
            f"with net debt of {_fmt(net_debt, '$')} ({_fmt(net_debt_ebitda, 'x')} of EBITDA). "
            f"Interest coverage of {_fmt(interest_cov, 'x')} is "
            f"{'exceptional' if (interest_cov or 0) > 20 else 'strong' if (interest_cov or 0) > 5 else 'adequate' if (interest_cov or 0) > 2 else 'concerning'}. "
            f"Liquidity: Current ratio of {_fmt(cr, 'x')} indicates {cr_tier_en}, "
            f"quick ratio {_fmt(qr, 'x')}, cash ratio {_fmt(cash_r, 'x')}. "
            f"Net working capital of {_fmt(nwc, '$')}. "
        )
        if cash_runway is not None:
            content_en += f"Cash runway at current burn rate: {_fmt(cash_runway)} years."

        content_th = (
            f"โครงสร้างเงินทุน: D/E {_fmt(de, 'x')} จัดเป็น{de_tier_th} "
            f"หนี้ต่อสินทรัพย์รวม {_pct(da)} · Net debt {_fmt(net_debt, ' USD')} "
            f"({_fmt(net_debt_ebitda, 'x')} ของ EBITDA) "
            f"Interest coverage {_fmt(interest_cov, 'x')} จัดเป็น"
            f"{'ยอดเยี่ยม' if (interest_cov or 0) > 20 else 'แข็งแกร่ง' if (interest_cov or 0) > 5 else 'พอใช้' if (interest_cov or 0) > 2 else 'น่ากังวล'} "
            f"สภาพคล่อง: Current ratio {_fmt(cr, 'x')} บ่งชี้{cr_tier_th} · "
            f"Quick ratio {_fmt(qr, 'x')} · Cash ratio {_fmt(cash_r, 'x')} "
            f"เงินทุนหมุนเวียนสุทธิ {_fmt(nwc, ' USD')} "
        )
        if cash_runway is not None:
            content_th += f"Cash runway ที่อัตรา burn ปัจจุบัน: {_fmt(cash_runway)} ปี"

        return {
            "id": "balance_sheet",
            "title_en": "Balance Sheet Strength",
            "title_th": "ความแข็งแกร่งของงบดุล",
            "content_en": content_en,
            "content_th": content_th,
            "score": self._balance_sheet_score(de, cr, interest_cov),
            "metrics_used": ["D/E", "D/A", "Net Debt", "Net Debt/EBITDA",
                             "Interest Coverage", "Current Ratio", "Quick Ratio",
                             "Cash Ratio", "NWC", "Cash Runway"],
        }

    # ═══════════════════════════════════════════════════════
    # SECTION 9: Sector-Specific (conditional)
    # ═══════════════════════════════════════════════════════
    def _sector_specific(self) -> dict | None:
        semi = self.latest.get("semiconductor", {})
        saas = self.latest.get("software_saas", {})
        bank = self.latest.get("banking", {})
        reit = self.latest.get("reit", {})
        insur = self.latest.get("insurance", {})

        is_semi = semi.get("_is_semi", 0) == 1
        is_saas = saas.get("_is_saas", 0) == 1
        is_bank = bank.get("_is_bank", 0) == 1
        is_reit = reit.get("_is_reit", 0) == 1
        is_insur = insur.get("_is_insurance", 0) == 1

        if not any([is_semi, is_saas, is_bank, is_reit, is_insur]):
            return None

        parts_en = []
        parts_th = []
        metrics_used = []

        if is_semi:
            gm = semi.get("Gross Margin (Semi)")
            rd_pct = semi.get("R&D as % Revenue")
            capex_int = semi.get("CapEx Intensity")
            inv_days = semi.get("Inventory Days")
            parts_en.append(
                f"**Semiconductor metrics**: Gross margin {_pct(gm)}, "
                f"R&D intensity {_pct(rd_pct)}, CapEx intensity {_pct(capex_int)}. "
                f"Inventory days {_fmt(inv_days)} — {'lean' if (inv_days or 0) < 60 else 'watchful' if (inv_days or 0) < 120 else 'high (cycle risk)'}."
            )
            parts_th.append(
                f"**เมตริกอุตสาหกรรมเซมิ**: Gross margin {_pct(gm)} · "
                f"R&D {_pct(rd_pct)} ของรายได้ · CapEx intensity {_pct(capex_int)} "
                f"Inventory days {_fmt(inv_days)} — {'ต่ำ' if (inv_days or 0) < 60 else 'ปกติ' if (inv_days or 0) < 120 else 'สูง (เสี่ยงวัฏจักร)'}"
            )
            metrics_used += ["Semi Gross Margin", "R&D %", "CapEx Intensity", "Inventory Days"]

        if is_saas:
            rule40 = saas.get("Rule of 40 Score")
            magic = saas.get("Magic Number")
            rev_g = saas.get("Revenue Growth Rate")
            op_m = saas.get("Operating Margin (SaaS)")
            parts_en.append(
                f"**SaaS metrics**: Rule of 40 score {_fmt(rule40)} "
                f"(Growth {_pct(rev_g)} + Op Margin {_pct(op_m)}). "
                f"Magic Number {_fmt(magic)} — "
                f"{'excellent sales efficiency' if (magic or 0) > 1 else 'moderate' if (magic or 0) > 0.5 else 'inefficient sales spend'}."
            )
            parts_th.append(
                f"**เมตริก SaaS**: Rule of 40 = {_fmt(rule40)} "
                f"(Growth {_pct(rev_g)} + Op Margin {_pct(op_m)}) "
                f"Magic Number {_fmt(magic)} — "
                f"{'ประสิทธิภาพขายยอดเยี่ยม' if (magic or 0) > 1 else 'ปานกลาง' if (magic or 0) > 0.5 else 'ค่าใช้จ่ายขายไม่มีประสิทธิภาพ'}"
            )
            metrics_used += ["Rule of 40", "Magic Number", "SaaS Rev Growth", "SaaS Op Margin"]

        if is_bank:
            nim = bank.get("Net Interest Margin (NIM)")
            car = bank.get("Capital Adequacy Ratio (CAR)")
            npl = bank.get("NPL Ratio")
            ldr = bank.get("Loan to Deposit Ratio (LDR)")
            parts_en.append(
                f"**Banking metrics**: NIM {_pct(nim)}, CAR {_pct(car)}, "
                f"NPL ratio {_pct(npl)}, LDR {_pct(ldr)}."
            )
            parts_th.append(
                f"**เมตริกธนาคาร**: NIM {_pct(nim)} · CAR {_pct(car)} · "
                f"NPL ratio {_pct(npl)} · LDR {_pct(ldr)}"
            )
            metrics_used += ["NIM", "CAR", "NPL Ratio", "LDR"]

        if is_reit:
            ffo = reit.get("Funds From Operations (FFO)")
            affo = reit.get("Adjusted FFO (AFFO)")
            p_ffo = reit.get("P/FFO Multiple")
            ffo_yield = reit.get("FFO Yield")
            parts_en.append(
                f"**REIT metrics**: FFO {_fmt(ffo, '$')}, AFFO {_fmt(affo, '$')}, "
                f"P/FFO {_fmt(p_ffo, 'x')}, FFO yield {_pct(ffo_yield)}."
            )
            parts_th.append(
                f"**เมตริก REIT**: FFO {_fmt(ffo, ' USD')} · AFFO {_fmt(affo, ' USD')} · "
                f"P/FFO {_fmt(p_ffo, 'x')} · FFO yield {_pct(ffo_yield)}"
            )
            metrics_used += ["FFO", "AFFO", "P/FFO", "FFO Yield"]

        if is_insur:
            combined = insur.get("Combined Ratio")
            loss = insur.get("Loss Ratio")
            uw = insur.get("Underwriting Margin")
            parts_en.append(
                f"**Insurance metrics**: Combined ratio {_pct(combined)} "
                f"{'(profitable underwriting)' if (combined or 100) < 100 else '(underwriting loss)'}, "
                f"loss ratio {_pct(loss)}, underwriting margin {_pct(uw)}."
            )
            parts_th.append(
                f"**เมตริกประกัน**: Combined ratio {_pct(combined)} "
                f"{'(รับประกันมีกำไร)' if (combined or 100) < 100 else '(รับประกันขาดทุน)'} · "
                f"Loss ratio {_pct(loss)} · UW margin {_pct(uw)}"
            )
            metrics_used += ["Combined Ratio", "Loss Ratio", "UW Margin"]

        self.metrics_used += metrics_used

        return {
            "id": "sector_specific",
            "title_en": "Industry-Specific Analysis",
            "title_th": "การวิเคราะห์เฉพาะอุตสาหกรรม",
            "content_en": " ".join(parts_en),
            "content_th": " ".join(parts_th),
            "metrics_used": metrics_used,
        }

    # ═══════════════════════════════════════════════════════
    # SECTION 10: Risk Factors
    # ═══════════════════════════════════════════════════════
    def _risk_factors(self) -> dict:
        risks_en = []
        risks_th = []

        # Debt risk
        de = self.latest.get("leverage", {}).get("Debt to Equity (D/E)")
        if de is not None and de > 1.5:
            risks_en.append(f"⚠️ High leverage: D/E of {_fmt(de, 'x')} exceeds 1.5x threshold")
            risks_th.append(f"⚠️ หนี้สูง: D/E {_fmt(de, 'x')} เกิน 1.5 เท่า")

        # Interest coverage
        ic = self.latest.get("leverage", {}).get("Interest Coverage (EBIT)")
        if ic is not None and ic < 3:
            risks_en.append(f"⚠️ Low interest coverage: {_fmt(ic, 'x')} (< 3x threshold)")
            risks_th.append(f"⚠️ Interest coverage ต่ำ: {_fmt(ic, 'x')} (ต่ำกว่า 3 เท่า)")

        # Liquidity
        cr = self.latest.get("liquidity", {}).get("Current Ratio")
        if cr is not None and cr < 1:
            risks_en.append(f"⚠️ Weak liquidity: current ratio {_fmt(cr, 'x')} < 1x")
            risks_th.append(f"⚠️ สภาพคล่องอ่อน: current ratio {_fmt(cr, 'x')} < 1 เท่า")

        # Altman Z
        z = self.latest.get("quality", {}).get("Altman Z-Score")
        if z is not None and z < 1.81:
            risks_en.append(f"⚠️ Altman Z-Score in distress zone: {_fmt(z)}")
            risks_th.append(f"⚠️ Altman Z-Score อยู่ในโซนอันตราย: {_fmt(z)}")

        # Piotroski low
        f = self.latest.get("quality", {}).get("Piotroski F-Score")
        if f is not None and f < 4:
            risks_en.append(f"⚠️ Weak Piotroski F-Score: {_fmt(f, decimals=0)}/9")
            risks_th.append(f"⚠️ Piotroski F-Score อ่อน: {_fmt(f, decimals=0)}/9")

        # Earnings quality
        ocf_ni = self.latest.get("cash_flow", {}).get("OCF to Net Income")
        if ocf_ni is not None and ocf_ni < 0.7:
            risks_en.append(f"⚠️ Low earnings quality: OCF/NI = {_fmt(ocf_ni)}")
            risks_th.append(f"⚠️ คุณภาพกำไรต่ำ: OCF/NI = {_fmt(ocf_ni)}")

        # Beneish
        m = self.latest.get("quality", {}).get("Beneish M-Score")
        if m is not None and m > -1.78:
            risks_en.append(f"⚠️ Beneish M-Score raises manipulation concerns: {_fmt(m)}")
            risks_th.append(f"⚠️ Beneish M-Score ส่งสัญญาณตกแต่งงบ: {_fmt(m)}")

        # Negative growth
        rev_g = self.latest.get("growth", {}).get("Revenue Growth YoY")
        if rev_g is not None and rev_g < -5:
            risks_en.append(f"⚠️ Declining revenue: {_pct(rev_g)} YoY")
            risks_th.append(f"⚠️ รายได้หดตัว: {_pct(rev_g)} YoY")

        # Valuation risk
        mos = self.latest.get("intrinsic_value", {}).get("Margin of Safety (DCF)")
        if mos is not None and mos < -0.3:
            risks_en.append(f"⚠️ Trading significantly above intrinsic value: {_pct((-mos) * 100)} premium")
            risks_th.append(f"⚠️ ราคาสูงกว่ามูลค่าจริงมาก: premium {_pct((-mos) * 100)}")

        # P/E extreme
        pe = self.latest.get("valuation", {}).get("P/E Ratio")
        if pe is not None and pe > 40:
            risks_en.append(f"⚠️ Elevated P/E multiple: {_fmt(pe, 'x')}")
            risks_th.append(f"⚠️ P/E สูง: {_fmt(pe, 'x')}")

        if not risks_en:
            risks_en.append("✓ No major risk flags detected across financial metrics")
            risks_th.append("✓ ไม่พบสัญญาณเสี่ยงสำคัญจากอัตราส่วนทางการเงิน")

        return {
            "id": "risk_factors",
            "title_en": "Risk Factors",
            "title_th": "ปัจจัยความเสี่ยง",
            "content_en": "\n".join(risks_en),
            "content_th": "\n".join(risks_th),
            "risk_count": sum(1 for r in risks_en if r.startswith("⚠️")),
            "metrics_used": ["D/E", "Interest Coverage", "Current Ratio", "Altman Z",
                             "Piotroski F", "OCF/NI", "Beneish M", "Revenue Growth",
                             "MoS", "P/E"],
        }

    # ═══════════════════════════════════════════════════════
    # SECTION 11: Bull / Bear Cases
    # ═══════════════════════════════════════════════════════
    def _bull_bear_cases(self) -> dict:
        bull_en, bear_en = [], []
        bull_th, bear_th = [], []

        prof = self.latest.get("profitability", {})
        val = self.latest.get("valuation", {})
        iv = self.latest.get("intrinsic_value", {})
        q = self.latest.get("quality", {})
        buffett = self.latest.get("buffett", {})
        g = self.latest.get("growth", {})
        cf = self.latest.get("cash_flow", {})
        lev = self.latest.get("leverage", {})

        # Bull points
        roe = prof.get("ROE")
        if roe and roe > 20:
            bull_en.append(f"✓ Exceptional ROE of {_pct(roe)} indicates efficient capital use")
            bull_th.append(f"✓ ROE ยอดเยี่ยม {_pct(roe)} บ่งชี้การใช้ทุนที่มีประสิทธิภาพ")

        moat = buffett.get("Moat Score (0-4)")
        if moat and moat >= 3:
            bull_en.append(f"✓ Strong moat characteristics ({moat}/4 signals)")
            bull_th.append(f"✓ มีลักษณะคูเมืองแข็งแกร่ง ({moat}/4)")

        z = q.get("Altman Z-Score")
        if z and z > 3:
            bull_en.append(f"✓ Altman Z-Score of {_fmt(z)} indicates financial safety")
            bull_th.append(f"✓ Altman Z-Score {_fmt(z)} บ่งชี้ความปลอดภัยทางการเงิน")

        rev_g = g.get("Revenue Growth YoY")
        if rev_g and rev_g > 15:
            bull_en.append(f"✓ Strong revenue growth of {_pct(rev_g)} YoY")
            bull_th.append(f"✓ รายได้เติบโตแข็งแกร่ง {_pct(rev_g)} YoY")

        mos = iv.get("Margin of Safety (DCF)")
        if mos and mos > 0.15:
            bull_en.append(f"✓ Trading at {_pct(mos * 100)} discount to DCF intrinsic value")
            bull_th.append(f"✓ ราคาต่ำกว่า DCF {_pct(mos * 100)} (มี margin of safety)")

        cash_conv = buffett.get("Cash Conversion Ratio")
        if cash_conv and cash_conv > 1:
            bull_en.append(f"✓ Cash conversion of {_fmt(cash_conv)} confirms high-quality earnings")
            bull_th.append(f"✓ Cash conversion {_fmt(cash_conv)} ยืนยันกำไรคุณภาพสูง")

        de = lev.get("Debt to Equity (D/E)")
        if de is not None and de < 0.5:
            bull_en.append(f"✓ Conservative capital structure (D/E {_fmt(de, 'x')})")
            bull_th.append(f"✓ โครงสร้างทุนอนุรักษ์ (D/E {_fmt(de, 'x')})")

        # Bear points
        if mos is not None and mos < -0.2:
            bear_en.append(f"✗ Trading {_pct((-mos) * 100)} above intrinsic value")
            bear_th.append(f"✗ ราคาสูงกว่ามูลค่าจริง {_pct((-mos) * 100)}")

        pe = val.get("P/E Ratio")
        if pe and pe > 35:
            bear_en.append(f"✗ Elevated P/E multiple of {_fmt(pe, 'x')}")
            bear_th.append(f"✗ P/E สูง {_fmt(pe, 'x')}")

        if rev_g is not None and rev_g < 0:
            bear_en.append(f"✗ Revenue declining {_pct(rev_g)} YoY")
            bear_th.append(f"✗ รายได้หดตัว {_pct(rev_g)} YoY")

        if de is not None and de > 1.5:
            bear_en.append(f"✗ High leverage (D/E {_fmt(de, 'x')})")
            bear_th.append(f"✗ หนี้สูง (D/E {_fmt(de, 'x')})")

        if z is not None and z < 1.81:
            bear_en.append(f"✗ Altman Z-Score in distress: {_fmt(z)}")
            bear_th.append(f"✗ Altman Z อยู่ในโซนอันตราย: {_fmt(z)}")

        ic = lev.get("Interest Coverage (EBIT)")
        if ic is not None and ic < 3:
            bear_en.append(f"✗ Weak interest coverage: {_fmt(ic, 'x')}")
            bear_th.append(f"✗ Interest coverage อ่อน: {_fmt(ic, 'x')}")

        f = q.get("Piotroski F-Score")
        if f is not None and f < 4:
            bear_en.append(f"✗ Low Piotroski F-Score: {_fmt(f, decimals=0)}/9")
            bear_th.append(f"✗ Piotroski F ต่ำ: {_fmt(f, decimals=0)}/9")

        # Pad if empty
        if not bull_en:
            bull_en.append("No strong bull signals from current financial ratios")
            bull_th.append("ยังไม่มีสัญญาณ bull ที่แข็งแกร่งจากอัตราส่วนปัจจุบัน")
        if not bear_en:
            bear_en.append("No major bear signals from current financial ratios")
            bear_th.append("ไม่พบสัญญาณ bear สำคัญจากอัตราส่วนปัจจุบัน")

        return {
            "id": "bull_bear",
            "title_en": "Bull Case vs Bear Case",
            "title_th": "มุมมองขาขึ้น (Bull) vs ขาลง (Bear)",
            "bull_case_en": bull_en,
            "bull_case_th": bull_th,
            "bear_case_en": bear_en,
            "bear_case_th": bear_th,
        }

    # ═══════════════════════════════════════════════════════
    # SECTION 12: Verdict
    # ═══════════════════════════════════════════════════════
    def _verdict(self) -> dict:
        r = self.r

        # Suitable investor type
        rev_g = self.latest.get("growth", {}).get("Revenue Growth YoY") or 0
        div_yield = self.latest.get("dividend", {}).get("Dividend Yield") or 0
        volatility = self.latest.get("risk", {}).get("Annualized Volatility") or 0

        investor_types_en = []
        investor_types_th = []

        if rev_g > 15:
            investor_types_en.append("growth investors")
            investor_types_th.append("นักลงทุนเน้นเติบโต")
        if div_yield > 2:
            investor_types_en.append("income seekers")
            investor_types_th.append("นักลงทุนเน้นเงินปันผล")
        if r.composite_score > 60 and volatility < 30:
            investor_types_en.append("long-term investors")
            investor_types_th.append("นักลงทุนระยะยาว")
        if volatility > 50:
            investor_types_en.append("(caution: high volatility)")
            investor_types_th.append("(ระวัง: ความผันผวนสูง)")

        content_en = (
            f"**Verdict: {r.signal}** (Composite score {r.composite_score}/100). "
            f"This analysis draws from {r.total_ratios} financial ratios across "
            f"{len(r.categories_computed)} categories. "
            f"Sub-scores: Profitability {r.sub_scores.get('profitability', 0)}, "
            f"Valuation {r.sub_scores.get('valuation', 0)}, "
            f"Quality {r.sub_scores.get('quality', 0)}, "
            f"Liquidity {r.sub_scores.get('liquidity', 0)}, "
            f"Leverage {r.sub_scores.get('leverage', 0)}, "
            f"Growth {r.sub_scores.get('growth', 0)}. "
        )
        if investor_types_en:
            content_en += f"This profile may suit {', '.join(investor_types_en)}. "
        content_en += (
            "**What to watch**: Continued growth trajectory, capital allocation discipline, "
            "margin sustainability, and any deterioration in earnings quality (OCF/NI ratio). "
            "**Reminder**: Financial ratios are one input among many — pair with qualitative "
            "assessment of management, competitive dynamics, and macro conditions."
        )

        content_th = (
            f"**คำวินิจฉัย: {r.signal_th}** (คะแนนรวม {r.composite_score}/100) "
            f"การวิเคราะห์นี้ใช้ {r.total_ratios} อัตราส่วนจาก "
            f"{len(r.categories_computed)} หมวดหมู่ "
            f"คะแนนย่อย: ความสามารถทำกำไร {r.sub_scores.get('profitability', 0)} · "
            f"การประเมินมูลค่า {r.sub_scores.get('valuation', 0)} · "
            f"คุณภาพ {r.sub_scores.get('quality', 0)} · "
            f"สภาพคล่อง {r.sub_scores.get('liquidity', 0)} · "
            f"หนี้สิน {r.sub_scores.get('leverage', 0)} · "
            f"การเติบโต {r.sub_scores.get('growth', 0)} "
        )
        if investor_types_th:
            content_th += f"เหมาะกับ: {', '.join(investor_types_th)} "
        content_th += (
            "**สิ่งที่ควรจับตา**: การเติบโตต่อเนื่อง วินัยการจัดสรรทุน "
            "ความยั่งยืนของมาร์จิ้น และคุณภาพกำไร (ratio OCF/NI) "
            "**หมายเหตุ**: อัตราส่วนทางการเงินเป็นเพียงข้อมูลอย่างหนึ่ง — "
            "ควรใช้ร่วมกับการประเมินคุณภาพผู้บริหาร คู่แข่ง และภาพเศรษฐกิจมหภาค"
        )

        return {
            "id": "verdict",
            "title_en": "Verdict & What to Watch",
            "title_th": "คำวินิจฉัยและสิ่งที่ควรจับตา",
            "content_en": content_en,
            "content_th": content_th,
        }

    # ═══════════════════════════════════════════════════════
    # Section scoring helpers
    # ═══════════════════════════════════════════════════════
    def _quality_score(self, values: list[float | None]) -> int:
        # Simple average of normalized values
        return int(self.r.sub_scores.get("profitability", 50) * 0.5 +
                   self.r.sub_scores.get("quality", 50) * 0.5)

    def _profitability_score(self, m: dict) -> int:
        return int(self.r.sub_scores.get("profitability", 50))

    def _growth_score(self, values: list) -> int:
        return int(self.r.sub_scores.get("growth", 50))

    def _cash_score(self, ocf_ni, fcf_margin, accrual) -> int:
        score = 50
        if ocf_ni and ocf_ni > 1: score += 15
        if fcf_margin and fcf_margin > 15: score += 15
        if accrual and abs(accrual) < 0.05: score += 10
        return min(100, score)

    def _valuation_score(self, mos, peg, pe) -> int:
        return int(self.r.sub_scores.get("valuation", 50))

    def _health_score(self, z, f, m) -> int:
        score = 50
        if z and z > 3: score += 20
        elif z and z > 1.81: score += 5
        if f and f >= 7: score += 15
        elif f and f >= 5: score += 5
        if m and m < -2.22: score += 15
        return min(100, score)

    def _balance_sheet_score(self, de, cr, ic) -> int:
        return int((self.r.sub_scores.get("leverage", 50) +
                    self.r.sub_scores.get("liquidity", 50)) / 2)

    # ═══════════════════════════════════════════════════════
    # Markdown rendering
    # ═══════════════════════════════════════════════════════
    def _render_markdown(self, sections: list[dict], lang: str = "en") -> str:
        """Render all sections as a single markdown document."""
        r = self.r
        title_key = f"title_{lang}"
        content_key = f"content_{lang}"

        lines = []
        header = ("# Deep Analysis Report" if lang == "en"
                  else "# รายงานการวิเคราะห์เชิงลึก")
        lines.append(f"{header}: **{r.symbol}** ({r.name})")
        lines.append("")
        lines.append(f"> {'Signal' if lang == 'en' else 'สัญญาณ'}: "
                     f"**{r.signal if lang == 'en' else r.signal_th}** · "
                     f"{'Score' if lang == 'en' else 'คะแนน'}: **{r.composite_score}/100** · "
                     f"{'Analysis draws from' if lang == 'en' else 'วิเคราะห์จาก'} "
                     f"**{len(set(self.metrics_used))} / {r.total_ratios}** "
                     f"{'ratios' if lang == 'en' else 'อัตราส่วน'}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for i, sec in enumerate(sections, 1):
            title = sec.get(title_key, sec.get("title_en", ""))
            lines.append(f"## {i}. {title}")

            if "content_en" in sec or "content_th" in sec:
                content = sec.get(content_key, sec.get("content_en", ""))
                lines.append("")
                lines.append(content)

            # Bull/bear special handling
            if sec["id"] == "bull_bear":
                lines.append("")
                lines.append(f"### {'Bull Case (positive factors)' if lang == 'en' else 'มุมมอง Bull (บวก)'}")
                for b in sec[f"bull_case_{lang}"]:
                    lines.append(f"- {b}")
                lines.append("")
                lines.append(f"### {'Bear Case (negative factors)' if lang == 'en' else 'มุมมอง Bear (ลบ)'}")
                for b in sec[f"bear_case_{lang}"]:
                    lines.append(f"- {b}")

            if "score" in sec:
                lines.append("")
                lines.append(f"*{'Section score' if lang == 'en' else 'คะแนนหมวดนี้'}: **{sec['score']}/100***")

            if "metrics_used" in sec and sec["metrics_used"]:
                lines.append("")
                lines.append(f"*{'Metrics analyzed' if lang == 'en' else 'อัตราส่วนที่ใช้'}: "
                             f"{', '.join(sec['metrics_used'][:10])}"
                             f"{' ...' if len(sec['metrics_used']) > 10 else ''}*")

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)


def deep_analyze(result: AnalysisResult) -> dict:
    """Convenience wrapper."""
    return DeepNarrator(result).generate()
