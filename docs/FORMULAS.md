# Formula Reference

Comprehensive reference for all 200+ formulas in Pro Stock Analyzer, organized by category.

Every formula returns `None` if any input is missing, so downstream code should always check for `None`.

---

## 1. Profitability (22 ratios)

| Ratio | Formula |
|-------|---------|
| Gross Profit Margin | (Revenue − COGS) / Revenue |
| Operating Profit Margin | Operating Income / Revenue |
| EBIT Margin | EBIT / Revenue |
| EBITDA Margin | EBITDA / Revenue |
| Net Profit Margin | Net Income / Revenue |
| Pre-Tax Margin | Pretax Income / Revenue |
| SG&A Margin | SG&A / Revenue |
| R&D Margin | R&D Expenses / Revenue |
| ROE | Net Income / Avg Shareholders' Equity |
| ROA | Net Income / Avg Total Assets |
| ROIC | NOPAT / (Debt + Equity − Cash) |
| ROCE | EBIT / (Debt + Equity − Cash) |
| Return on Sales (ROS) | Operating Income / Revenue |
| Return on Revenue | Net Income / Revenue |
| Cash ROA | OCF / Avg Total Assets |
| Cash ROE | OCF / Avg Equity |
| FCF ROA | FCF / Avg Assets |
| FCF ROE | FCF / Avg Equity |
| NOPAT | EBIT × (1 − Tax Rate) |
| EBIT | Operating Income (or NI + Interest + Tax) |
| EBITDA | EBIT + D&A |
| Invested Capital | Avg Equity + Debt − Cash |
| Effective Tax Rate | Tax Expense / Pretax Income |

## 2. Efficiency (18 ratios)

| Ratio | Formula |
|-------|---------|
| Asset Turnover | Revenue / Avg Assets |
| Fixed Asset Turnover | Revenue / Fixed Assets |
| Equity Turnover | Revenue / Avg Equity |
| Inventory Turnover | COGS / Avg Inventory |
| Receivables Turnover | Revenue / Avg AR |
| Payables Turnover | COGS / Avg AP |
| Working Capital Turnover | Revenue / Working Capital |
| DIO | 365 / Inventory Turnover |
| DSO | 365 / Receivables Turnover |
| DPO | 365 / Payables Turnover |
| CCC | DIO + DSO − DPO |
| Revenue per Employee | Revenue / Employees |
| Sales per Share | Revenue / Shares |
| Capital Intensity | Avg Assets / Revenue |
| Working Capital | CA − CL |
| Working Capital Ratio | WC / Total Assets |
| OCF to Sales | OCF / Revenue |
| CapEx to Sales | CapEx / Revenue |

## 3. Liquidity (10 ratios)

| Ratio | Formula |
|-------|---------|
| Current Ratio | Current Assets / Current Liabilities |
| Quick Ratio (Acid Test) | (Cash + STI + AR) / CL |
| Quick Ratio (Alt) | (CA − Inventory) / CL |
| Cash Ratio | Cash / CL |
| Absolute Liquidity | (Cash + STI) / CL |
| Operating Cash Flow Ratio | OCF / CL |
| Defensive Interval | Quick Assets / (Revenue / 365) |
| Net Working Capital | CA − CL |
| NWC to Assets | NWC / Total Assets |
| NWC to Sales | NWC / Revenue |

## 4. Leverage (20 ratios)

| Ratio | Formula |
|-------|---------|
| Debt to Equity | Total Debt / Total Equity |
| Debt to Assets | Total Debt / Total Assets |
| Long Term Debt to Equity | LT Debt / Equity |
| Long Term Debt to Assets | LT Debt / Assets |
| Short Term Debt to Total Debt | ST Debt / Total Debt |
| Total Liabilities to Equity | Total Liab / Equity |
| Equity Multiplier | Assets / Equity |
| Equity Ratio | Equity / Assets |
| Financial Leverage | Assets / Equity |
| Interest Coverage (EBIT) | EBIT / Interest |
| Interest Coverage (EBITDA) | EBITDA / Interest |
| Cash Interest Coverage | OCF / Interest |
| DSCR | Operating Income / Debt Service |
| Fixed Charge Coverage | (EBIT + Lease) / (Interest + Lease) |
| Net Debt | Total Debt − Cash |
| Net Debt to EBITDA | Net Debt / EBITDA |
| Net Debt to Equity | Net Debt / Equity |
| Debt to EBITDA | Debt / EBITDA |
| Times Interest Earned | EBIT / Interest |
| Cash Flow to Debt | OCF / Total Debt |

## 5. Cash Flow (22 ratios)

Absolute measures: **OCF, FCF, UFCF, Owner Earnings**  
Margins: **OCF/FCF/UFCF Margin**  
Quality: **Cash Conversion (FCF/NI), OCF/NI, OCF/EBITDA, Accrual Ratio**  
Coverage: **OCF/CL, OCF/Debt, FCF/Debt, FCF Yield**  
Reinvestment: **CapEx/OCF, CapEx/Revenue, CapEx/D&A**  
Shareholder return: **Div/OCF, Div/FCF, Buybacks/FCF, Total Return/FCF**

## 6. Growth (14 ratios)

YoY growth for: Revenue, Net Income, EPS, Operating Income, EBITDA, Gross Profit, FCF, OCF, Equity, Assets, Dividends  
Composite: **Sustainable Growth Rate (ROE × Retention), Internal Growth Rate (ROA × Retention), Retention Ratio**

## 7. Valuation (28 ratios)

Per-share: **EPS, BVPS, SPS, CFPS, FCFPS, DPS**  
Price multiples: **P/E, PEG, P/B, P/S, P/CF, P/FCF, P/Tangible Book**  
Market cap: **MC/Revenue, MC/FCF, MC/NI**  
EV multiples: **EV, EV/EBITDA, EV/EBIT, EV/Sales, EV/FCF, EV/OCF, EV/GP**  
Yields: **Earnings, FCF, Sales, Book**

## 8. Quality (16 ratios)

| Ratio | Formula |
|-------|---------|
| Altman Z-Score | 1.2A + 1.4B + 3.3C + 0.6D + 1.0E |
| Altman Z' (Private) | 0.717A + 0.847B + 3.107C + 0.420D + 0.998E |
| Piotroski F-Score | Sum of 9 binary tests |
| F-Score individual flags | (9 tests exposed individually) |
| Beneish M-Score | -4.84 + 0.92·DSRI + 0.528·GMI + 0.404·SGI |
| Sloan Accruals | (NI − OCF − ICF) / Avg Assets |
| Cash Flow to Earnings | OCF / NI |
| Accruals to Assets | (NI − OCF) / Assets |

**Altman Z zones**: >3 safe, 1.81–3 grey, <1.81 distress  
**Piotroski F zones**: 8–9 strong, 5–7 average, 0–4 weak  
**Beneish M**: <−2.22 likely clean, >−1.78 likely manipulating

## 9. Buffett (14 ratios)

| Ratio | Formula |
|-------|---------|
| Owner Earnings | NI + D&A − Maintenance CapEx (0.7 × CapEx) |
| Owner Earnings (Simple) | OCF − CapEx (= FCF) |
| Owner Earnings Growth YoY | (OE_t − OE_{t-1}) / OE_{t-1} |
| Owner Earnings Margin | OE / Revenue |
| Owner Earnings Yield | OE / Market Cap |
| Current ROE | NI / Equity |
| 10Y Avg ROE | Mean of ROE over history |
| ROE Consistency | Stddev(ROE) / Mean(ROE) |
| Cash Conversion | FCF / NI |
| Retained Earnings Growth | ΔRE / RE_{t-1} |
| BVPS Growth (10Y) | CAGR of BVPS |
| Reinvestment Rate | (CapEx + ΔWC) / NI |
| Return on Retained Earnings | ΔNI / ΔRE |
| Moat Score (0-4) | # of: ROE>15%, Cash Conv>1, GM>40%, D/E<0.5 |

## 10. Cost of Capital (8 ratios)

| Ratio | Formula |
|-------|---------|
| Risk-Free Rate | 4.5% (US 10Y Treasury) |
| Beta (Sector) | Damodaran sector defaults |
| Equity Risk Premium | 5.5% |
| Cost of Equity (CAPM) | Rf + β × ERP |
| Cost of Debt (Pre-Tax) | Interest / Avg Debt |
| Cost of Debt (After-Tax) | Cost of Debt × (1 − Tax) |
| WACC | (E/V)·Re + (D/V)·Rd·(1−T) |
| Effective Tax Rate | Tax / Pretax Income |

**Sector betas**: Technology 1.20, Healthcare 0.90, Utilities 0.55, Energy 1.25, etc.

## 11. Intrinsic Value (12 ratios)

| Method | Formula |
|--------|---------|
| DCF (two-stage) | Σ FCF_t / (1+r)^t + Terminal / (1+r)^n |
| Owner Earnings DCF | Same, using Owner Earnings instead of FCF |
| Graham Number | √(22.5 × EPS × BVPS) |
| Graham Revised | EPS × (8.5 + 2g) |
| Ten Cap | Owner Earnings × 10 / Shares |
| DDM (Gordon Growth) | D1 / (r − g) |
| Margin of Safety (DCF) | (DCF IV − Price) / DCF IV |
| Margin of Safety (Graham) | (Graham IV − Price) / Graham IV |
| Reverse DCF (Implied Growth) | Binary search: g s.t. DCF(g) = Price |
| DCF vs Current Price | DCF / Price |

**Terminal growth by sector**: Technology 3.0%, Utilities 2.0%, Energy 2.0%, etc.

## 12. Dividend (10 ratios)

DPS, Dividend Yield, Payout Ratio, Cash Payout, Coverage, Cash Coverage, Retention, Growth YoY, Div/Equity, Dividends Paid (absolute)

## 13. Risk (10 ratios)

| Ratio | Formula |
|-------|---------|
| D/E Risk Score | 0–3 based on D/E thresholds |
| Interest Coverage Warning | 1 if IC<3 else 0 |
| Cash Runway (Years) | Cash / |OCF| when OCF<0 |
| Financial Leverage | Assets / Equity |
| Annualized Volatility | Stddev of yearly returns |
| Mean Annual Return | Mean of yearly returns |
| Sharpe Ratio | (μ − Rf) / σ |
| Sortino Ratio | (μ − Rf) / Downside Deviation |
| Max Drawdown | max peak-to-trough decline % |
| Price CAGR | (P_last/P_first)^(1/years) − 1 |

## 14. Banking (12 ratios)

NIM, LDR, Deposit/Assets, Loan/Assets, CET1, CAR, Cost-to-Income, Efficiency Ratio, NPL Ratio, NPL Coverage, Bank ROA, Bank ROE

## 15. REIT (11 ratios)

FFO, AFFO, FFO/AFFO per share, P/FFO, P/AFFO, FFO Yield, AFFO Payout, Debt/Real Estate, FFO Growth YoY  
**FFO** = NI + Real Estate D&A − Gains on Sales  
**AFFO** = FFO − Maintenance CapEx − SL Rent Adj

## 16. Software/SaaS (12 ratios)

Est ARR (≈ Revenue), Revenue Growth, SaaS Gross Margin, Operating Margin, **Rule of 40** (Growth% + Op Margin%), **Magic Number** (ΔARR / S&M), S&M/R&D/G&A as % Revenue, Sales Efficiency, R&D Intensity 5Y avg

## 17. Semiconductor (9 ratios)

Gross Margin, R&D as % Revenue, R&D absolute, Revenue per Employee, Inventory Days, Inventory/Revenue, CapEx Intensity, Fab Investment approx

## 18. Insurance (9 ratios)

Loss Ratio (Claims/Premiums), Expense Ratio, **Combined Ratio** (Loss + Expense), Underwriting Margin, Investment Yield, Solvency Ratio, Reserve/Premium, Reserve/Equity
