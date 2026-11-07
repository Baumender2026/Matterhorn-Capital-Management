#!/usr/bin/env python3
"""DDM valuation workbook for Round 2: Gordon Growth Model and two-stage DDM, one sheet per stock.

    python3 scripts/build_ddm_workbook.py                          the blank template
    python3 scripts/build_ddm_workbook.py KO PEP JNJ               add stocks, or refresh their data
    python3 scripts/build_ddm_workbook.py KO --as-of 2026-11-06    prices of a given date (final numbers)
    python3 scripts/build_ddm_workbook.py KO --g1-yahoo            also reset g1 to Yahoo's average growth estimate

Writes runs/round2/inputs/DDM_valuation.xlsx (or --out). Close it in Excel first.

The workbook does the valuation with Excel formulas, so every assumption can be changed in Excel:
  Summary      one row per stock: values, margin of safety, signal, flags
  Inputs       shared by all stocks: rf (10-year Treasury), ERP, buy threshold, flag levels
  <TICKER>     data, CAPM, growth assumptions, GGM, two-stage DDM with its schedule, sensitivity grids
  Template     a blank stock sheet, to duplicate by hand
  Example NKE  the TA notebook's Nike case, which checks the formulas (GGM 23.24, two-stage 29.78; comps 19.33 on the CSV)

Each stock sheet also has the comparables from row 101, with the stock report's metrics and code (comps_from_snapshot in
build_stock_report.py): forward P/E, P/FCF and EV/EBITDA (plus five more), the n/m rule, the peer median (or average),
the implied prices and the comps value, against the DDM (the TA's undervalued / overvalued / mixed: check). A double check:
it does not change V0, the MoS or the signal. Peers (yellow) come from the stock's YAML, else PEERS below, else Yahoo's
industry list; typed peers are kept. The stock report stops if the YAML's peers, comps_stat or comps_primary differ.

A stock already in the workbook gets new data (blue cells) only: your assumptions (yellow) stay.
The formulas follow the Round 2 cheat sheet (§3-§4) and scripts/build_stock_report.py:
k = rf10 + beta x ERP, beta on SPY over 60 complete months, D0 = dividends of the last 12 months,
MoS = V0 / P0 - 1.
Payout discounted, a switch in each sheet: Dividends, or Dividends + buybacks (cheat sheet p. 2), where
D0 used = D0 + last fiscal year's buybacks / its diluted average shares, as dividend_basis in the report script.
A new sheet starts with g1 = Yahoo's average earnings growth estimate (current and next fiscal year; next year alone for
the tickers in G1_NEXT_YEAR), Dividends + buybacks and P/FCF in the comps value (the team's rule since 7 Nov 2026), and, for a company based outside the US, its country's ERP (Damodaran) typed in the
sheet. rf is the US 10-year for every stock: the tickers are US lines, so price and dividends are in USD.
"""

import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_stock_report import (COMPS_STAT_LABEL, COMPS_STATS, COMPS_USE_LABELS, HISTORY_YEARS,  # noqa: E402
                                INFO_KEYS, MULTIPLES, N_PEERS, PEER_LABELS, TA, WINDOW, comps_from_snapshot,
                                complete_month_end, fetch_fx, fred_series, fx_pairs, fx_rate, gordon,
                                methods_verdict, retry, short_name, statements_of, to_records, two_stage)

REPO = Path(__file__).resolve().parent.parent
WORKBOOK = REPO / "runs" / "round2" / "inputs" / "DDM_valuation.xlsx"

G1_DEFAULT, T_DEFAULT, G2_DEFAULT = 0.05, 5, 0.03   # as in runs/round2/inputs/_TEMPLATE.yaml
ERP_DEFAULT = 0.0446       # Damodaran, United States, country risk premiums of 5 Jan 2026 (ctryprem.html)
# Damodaran, country risk premiums of 5 Jan 2026: (total ERP, Moody's rating, country risk premium). Total ERP = mature
# market 4.23% + CRP. A new sheet of a company based in one of these countries gets its ERP in the sheet; Inputs keeps
# the US one. Another non-US country: the script says so, type its ERP in the sheet.
COUNTRY_ERP = {
    "Switzerland": (0.0423, "Aaa", 0.0000), "Germany": (0.0423, "Aaa", 0.0000), "Denmark": (0.0423, "Aaa", 0.0000),
    "United Kingdom": (0.0501, "Aa3", 0.0078), "Taiwan": (0.0501, "Aa3", 0.0078),
    "Hong Kong": (0.0501, "Aa3", 0.0078), "China": (0.0514, "A1", 0.0091),
}
ERP_DATE = "5 Jan 2026"
# Yahoo's growth estimates come from the home listing when the US line has few analysts: same company, same shares.
ESTIMATES_FROM = {"AZN": "AZN.L", "TCEHY": "0700.HK",   # AZN's NYSE page: 2-3 analysts and a GAAP base year
                  "GOOG": "GOOGL",                      # the same estimates, 7 analysts on GOOG's current year
                  "NVO": "NOVO-B.CO",                   # 7-8 analysts on the ADR, 21-22 in Copenhagen
                  "NSRGY": "NESN.SW"}                   # 3 analysts on the ADR, 15-20 in Zurich
# g1 from Yahoo's next-year earnings growth estimate alone, not the average of the current and next year: the team's
# choice of 7 Nov 2026 for the stocks added that day. Row g_yahoo of their sheets holds that estimate, so the checks on g1
# (typed or from Yahoo, the buyback flag) work as for the others.
G1_NEXT_YEAR = {"NVO", "PFE", "VZ", "PEP", "NSRGY"}
G1_NEXT_YEAR_DATE = "7 Nov 2026"
# Dividends missing from Yahoo's history of a ticker, typed from the company: {ticker: [(ex-date, amount, source)]}.
# Added only if Yahoo has no dividend within 20 days of that date, so a fixed history is not counted twice.
MISSING_DIVIDENDS = {
    "AZN": [("2026-08-06", 1.06, "AstraZeneca, H1 2026 results, 27 Jul 2026: interim USD 1.06 (79.5p), ex-dividend "
                                 "6 Aug 2026 on AZN.L; missing on Yahoo's NYSE line since the listing change")],
}
MIN_ANALYSTS = 10                                   # fewer on the page used: a warning
# Ordinary shares per ADR, so that a foreign company's buybacks per share are per ADR, like its price and dividends
ADR_SHARES = {"TSM": 5, "RHHBY": 0.125, "TCEHY": 1, "NVO": 1, "NSRGY": 1}
# Peers of the comparables, for a stock without runs/round2/inputs/<TICKER>.yaml. Proposed by Claude on 6 Nov 2026 from
# Yahoo's industry and the business, without Bloomberg RV: the team checks them on RV and types over them in the sheet.
# Left out because Yahoo's ratios are broken: Chinese ADRs (BABA, BIDU, JD, PDD, TME, NTES: EV/EBITDA of -3x to 6x, a USD EV
# over a CNY EBITDA), UMC and ASX (EV/EBITDA -0.3x and 2.4x), SAP (EV/EBITDA 322x, P/B 76x), MU (forward P/E 3.2x), ARM (155x).
PEERS = {
    "NVDA": ["AVGO", "AMD", "QCOM", "MRVL", "TXN", "ADI"],     # listed US chip designers and makers, AI and data centre first
    "MSFT": ["ORCL", "CRM", "ADBE", "NOW", "INTU", "GOOGL"],   # large US software and cloud platforms
    "GOOG": ["META", "MSFT", "AMZN", "NFLX", "RDDT", "PINS"],  # online advertising, cloud and media platforms
    "TSM":  ["INTC", "GFS", "AVGO", "TXN", "ADI", "NXPI"],     # chip makers with fabs; foundry peers on US lines (GFS, INTC)
    "META": ["GOOGL", "PINS", "RDDT", "NFLX", "AMZN", "MSFT"], # online advertising and social media
    "TCEHY": ["META", "GOOGL", "NFLX", "SE", "EA"],            # social, games, ads and payments; Chinese peers left out (above)
    "PG":   ["CL", "KMB", "CHD", "CLX", "KVUE", "UL"],         # household and personal products
    "RHHBY": ["NVS", "AZN", "MRK", "PFE", "JNJ", "SNY"],       # large pharma, Europe and US
    "ORCL": ["MSFT", "CRM", "IBM", "ADBE", "NOW", "INTU"],     # enterprise software, databases and cloud
    "AZN":  ["NVS", "MRK", "PFE", "GSK", "SNY", "ABBV"],       # large pharma, Europe and US
    "GS":   ["MS", "JPM", "BAC", "C", "JEF", "EVR"],           # investment banks and the large banks with markets arms
    "IBM":  ["ACN", "ORCL", "MSFT", "CSCO", "HPE", "CTSH"],    # IT services, software and infrastructure
    "AXP":  ["COF", "SYF", "V", "MA", "PYPL", "ALLY"],         # card issuers, networks and consumer lenders
    "QCOM": ["AVGO", "TXN", "ADI", "NXPI", "MRVL", "AMD"],     # chip designers: mobile, connectivity, auto
    # added 7 Nov 2026, same approach
    "NVO":  ["LLY", "NVS", "AZN", "SNY", "MRK", "PFE"],        # diabetes and obesity (LLY, SNY), large pharma
    "PFE":  ["MRK", "BMY", "JNJ", "ABBV", "GSK", "AZN"],       # large pharma, US and Europe
    "VZ":   ["T", "TMUS", "CMCSA", "CHTR", "BCE", "TU"],       # US telecom and cable; BCE and TU report in CAD
    "PEP":  ["KO", "KDP", "MDLZ", "MNST", "GIS", "KHC"],       # drinks and snacks
    "NSRGY": ["UL", "MDLZ", "PEP", "GIS", "KHC", "HSY"],       # packaged food; UL reports in EUR
}
PEERS_DATE = "6 Nov 2026"
PEERS_DATES = {t: "7 Nov 2026" for t in ("NVO", "PFE", "VZ", "PEP", "NSRGY")}   # PEERS_DATE for the others
G1_BOUNDS = (0.0, 0.15)            # the 5-year dividend CAGR, g1 when Yahoo has no growth estimate, is clipped to this
T_MAX = 20                                          # rows of the two-stage schedule
HIST_YEARS = 6                                      # calendar years in the dividend table
SUMMARY_ROWS = 20                                   # rows prepared in Summary; more are added when needed
DIVS, DIVS_BB = "Dividends", "Dividends + buybacks"  # the payout discounted, chosen in each stock sheet
GROWTH_YEARS = 3                                    # fiscal years for the buyback average and the growth checks

# ---------------------------------------------------------------- style

ARIAL = "Arial"
BLUE, BLACK, GREEN, NAVY, GREY = "0000FF", "000000", "008000", "1F4E79", "595959"
YELLOW, RESULT, HEAD = "FFF2CC", "E2EFDA", "F2F2F2"
GOOD, BAD, NEUTRAL = ("C6EFCE", "006100"), ("FFC7CE", "9C0006"), ("FFEB9C", "9C5700")
PRICE, PRICE3, PCT, PCT1, BETA, INT, DATE = "#,##0.00", "#,##0.000", "0.00%", "0.0%", "0.000", "0", "dd mmm yyyy"
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def fill(color):
    return PatternFill("solid", start_color=color, end_color=color)


def font(color=BLACK, bold=False, size=10, italic=False):
    return Font(name=ARIAL, size=size, bold=bold, italic=italic, color=color)


KIND = {   # font colour, bold, fill, border of each kind of value cell
    "data": (BLUE, False, None, None),
    "input": (BLUE, False, YELLOW, BOX),
    "formula": (BLACK, False, None, None),
    "link": (GREEN, False, None, None),
    "result": (BLACK, True, RESULT, BOX),
}


def put(ws, ref, value=None, kind="formula", fmt=None, bold=False):
    c = ws[ref]
    c.value = value
    color, strong, bg, border = KIND[kind]
    c.font = font(color, bold=bold or strong)
    if bg:
        c.fill = fill(bg)
    if border:
        c.border = border
    if fmt:
        c.number_format = fmt
    return c


def label(ws, ref, text, bold=False):
    ws[ref] = text
    ws[ref].font = font(bold=bold)


def note(ws, ref, text):
    ws[ref] = text
    ws[ref].font = font(GREY, size=9, italic=True)


def section(ws, row, text, cols="BCD"):
    ws[f"{cols[0]}{row}"] = text
    ws[f"{cols[0]}{row}"].font = font(NAVY, bold=True, size=11)
    for col in cols:
        ws[f"{col}{row}"].border = Border(bottom=Side(style="thin", color=NAVY))


def title(ws, text, sub):
    ws["B2"] = text
    ws["B2"].font = font(bold=True, size=12)
    note(ws, "B3", sub)


def widths(ws, spec):
    for col, w in spec.items():
        ws.column_dimensions[col].width = w


def cf_mos(ws, rng, threshold):
    """Margin of safety: green at or above the buy threshold, red below zero."""
    first = rng.split(":")[0].replace("$", "")
    ws.conditional_formatting.add(rng, FormulaRule(formula=[f"AND(ISNUMBER({first}),{first}>={threshold})"],
                                                   fill=fill(GOOD[0]), font=Font(color=GOOD[1])))
    ws.conditional_formatting.add(rng, FormulaRule(formula=[f"AND(ISNUMBER({first}),{first}<0)"],
                                                   fill=fill(BAD[0]), font=Font(color=BAD[1])))


def cf_signal(ws, rng):
    first = rng.split(":")[0].replace("$", "")
    for word, (bg, fg) in (("Buy", GOOD), ("Watch", NEUTRAL), ("Overvalued", BAD)):
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'{first}="{word}"'], fill=fill(bg), font=Font(color=fg)))


# ---------------------------------------------------------------- Inputs sheet

INP = {"as_of": "C6", "rf": "C7", "erp": "C8", "buy": "C9", "flag_up": "C10", "spread": "C11", "step": "C12"}


def inp(key):
    col, row = INP[key][0], INP[key][1:]
    return f"Inputs!${col}${row}"


ERP_NOTE = (f"Damodaran, United States, {ERP_DATE}. Country risk premiums page. A sheet of a company based outside "
            "the US types its country's ERP instead")
STEPS = [
    "1. Add stocks: python3 scripts/build_ddm_workbook.py KO PEP (from the repo root, with this file closed in Excel).",
    "    It adds one sheet per ticker and a row in Summary. Run it again for a stock already here and only the blue cells change.",
    "2. Or by hand: right-click Template > Move or Copy > Create a copy, rename it to the ticker, type the blue cells,",
    "    then type the sheet name in the Ticker column of Summary.",
    "3. In each stock sheet, check the yellow cells: the payout discounted, g1 (set to Yahoo's average earnings growth",
    "    estimate), T, g2, the method, the β override, the ERP of a non-US company, and the peers of the comps (row 101 on).",
    "4. Final numbers: run the script again with --as-of 2026-11-06 (the challenge uses the close of Friday 6 November).",
    "5. Don't insert rows or columns in the stock sheets: Summary reads fixed cells.",
]
FORMULAS = [
    "Cost of equity:  k = rf + β × ERP, with β the slope of 60 monthly excess returns on SPY",
    "Gordon Growth Model:  V0 = D0 (1 + g) / (k − g), needs k > g. For a mature company with stable growth",
    "Two-stage DDM:  V0 = Σ D0 (1 + g1)^t / (1 + k)^t for t = 1 … T  +  [D_T (1 + g2) / (k − g2)] / (1 + k)^T",
    "    For a company not yet in its normal state. g1 can be above k; g2 must be below k",
    "Margin of safety:  MoS = V0 / P0 − 1 (cheat sheet). Discount to value = 1 − P0 / V0 (Class 5, Graham)",
    "D0: dividends per share paid over the last 12 months. The first dividend discounted is D1 = D0 (1 + g)",
    "With buybacks (cheat sheet p. 2): D0 used = D0 + last fiscal year's buybacks per share. g1 is Yahoo's per-share",
    "    growth, which already contains the buybacks, so they count twice and V0 is too high: see the note next to g1",
    "Non-US companies: the tickers are US lines (price and dividends in USD), so rf stays the US 10-year and the sheet",
    f"    types its country's ERP: Damodaran, {ERP_DATE}, mature market 4.23% + country risk premium",
    "Comparables (row 101 on): price = peer median multiple × the stock's EPS, FCF or EBITDA, as the stock report. A check, not in V0",
]


def write_inputs_text(ws):
    """The ERP note and the two blocks of instructions, also rewritten in an existing workbook."""
    note(ws, f"D{INP['erp'][1:]}", ERP_NOTE)
    for first, lines, n in ((22, STEPS, 8), (31, FORMULAS, 11)):
        for i in range(n):
            ws[f"B{first + i}"] = None
        for i, text in enumerate(lines):
            label(ws, f"B{first + i}", text)


def build_inputs(ws):
    title(ws, "DDM valuation: inputs shared by all stocks",
          "Change the yellow cells. Every stock sheet and the Summary follow them.")
    widths(ws, {"A": 2, "B": 40, "C": 14, "D": 70})
    section(ws, 5, "Market and rules")
    rows = [
        ("as_of", "Price date", "data", None, DATE, "Set by the script: the latest close it used"),
        ("rf", "Risk-free rate rf, 10-year Treasury", "data", None, PCT, "FRED DGS10, set by the script"),
        ("erp", "Equity risk premium ERP", "input", ERP_DEFAULT, PCT, ERP_NOTE),
        ("buy", "Buy threshold: margin of safety at least", "input", 0.25, PCT1,
         "Class 5: buy below 80% of value, i.e. V0 / P0 − 1 ≥ 25%"),
        ("flag_up", "Red flag: upside above", "input", 0.50, PCT1,
         "Cheat sheet: on a large, mature company it is more likely a wrong input or a value trap"),
        ("spread", "Red flag: k − g2 below", "input", 0.03, PCT1, "Value very sensitive to k and g2"),
        ("step", "Step of the sensitivity grids", "input", 0.005, PCT, "For k and g, ±1 and ±2 steps"),
    ]
    for key, text, kind, value, fmt, why in rows:
        r = INP[key][1:]
        label(ws, f"B{r}", text)
        put(ws, INP[key], value, kind, fmt)
        note(ws, f"D{r}", why)

    section(ws, 14, "Legend")
    legend = [("input", 0.05, PCT, "Yellow: an assumption. Change it"),
              ("data", 1.23, PRICE, "Blue: data from Yahoo Finance or FRED, written by the script (or typed from Bloomberg)"),
              ("formula", 1.23, PRICE, "Black: a formula. Don't type over it"),
              ("link", 0.05, PCT, "Green: a link to the Inputs sheet"),
              ("result", 1.23, PRICE, "Green fill: the result, fair value and margin of safety")]
    for i, (kind, value, fmt, text) in enumerate(legend):
        r = 15 + i
        put(ws, f"C{r}", value, kind, fmt)
        label(ws, f"D{r}", text)

    section(ws, 21, "How to use it")
    section(ws, 30, "Formulas (Round 2 cheat sheet §3–§4)")
    write_inputs_text(ws)
    ws.sheet_view.showGridLines = False


# ---------------------------------------------------------------- stock sheet

# (key, label, kind, content, number format, note). content: a default for inputs, a formula for formulas,
# with {key} replaced by the absolute address of that row. "section" rows have only a title.
LEFT = [
    ("section", "Company"),
    ("ticker", "Ticker", "data", None, None, "The sheet name must match the ticker typed in Summary"),
    ("name", "Company", "data", None, None, ""),
    ("sector", "Sector / industry", "data", None, None, ""),
    ("currency", "Currency", "data", None, None, ""),
    ("as_of", "Price date", "data", None, DATE, ""),
    ("source", "Data", "data", None, None, ""),
    ("section", "Market data"),
    ("P0", "Price P0", "data", None, PRICE, "Last close, not adjusted"),
    ("D0", "Dividend D0, last 12 months", "data", None, PRICE3, "Dividends paid in the 12 months to the price date"),
    ("div_rate", "Annual dividend rate (Yahoo)", "data", None, PRICE3, "The current rate, annualised: compare with D0"),
    ("yield_", "Dividend yield D0 / P0", "formula", '=IF(N({P0})>0,{D0}/{P0},"")', PCT, ""),
    ("eps_ttm", "EPS, last 12 months", "data", None, PRICE, ""),
    ("eps_fwd", "EPS, next 12 months (consensus)", "data", None, PRICE, ""),
    ("payout", "Dividend payout D0 / EPS", "formula", '=IF(N({eps_ttm})>0,{D0}/{eps_ttm},"")', PCT1,
     "Above 100%: earnings don't cover the dividend"),
    ("roe", "ROE", "data", None, PCT1, ""),
    ("dps_cagr", "Dividend growth, last 5 years (CAGR)", "data", None, PCT, "Calendar years: see the table below"),
    ("g_yahoo", "Earnings growth estimate, Yahoo average", "data", None, PCT,
     "Average of the current and next fiscal year (Yahoo, Analysis, Growth Estimates)"),
    ("beta_calc", "β, 60 months on SPY", "data", None, BETA, "Monthly excess returns, as in the cheat sheet"),
    ("beta_yahoo", "β, Yahoo", "data", None, BETA, "Reference only"),
    ("section", "Buybacks (Yahoo, fiscal years)"),
    ("buyback_fy", "Buybacks, last fiscal year (USD m)", "data", None, "#,##0", "Repurchase Of Capital Stock, cash flow statement"),
    ("shares_fy", "Diluted average shares, same year (m)", "data", None, "#,##0.0", ""),
    ("bps", "Buybacks per share", "formula", '=IF(N({shares_fy})>0,N({buyback_fy})/{shares_fy},"")', PRICE3,
     "Added to D0 with Dividends + buybacks, as in the report script"),
    ("bps_avg", f"Buybacks per share, {GROWTH_YEARS}-year average", "data", None, PRICE3,
     "A check: buybacks are lumpy and cut first in a downturn"),
    ("shares_chg", f"Share count change per year, {GROWTH_YEARS} years", "data", None, PCT,
     "Negative: buybacks shrink the share count"),
    ("ni_growth", f"Net income growth per year, {GROWTH_YEARS} years", "data", None, PCT,
     "Total growth: compare g1 with it when buybacks are in"),
    ("section", "Cost of equity (CAPM)"),
    ("rf", "Risk-free rate rf, 10-year Treasury", "link", "=" + inp("rf"), PCT, "From Inputs"),
    ("erp", "Equity risk premium ERP", "link", "=" + inp("erp"), PCT, "From Inputs"),
    ("beta_over", "β override (optional)", "input", None, BETA, "e.g. Bloomberg BETA. Leave empty to use the 60-month β"),
    ("beta", "β used", "formula", "=IF(ISNUMBER({beta_over}),{beta_over},N({beta_calc}))", BETA, ""),
    ("k", "Cost of equity k = rf + β × ERP", "formula", "={rf}+{beta}*{erp}", PCT, ""),
    ("section", "Payout discounted"),
    ("basis", "Dividends, or dividends + buybacks", "input", DIVS_BB, None, f"{DIVS_BB} for every stock: the team's rule (cheat sheet p. 2)"),
    ("D0u", "D0 used, per share", "formula", f'=IF({{basis}}="{DIVS_BB}",{{D0}}+N({{bps}}),{{D0}})', PRICE3,
     "With buybacks: see the limitation next to g1"),
    ("payout_u", "Payout used: D0 used / EPS", "formula", '=IF(N({eps_ttm})>0,{D0u}/{eps_ttm},"")', PCT1,
     "Above 100%: earnings don't cover the payout"),
    ("g_sust", "Sustainable growth ROE × (1 − payout used)", "formula",
     '=IF(AND(ISNUMBER({roe}),ISNUMBER({payout_u})),{roe}*(1-{payout_u}),"")', PCT, "A ceiling for long-run growth"),
    ("section", "Growth assumptions"),
    ("g1", "g1, growth in stage 1", "input", G1_DEFAULT, PCT, None),     # note built in g1_note_formula()
    ("T", f"T, years in stage 1 (1–{T_MAX})", "input", T_DEFAULT, INT, "Years the company needs to reach its normal state"),
    ("g2", "g2, growth after T (terminal)", "input", G2_DEFAULT, PCT, "Below k, close to long-run economic growth"),
    ("g", "g, Gordon growth", "input", "={g2}", PCT, "Equal to g2 unless you type a number here"),
    ("method", "Method for the fair value", "input", "Two-stage", None,
     "Two-stage: not yet in its normal state. GGM: mature, stable growth"),
    ("section", "Gordon Growth Model"),
    ("D1", "D1 = D0 used × (1 + g)", "formula", "={D0u}*(1+{g})", PRICE3, ""),
    ("V_ggm", "Value V0 = D1 / (k − g)", "formula",
     '=IF(N({D0u})<=0,"n/a: no payout",IF({k}>{g},{D1}/({k}-{g}),"n/a: k ≤ g"))', PRICE, ""),
    ("mos_ggm", "Margin of safety V0 / P0 − 1", "formula",
     '=IF(AND(ISNUMBER({V_ggm}),N({P0})>0),{V_ggm}/{P0}-1,"")', PCT1, ""),
    ("disc_ggm", "Discount to value 1 − P0 / V0", "formula",
     '=IF(AND(ISNUMBER({V_ggm}),N({V_ggm})>0),1-{P0}/{V_ggm},"")', PCT1, "Class 5: buy below 80% of value = at least 20% here"),
    ("implied_g", "Growth implied by the price", "formula",
     '=IF(N({P0})>0,({k}*{P0}-{D0u})/({P0}+{D0u}),"")', PCT, "Reverse Gordon: the constant g that gives V0 = P0"),
    ("section", "Two-stage DDM"),
    ("pv1", "PV of the payouts of years 1 to T", "formula", "=SUM({pv_col})", PRICE, "Schedule on the right"),
    ("DT", "D_T, payout in year T", "formula", "={D0u}*(1+{g1})^{T}", PRICE3, ""),
    ("TV", "Terminal value at T = D_T (1 + g2) / (k − g2)", "formula",
     '=IF({k}>{g2},{DT}*(1+{g2})/({k}-{g2}),"n/a: k ≤ g2")', PRICE, ""),
    ("pv_tv", "PV of the terminal value", "formula", '=IF(ISNUMBER({TV}),{TV}/(1+{k})^{T},"")', PRICE, ""),
    ("V_2s", "Value V0", "formula",
     '=IF(N({D0u})<=0,"n/a: no payout",IF(ISNUMBER({pv_tv}),{pv1}+{pv_tv},"n/a: k ≤ g2"))', PRICE, ""),
    ("tv_share", "Terminal value, share of V0", "formula",
     '=IF(AND(ISNUMBER({V_2s}),N({V_2s})>0),{pv_tv}/{V_2s},"")', PCT1, "A high share means the value rests on g2 and k"),
    ("mos_2s", "Margin of safety V0 / P0 − 1", "formula",
     '=IF(AND(ISNUMBER({V_2s}),N({P0})>0),{V_2s}/{P0}-1,"")', PCT1, ""),
    ("disc_2s", "Discount to value 1 − P0 / V0", "formula",
     '=IF(AND(ISNUMBER({V_2s}),N({V_2s})>0),1-{P0}/{V_2s},"")', PCT1, ""),
    ("section", "Fair value"),
    ("fv_method", "Method", "formula", "={method}", None, "Chosen in Growth assumptions"),
    ("V0", "Fair value V0", "result", '=IF({method}="GGM",{V_ggm},{V_2s})', PRICE, ""),
    ("V0_div", "Fair value on dividends only", "formula", None, PRICE,
     "Reference: the same method without buybacks"),     # formula built in v0_div_formula()
    ("fv_P0", "Price P0", "formula", "={P0}", PRICE, ""),
    ("mos", "Margin of safety V0 / P0 − 1", "result", '=IF(AND(ISNUMBER({V0}),N({P0})>0),{V0}/{P0}-1,"")', PCT1, ""),
    ("buy", "Buy threshold", "link", "=" + inp("buy"), PCT1, "From Inputs"),
    ("signal", "Signal", "formula",
     '=IF(N({P0})<=0,"",IF(NOT(ISNUMBER({mos})),"n/a",IF({mos}>={buy},"Buy",IF({mos}>=0,"Watch","Overvalued"))))',
     None, "Buy: at or above the threshold. Watch: between 0 and the threshold"),
    ("flags", "Flags", "formula", None, None, None),     # formula built in flags_formula()
]

ROW0 = 5           # first row of LEFT
SCHED_ROW = 7      # first row of the two-stage schedule (t = 1), columns F:J


def assign_rows():
    """Sections get a blank row above them (except the first)."""
    rows, sections, r = {}, {}, ROW0
    for i, item in enumerate(LEFT):
        if item[0] == "section":
            if i:
                r += 1
            sections[r] = item[1]
        else:
            rows[item[0]] = r
        r += 1
    return rows, sections, r


ROWS, SECTIONS, END = assign_rows()
A = {key: f"$C${r}" for key, r in ROWS.items()}          # absolute addresses for formulas
CELL = {key: f"C{r}" for key, r in ROWS.items()}         # plain addresses, for Summary and the script
A["pv_col"] = f"$J${SCHED_ROW}:$J${SCHED_ROW + T_MAX - 1}"
HIST_ROW = END + 2                                       # header of the dividend table
ALPHA_ROW = HIST_ROW + HIST_YEARS + 5                    # title of the alpha block, below the dividend table
GRID1_ROW = SCHED_ROW + T_MAX + 4                        # title of the first sensitivity grid
GRID2_ROW = GRID1_ROW + 9

# Annual alpha, read by Summary: (key, label, formula, note)
ALPHA = [
    ("alpha_close", "Alpha: closes in one year",
     '=IF(AND(ISNUMBER({V0}),N({P0})>0,ISNUMBER({k})),(1+{k})*({V0}/{P0}-1),"")',
     "(1 + k) × (V0 / P0 − 1); selected fair value"),
    ("alpha_never", "Alpha: never closes",
     '=IF(AND(N({P0})>0,N({D0u})>0,ISNUMBER({g2}),ISNUMBER({k})),{D0u}*(1+{g2})/{P0}+{g2}-{k},"")',
     "D0 used × (1 + g2) / P0 + g2 − k; course convention"),
]
for _i, (_key, *_rest) in enumerate(ALPHA):
    CELL[_key] = f"C{ALPHA_ROW + 1 + _i}"


def flags_formula():
    a = A
    parts = (f'IF(N({a["D0u"]})<=0,"No payout: DDM not applicable. ","")'
             f'&IF(AND({a["basis"]}="{DIVS}",N({a["bps"]})>N({a["D0"]})),'
             f'"Buybacks exceed dividends: the DDM on dividends undervalues. ","")'
             f'&IF(AND({a["basis"]}="{DIVS_BB}",NOT(ISNUMBER({a["bps"]}))),"No buyback data: D0 used is dividends. ","")'
             f'&IF(AND(ISNUMBER({a["mos"]}),N({a["mos"]})>{inp("flag_up")}),'
             f'"Upside above "&TEXT({inp("flag_up")},"0%")&": check the inputs (value trap?). ","")'
             f'&IF({a["k"]}-{a["g2"]}<{inp("spread")},"k − g2 below "&TEXT({inp("spread")},"0%")&". ","")'
             f'&IF(AND(ISNUMBER({a["payout_u"]}),N({a["payout_u"]})>1),"Payout above 100% of EPS. ","")'
             f'&IF({a["g"]}>={a["k"]},"GGM not valid: g ≥ k. ","")'
             f'&IF(AND({a["basis"]}="{DIVS_BB}",{yahoo_g1()}),'
             f'"g1 is per-share growth with buybacks in: they count twice, V0 too high (note next to g1). ","")'
             f'&IF(AND({a["currency"]}<>"",{a["currency"]}<>"USD"),"In "&{a["currency"]}&": rf is the US 10-year. ","")')
    return f'=IF(N({a["P0"]})<=0,"",IF(({parts})="","None",TRIM({parts})))'


def yahoo_g1():
    """True when g1 is Yahoo's average growth estimate, as rounded by the script."""
    return f'ISNUMBER({A["g_yahoo"]}),ABS({A["g1"]}-{A["g_yahoo"]})<0.0006'


def g1_note_formula(next_year=False):
    """The note next to g1: where it comes from and, with buybacks in, the limitation of per-share growth.
    next_year: a sheet of G1_NEXT_YEAR, whose row g_yahoo is Yahoo's next-year estimate, not the average."""
    a = A
    est = "next year" if next_year else "average"
    total = f'IF(ISNUMBER({a["shares_chg"]}),TEXT((1+{a["g1"]})*(1+{a["shares_chg"]})-1,"0.0%"),"n/a")'
    limitation = ('"Limitation: Yahoo\'s growth is per share, and it already includes the buybacks (fewer shares lift EPS). '
                  'The payout here counts them too, so they count twice and V0 is too high. Total growth, without that '
                  f'effect: (1 + g1) × (1 + share count change) − 1 = "&{total}&"."')
    source = (f'"Yahoo next-year earnings growth estimate, row {ROWS["g_yahoo"]} (the team\'s choice, {G1_NEXT_YEAR_DATE})"'
              if next_year else f'"Yahoo average earnings growth estimate, row {ROWS["g_yahoo"]}"')
    typed = f'"Typed. Yahoo {est}: "&IF(ISNUMBER({a["g_yahoo"]}),TEXT({a["g_yahoo"]},"0.0%"),"n/a")'
    return f'=IF({a["basis"]}="{DIVS_BB}",{limitation},IF(AND({yahoo_g1()}),{source},{typed}))'


def g_yahoo_label(ws):
    """Row g_yahoo holds the Yahoo estimate g1 starts from: the average, or next year alone for G1_NEXT_YEAR."""
    return ("Earnings growth estimate, Yahoo next year" if ws.title in G1_NEXT_YEAR
            else next(x[1] for x in LEFT if x[0] == "g_yahoo"))


def update_layout(ws):
    """Bring a sheet built by an older version of this script up to date: labels, notes and formulas only."""
    r = ROWS["g_yahoo"]
    label(ws, f"B{r}", g_yahoo_label(ws))
    ws[f"C{r}"].number_format = PCT
    if not ws[f"D{r}"].value:       # a refresh writes the stock's own note (growth_note): keep it on the other sheets
        note(ws, f"D{r}", next(x[5] for x in LEFT if x[0] == "g_yahoo"))
    note(ws, f"D{ROWS['D0u']}", next(x[5] for x in LEFT if x[0] == "D0u"))
    note(ws, f"D{ROWS['g1']}", g1_note_formula(ws.title in G1_NEXT_YEAR))
    ws[CELL["flags"]].value = flags_formula()


def two_stage_expr(D, k, g2):
    """Closed-form two-stage value of payout D; k and g2 are cell references. Needs k > g2."""
    g1, T = A["g1"], A["T"]
    stage1 = f"IF(ABS({k}-{g1})<1E-9,{D}*{T},{D}*(1+{g1})/({k}-{g1})*(1-((1+{g1})/(1+{k}))^{T}))"
    terminal = f"{D}*(1+{g1})^{T}*(1+{g2})/(({k}-{g2})*(1+{k})^{T})"
    return f"{stage1}+{terminal}"


def two_stage_cell(k, g2):
    """One cell of the two-stage grid, on D0 used."""
    return f'=IF({k}<={g2},"n/a",{two_stage_expr(A["D0u"], k, g2)})'


def v0_div_formula():
    """The fair value with the chosen method on dividends alone: what the buybacks add."""
    a = A
    ggm = f'IF({a["k"]}>{a["g"]},{a["D0"]}*(1+{a["g"]})/({a["k"]}-{a["g"]}),"n/a: k ≤ g")'
    two = f'IF({a["k"]}>{a["g2"]},{two_stage_expr(a["D0"], a["k"], a["g2"])},"n/a: k ≤ g2")'
    return f'=IF(N({a["D0"]})<=0,"n/a: no dividend",IF({a["method"]}="GGM",{ggm},{two}))'


def grid(ws, top, heading, g_key, g_label, cell_formula):
    """5 x 5 sensitivity grid in F:K: k down the rows, growth across the columns, base case in the centre."""
    section(ws, top, heading, cols="FGHIJK")
    hdr = top + 1
    put(ws, f"F{hdr}", f"k \\ {g_label}", "formula", bold=True)
    ws[f"F{hdr}"].alignment = Alignment(horizontal="center")
    steps = (-2, -1, 0, 1, 2)
    for j, s in enumerate(steps):
        col = "GHIJK"[j]
        c = put(ws, f"{col}{hdr}", f"={A[g_key]}+({s})*{inp('step')}", "formula", PCT, bold=True)
        c.fill, c.alignment = fill(HEAD), Alignment(horizontal="center")
    for i, s in enumerate(steps):
        r = hdr + 1 + i
        c = put(ws, f"F{r}", f"={A['k']}+({s})*{inp('step')}", "formula", PCT, bold=True)
        c.fill = fill(HEAD)
        for j in range(5):
            col = "GHIJK"[j]
            c = put(ws, f"{col}{r}", cell_formula(f"$F{r}", f"{col}${hdr}"), "formula", PRICE)
            c.alignment = Alignment(horizontal="right")
            if i == 2 and j == 2:
                c.font, c.border = font(bold=True), BOX
    body = f"G{hdr + 1}:K{hdr + 5}"
    ws.conditional_formatting.add(body, FormulaRule(
        formula=[f"AND(ISNUMBER(G{hdr + 1}),N({A['P0']})>0,G{hdr + 1}>={A['P0']})"], fill=fill(GOOD[0])))
    count = hdr + 6
    ws[f"F{count}"] = (f'=IF(N({A["P0"]})>0,"Cases at or above the price: "'
                       f'&COUNTIF({body},">="&{A["P0"]})&" of 25. Centre: base case","")')
    ws[f"F{count}"].font = font(GREY, size=9, italic=True)


def build_stock(ws):
    """The formulas and layout of a stock sheet, with empty data cells and default assumptions."""
    title(ws, "DDM valuation: Gordon Growth Model and two-stage DDM",
          "Yellow: assumptions to change. Blue: data. Black: formulas. Green fill: the result. Don't insert rows.")
    widths(ws, {"A": 2, "B": 40, "C": 14, "D": 52, "E": 3, "F": 11, "G": 11, "H": 12, "I": 12, "J": 12, "K": 12})
    for r, text in SECTIONS.items():
        section(ws, r, text)
    for item in LEFT:
        if item[0] == "section":
            continue
        key, text, kind, content, fmt, why = item
        r = ROWS[key]
        label(ws, f"B{r}", text, bold=kind == "result")
        if key == "flags":
            content = flags_formula()
        elif key == "V0_div":
            content = v0_div_formula()
        elif isinstance(content, str) and content.startswith("="):
            content = content.format(**A)
        bold = key in ("V_ggm", "V_2s")
        put(ws, f"C{r}", content, kind, fmt, bold=bold)
        if why:
            note(ws, f"D{r}", why)
    label(ws, f"B{ROWS['g_yahoo']}", g_yahoo_label(ws))
    note(ws, f"D{ROWS['g1']}", g1_note_formula(ws.title in G1_NEXT_YEAR))
    ws[CELL["flags"]].alignment = Alignment(wrap_text=False)

    dv = DataValidation(type="list", formula1='"Two-stage,GGM"', allow_blank=False, showErrorMessage=True,
                        errorTitle="Method", error="Choose Two-stage or GGM")
    dv.add(CELL["method"])
    dvt = DataValidation(type="whole", operator="between", formula1="1", formula2=str(T_MAX), showErrorMessage=True,
                         errorTitle="T", error=f"T is a whole number of years from 1 to {T_MAX}")
    dvt.add(CELL["T"])
    dvb = DataValidation(type="list", formula1=f'"{DIVS},{DIVS_BB}"', allow_blank=False, showErrorMessage=True,
                         errorTitle="Payout", error=f"Choose {DIVS} or {DIVS_BB}")
    dvb.add(CELL["basis"])
    for v in (dv, dvt, dvb):
        ws.add_data_validation(v)
    for key in ("mos_ggm", "mos_2s", "mos"):
        cf_mos(ws, CELL[key], A["buy"])
    cf_signal(ws, CELL["signal"])

    # dividends per share by calendar year
    section(ws, HIST_ROW, "Dividends per share by calendar year (Yahoo, split-adjusted)")
    for col, text in zip("BCD", ("Year", "Dividends per share", "Change")):
        put(ws, f"{col}{HIST_ROW + 1}", text, "formula", bold=True)
    for i in range(HIST_YEARS + 1):
        r = HIST_ROW + 2 + i
        if i < HIST_YEARS:
            put(ws, f"B{r}", None, "data")
            put(ws, f"C{r}", None, "data", PRICE3)
        else:
            label(ws, f"B{r}", "Last 12 months (D0)")
            put(ws, f"C{r}", f"={A['D0']}", "formula", PRICE3)
        if i:
            put(ws, f"D{r}", f'=IF(AND(N(C{r - 1})>0,ISNUMBER(C{r})),C{r}/C{r - 1}-1,"")', "formula", PCT1)
            ws[f"D{r}"].alignment = Alignment(horizontal="left")

    # annual alpha
    section(ws, ALPHA_ROW, "Alpha, annual")
    for key, text, formula, why in ALPHA:
        r = int(CELL[key][1:])
        label(ws, f"B{r}", text, bold=True)
        put(ws, CELL[key], formula.format(**A), "result", PCT)
        note(ws, f"D{r}", why)

    # two-stage schedule
    section(ws, ROW0, "Two-stage schedule (stage 1)", cols="FGHIJ")
    for col, text in zip("FGHIJ", ("Year t", "Stage", "Payout D_t", "Discount factor", "PV of D_t")):
        c = put(ws, f"{col}{SCHED_ROW - 1}", text, "formula", bold=True)
        c.alignment = Alignment(horizontal="center")
    for t in range(1, T_MAX + 1):
        r = SCHED_ROW + t - 1
        put(ws, f"F{r}", t, "formula", INT).alignment = Alignment(horizontal="center")
        put(ws, f"G{r}", f'=IF(F{r}<={A["T"]},"Stage 1","")', "formula").alignment = Alignment(horizontal="center")
        put(ws, f"H{r}", f'=IF(F{r}<={A["T"]},{A["D0u"]}*(1+{A["g1"]})^F{r},"")', "formula", PRICE3)
        put(ws, f"I{r}", f'=IF(F{r}<={A["T"]},1/(1+{A["k"]})^F{r},"")', "formula", "0.0000")
        put(ws, f"J{r}", f'=IF(F{r}<={A["T"]},H{r}*I{r},"")', "formula", PRICE)
    r = SCHED_ROW + T_MAX
    put(ws, f"F{r}", "T", "formula").alignment = Alignment(horizontal="center")
    put(ws, f"G{r}", "Terminal", "formula").alignment = Alignment(horizontal="center")
    put(ws, f"H{r}", f"={A['TV']}", "formula", PRICE)
    put(ws, f"I{r}", f"=1/(1+{A['k']})^{A['T']}", "formula", "0.0000")
    put(ws, f"J{r}", f"={A['pv_tv']}", "formula", PRICE)
    for col in "FGHIJ":
        ws[f"{col}{r}"].border = Border(top=THIN)
    put(ws, f"I{r + 1}", "Value V0", "formula", bold=True)
    put(ws, f"J{r + 1}", f"={A['V_2s']}", "formula", PRICE, bold=True)
    note(ws, f"F{r + 2}", "Years after T are left empty: change T and the schedule follows.")

    grid(ws, GRID1_ROW, "Sensitivity: two-stage V0 (k down, g2 across)", "g2", "g2", two_stage_cell)
    grid(ws, GRID2_ROW, "Sensitivity: Gordon V0 (k down, g across)", "g", "g",
         lambda k, g: f'=IF({k}<={g},"n/a",{A["D0u"]}*(1+{g})/({k}-{g}))')

    ws.freeze_panes = "A5"
    ws.sheet_view.showGridLines = False


def fill_example(ws):
    """The TA notebook's Nike case (02_round2_lecture.ipynb §4-§5): rf 5%, beta 1.0369, ERP 6.114%."""
    put(ws, CELL["ticker"], "NKE", "data")
    put(ws, CELL["name"], "Nike: TA notebook example (checks the formulas)", "data")
    put(ws, CELL["source"], "course/ta-code/02_round2_lecture.ipynb, §4–§5", "data")
    put(ws, CELL["P0"], 37.545, "data", PRICE)
    put(ws, CELL["D0"], 1.64, "data", PRICE3)
    put(ws, CELL["beta_calc"], 1.0369, "data", BETA)
    put(ws, CELL["rf"], 0.05, "data", PCT)
    note(ws, f"D{ROWS['rf']}", "Typed for the example: the stock sheets link to Inputs")
    put(ws, CELL["erp"], 0.06114, "data", PCT)
    note(ws, f"D{ROWS['erp']}", "Typed for the example: the stock sheets link to Inputs")
    put(ws, CELL["g1"], 0.10, "input", PCT)
    put(ws, CELL["g2"], 0.04, "input", PCT)
    note(ws, f"D{ROWS['V_ggm']}", "TA notebook: 23.24")
    note(ws, f"D{ROWS['V_2s']}", "TA notebook: 29.78")


# ---------------------------------------------------------------- comparables block (rows 101 on of each stock sheet)
# The stock report's comps (build_stock_report.comps_from_snapshot) as Excel formulas: same multiples, n/m rule, statistic,
# implied prices and comps value. A double check: it does not feed V0, the MoS or the signal. Fixed cells, like the DDM rows.

COMPS_ROW = 101
CR = {"title": 101, "note": 102, "stat": 104, "forward_pe": 105, "p_fcf": 106, "ev_ebitda": 107, "source": 108,
      "data_head": 110, "eps_fwd": 111, "shares": 112, "mcap": 113, "net_debt": 114, "ev": 115, "ebitda": 116, "fcf": 117,
      "revenue": 118, "bvps": 119, "head": 121, "peer0": 122, "n": 128, "avg": 129, "med": 130, "own": 131,
      "imp_avg": 132, "imp_med": 133, "imp_use": 134, "value": 136, "mos": 137, "verdict": 138, "peers": 139,
      "flags": 140, "notes": 141, "raw_title": 143, "raw_head": 144, "raw0": 145}
MCOL = {"forward_pe": "G", "p_fcf": "H", "ev_ebitda": "I", "trailing_pe": "J", "pb": "K", "ps": "L", "ev_sales": "M",
        "yield": "N"}                                       # columns of the peer table, in the report's order first
RAW = {"mcap": "F", "fcf": "G", "fy": "H", "rate": "I", "price": "J", "forward_pe": "K", "trailing_pe": "L",
       "ev_ebitda": "M", "pb": "N", "ps": "O", "ev_sales": "P", "fin": "Q", "fx": "R"}     # raw inputs, one row per peer
CA = {k: f"$C${r}" for k, r in CR.items()}
for _k, _r in (("V_comp", "value"), ("mos_comp", "mos"), ("verdict", "verdict"), ("peers_c", "peers"), ("flags_c", "flags")):
    CELL[_k] = f"C{CR[_r]}"
SHADE = "F3EFEB"                                            # the report's shading of the columns in the comps value
MULT, YES_NO = '0.0"x"', '"Yes,No"'
STOCK_DATA = [   # key, label, kind, number format, note
    ("eps_fwd", "Forward EPS, next fiscal year (consensus)", "data", PRICE,
     "Yahoo, Analysis, Earnings Estimate, next year: the stock report's forward EPS"),
    ("shares", "Shares: Yahoo market cap ÷ price (m)", "data", "#,##0.0", "As the report: not row 29"),
    ("mcap", "Market cap at P0 (USD m)", "formula", "#,##0", "P0 × shares"),
    ("net_debt", "Net debt (USD m)", "data", "#,##0", "Yahoo enterprise value − market cap, as the report"),
    ("ev", "Enterprise value at P0 (USD m)", "formula", "#,##0", "Market cap + net debt"),
    ("ebitda", "EBITDA, last 12 months (USD m)", "data", "#,##0", "Yahoo"),
    ("fcf", "Free cash flow, last fiscal year (USD m)", "data", "#,##0", "Cash flow statement"),
    ("revenue", "Revenue, last 12 months (USD m)", "data", "#,##0", "Yahoo"),
    ("bvps", "Book value per share", "data", PRICE, "Yahoo"),
]


def rule(expr, kind):
    """The report's n/m rule (sane) on an expression: P/E-type multiples in (0, 100], the others above 0."""
    test = f"AND({expr}>0,{expr}<=100)" if kind == "earnings" else f"{expr}>0"
    return f'IF({test},{expr},"n/m")'


def comps_formulas():
    """{cell: formula} of the block, for the peer table, the stock's multiples, the implied prices and the results."""
    f, kind = {}, {mid: k for mid, _, k in MULTIPLES}
    P0, eps_ttm, D0 = A["P0"], A["eps_ttm"], A["D0u"]
    eps, sh, mc, nd, ev, eb, fcf, rev, bv = (CA[k] for k in ("eps_fwd", "shares", "mcap", "net_debt", "ev", "ebitda", "fcf",
                                                            "revenue", "bvps"))
    f[CELL_C("mcap")] = f'=IF(AND(N({P0})>0,ISNUMBER({sh})),{P0}*{sh},"")'
    f[CELL_C("ev")] = f'=IF(AND(ISNUMBER({mc}),ISNUMBER({nd})),{mc}+{nd},"")'
    first, last = CR["peer0"], CR["peer0"] + N_PEERS - 1
    for i in range(N_PEERS):                                   # peer rows: the raw inputs through the n/m rule
        r, q = first + i, CR["raw0"] + i
        raw = lambda key: f"{RAW[key]}{q}"                     # noqa: E731
        blank = f'IF($C{r}="","",'
        f[f"F{r}"] = f'={blank}IF(ISNUMBER({raw("mcap")}),{raw("mcap")}/1000,""))'
        for mid in ("forward_pe", "trailing_pe", "ev_ebitda", "pb", "ps", "ev_sales"):
            x = raw(mid)
            f[f"{MCOL[mid]}{r}"] = f'={blank}IF(ISNUMBER({x}),{rule(x, kind[mid])},"n/m"))'
        pf = f'{raw("mcap")}/{raw("fcf")}'
        f[f"H{r}"] = (f'={blank}IF(AND(ISNUMBER({raw("mcap")}),ISNUMBER({raw("fcf")}),N({raw("fcf")})<>0),'
                      f'{rule(pf, "earnings")},"n/m"))')
        f[f"N{r}"] = f'={blank}IF(AND(N({raw("rate")})>0,N({raw("price")})>0),{raw("rate")}/{raw("price")},"n/m"))'
        f[f"C{q}"] = f'=IF($C{r}="","",$C{r})'
    for mid, col in MCOL.items():                             # statistics over the peers
        rng = f"{col}{first}:{col}{last}"
        f[f"{col}{CR['n']}"] = f"=COUNT({rng})"
        f[f"{col}{CR['avg']}"] = f'=IF({col}{CR["n"]}>0,AVERAGE({rng}),"n/m")'
        f[f"{col}{CR['med']}"] = f'=IF({col}{CR["n"]}>0,MEDIAN({rng}),"n/m")'
    own = {   # the stock's own multiples at P0: (guard, expression)
        "forward_pe": (f"N({eps})>0", f"{P0}/{eps}"), "p_fcf": (f"AND(N({fcf})>0,ISNUMBER({mc}))", f"{mc}/{fcf}"),
        "ev_ebitda": (f"AND(N({eb})>0,ISNUMBER({ev}))", f"{ev}/{eb}"), "trailing_pe": (f"N({eps_ttm})>0", f"{P0}/{eps_ttm}"),
        "pb": (f"N({bv})>0", f"{P0}/{bv}"), "ps": (f"AND(N({rev})<>0,ISNUMBER({mc}))", f"{mc}/{rev}"),
        "ev_sales": (f"AND(N({rev})<>0,ISNUMBER({ev}))", f"{ev}/{rev}"), "yield": (f"N({D0})>0", f"{D0}/{P0}"),
    }
    r = CR["own"]
    f[f"C{r}"], f[f"D{r}"] = f"={A['ticker']}", f"={A['name']}"
    f[f"F{r}"] = f'=IF(ISNUMBER({mc}),{mc}/1000,"")'
    for mid, (guard, expr) in own.items():
        f[f"{MCOL[mid]}{r}"] = f'=IF(AND(N({P0})>0,{guard}),{rule(expr, kind[mid])},"n/m")'
    implied = {   # price at a peer statistic m: (guard, expression), as comparables() in the report script
        "forward_pe": (f"N({eps})>0", "{eps}*{m}"), "p_fcf": (f"N({fcf})>0,N({sh})>0", "{m}*{fcf}/{sh}"),
        "ev_ebitda": (f"N({eb})>0,ISNUMBER({nd}),N({sh})>0", "({m}*{eb}-{nd})/{sh}"),
        "trailing_pe": (f"N({eps_ttm})>0", "{eps_ttm}*{m}"), "pb": (f"N({bv})>0", "{bv}*{m}"),
        "ps": (f"N({rev})<>0,N({sh})>0", "{rev}*{m}/{sh}"),
        "ev_sales": (f"N({rev})<>0,ISNUMBER({nd}),N({sh})>0", "({m}*{rev}-{nd})/{sh}"), "yield": (f"N({D0})>0", "{D0}/{m}"),
    }
    names = dict(eps=eps, fcf=fcf, sh=sh, eb=eb, nd=nd, eps_ttm=eps_ttm, bv=bv, rev=rev, D0=D0)
    for key, stat_row in (("imp_avg", CR["avg"]), ("imp_med", CR["med"])):
        for mid, (guard, expr) in implied.items():
            col = MCOL[mid]
            m = f"{col}${stat_row}"
            f[f"{col}{CR[key]}"] = f'=IF(AND(ISNUMBER({m}),{guard}),{expr.format(m=m, **names)},"n/m")'
    for mid in COMPS_USE_LABELS:                              # the implied prices that enter the comps value
        col = MCOL[mid]
        pick = f'IF({CA["stat"]}="Average",{col}{CR["imp_avg"]},{col}{CR["imp_med"]})'
        f[f"{col}{CR['imp_use']}"] = f'=IF(AND({CA[mid]}="Yes",ISNUMBER({pick})),{pick},"")'
    use = f"G{CR['imp_use']}:I{CR['imp_use']}"
    f[CELL_C("value")] = f'=IF(COUNT({use})>0,AVERAGE({use}),"n/a")'
    f[CELL_C("mos")] = f'=IF(AND(ISNUMBER({CA["value"]}),N({P0})>0),{CA["value"]}/{P0}-1,"")'
    mos_d, mos_c = A["mos"], CA["mos"]
    f[CELL_C("verdict")] = (f'=IF(N({P0})<=0,"",IF(AND(ISNUMBER({mos_d}),ISNUMBER({mos_c})),'
                            f'IF(AND({mos_d}>0,{mos_c}>0),"undervalued",IF(AND({mos_d}<0,{mos_c}<0),"overvalued","mixed: check")),'
                            f'IF(OR(ISNUMBER({mos_d}),ISNUMBER({mos_c})),"one method only","n/a")))')
    f[CELL_C("peers")] = "=TRIM(" + '&" "&'.join(f"C{first + i}" for i in range(N_PEERS)) + ")"
    n_peers = f"SUMPRODUCT(--(LEN(C{first}:C{last})>0))"
    chosen = f'COUNTIF({CA["forward_pe"]}:{CA["ev_ebitda"]},"Yes")'
    parts = (f'IF({n_peers}<5,"Only "&{n_peers}&" peers: the template asks for 5 or 6. ","")'
             f'&IF({CA["verdict"]}="mixed: check","DDM and comps disagree (the TA\'s mixed: check). ","")'
             f'&IF(LEFT({CA["source"]},8)="Proposed","Peers proposed, not yet checked on Bloomberg RV. ","")'
             f'&IF(AND({n_peers}>0,{chosen}>COUNT({use})),"Only "&COUNT({use})&" of the "&{chosen}&'
             f'" chosen multiples give a price (EV/EBITDA and P/FCF are n/m for a bank). ","")'
             f'&IF(NOT(ISNUMBER({A["V0"]})),"No DDM: the report would use the comps value as the fair value. ","")'
             f'&IF({CA["notes"]}<>"",{CA["notes"]}&". ","")')
    f[CELL_C("flags")] = f'=IF(N({P0})<=0,"",IF(({parts})="","None",TRIM({parts})))'
    return f


def CELL_C(key):  # noqa: N802
    return f"C{CR[key]}"


def clear_comps_rules(ws):
    """Drop the validations and conditional formats of rows 101 on, so that a run does not stack copies of them."""
    keep = [dv for dv in ws.data_validations.dataValidation
            if all(rg.min_row < COMPS_ROW for rg in dv.sqref.ranges)]
    ws.data_validations.dataValidation = keep
    for cf in list(ws.conditional_formatting._cf_rules):
        if all(rg.min_row >= COMPS_ROW for rg in cf.sqref.ranges):
            del ws.conditional_formatting._cf_rules[cf]


def cf_verdict(ws, ref):
    for word, (bg, fg) in (("undervalued", GOOD), ("mixed: check", NEUTRAL), ("overvalued", BAD)):
        ws.conditional_formatting.add(ref, FormulaRule(formula=[f'{ref.split(":")[0].replace("$", "")}="{word}"'],
                                                       fill=fill(bg), font=Font(color=fg)))


def build_comps(ws):
    """Write (or rewrite) the layout and formulas of the comps block. Yellow cells keep what is typed in them."""
    clear_comps_rules(ws)
    section(ws, CR["title"], "Comparables: a double check (as in the stock report)", cols="BCDEFGHIJKLMN")
    note(ws, f"B{CR['note']}", "Not in the fair value: the DDM is V0, the comps are a check (stock report, Round 2 README). "
                               "Peers: 5–6 from Bloomberg RV, same industry. n/m: negative, or above 100x for P/E, P/FCF "
                               "and EV/EBITDA. Blue cells are rewritten by every refresh: type a Bloomberg figure again after one.")
    # a new sheet: the three multiples in, the team's rule for every stock (7 Nov 2026). The stock report uses these cells
    choices = [("stat", COMPS_STAT_LABEL, "Median", "Median or Average of the peers. The stock report uses this choice"),
               ("forward_pe", COMPS_USE_LABELS["forward_pe"], "Yes", "Yes: its implied price is in the comps value"),
               ("p_fcf", COMPS_USE_LABELS["p_fcf"], "Yes", "Yes: in the comps value. New sheets start with Yes (team's rule); n/m for banks"),
               ("ev_ebitda", COMPS_USE_LABELS["ev_ebitda"], "Yes", "Yes: its implied price is in the comps value"),
               ("source", "Peers: source", None, "Change it once the peers are checked on Bloomberg RV")]
    for key, text, default, why in choices:
        ref = CELL_C(key)
        label(ws, f"B{CR[key]}", text)
        put(ws, ref, ws[ref].value if ws[ref].value not in (None, "") else default, "input")
        note(ws, f"D{CR[key]}", why)
    dv = DataValidation(type="list", formula1='"Median,Average"', allow_blank=False, showErrorMessage=True,
                        errorTitle="Statistic", error="Choose Median or Average")
    dv.add(CELL_C("stat"))
    dvy = DataValidation(type="list", formula1=YES_NO, allow_blank=False, showErrorMessage=True,
                         errorTitle="Comps value", error="Choose Yes or No")
    dvy.add(f"{CELL_C('forward_pe')}:{CELL_C('ev_ebitda')}")
    ws.add_data_validation(dv)
    ws.add_data_validation(dvy)

    label(ws, f"B{CR['data_head']}", "The stock's data for the comps (Yahoo, in USD)", bold=True)
    for key, text, kind, fmt, why in STOCK_DATA:
        label(ws, f"B{CR[key]}", text)
        c = ws[CELL_C(key)]
        put(ws, CELL_C(key), c.value if kind == "data" else None, kind, fmt)
        if ws[f"D{CR[key]}"].value is None:
            note(ws, f"D{CR[key]}", why)

    # peer table, as on page 2 of the report
    hr = CR["head"]
    heads = {"B": "Peer", "C": "Ticker", "D": "Company", "F": "Cap, USD bn", "G": "Fwd P/E", "H": "P/FCF",
             "I": "EV/EBITDA", "J": "Trail. P/E", "K": "P/B", "L": "P/S", "M": "EV/Sales", "N": "Div. yield"}
    for col, text in heads.items():
        c = put(ws, f"{col}{hr}", text, "formula", bold=True)
        c.fill, c.border = fill(HEAD), Border(bottom=THIN)
        c.alignment = Alignment(horizontal="left" if col in "BCD" else "center")
    for i, lb in enumerate(PEER_LABELS):
        r = CR["peer0"] + i
        label(ws, f"B{r}", lb)
        put(ws, f"C{r}", ws[f"C{r}"].value, "input")
        put(ws, f"D{r}", ws[f"D{r}"].value, "data")
    rows = [("n", "Peers used (n)", INT), ("avg", "Peer average", MULT), ("med", "Peer median", MULT),
            ("own", "Own multiples at P0", MULT), ("imp_avg", "Implied price at peer average", PRICE),
            ("imp_med", "Implied price at peer median", PRICE), ("imp_use", "Implied price in the comps value", PRICE)]
    for key, text, _ in rows:
        label(ws, f"B{CR[key]}", text, bold=key in ("med", "own"))
    form = comps_formulas()
    for ref, formula in form.items():
        col, r = ref[0], int(ref[1:])
        fmt = None
        if CR["peer0"] <= r <= CR["own"] and col in "GHIJKLM":
            fmt = MULT if r != CR["n"] else INT
        elif CR["peer0"] <= r <= CR["own"] and col == "N":
            fmt = PCT if r != CR["n"] else INT
        elif r in (CR["imp_avg"], CR["imp_med"], CR["imp_use"]) or ref in (CELL_C("value"),):
            fmt = PRICE
        elif col == "F" and r <= CR["own"]:
            fmt = "#,##0.0"
        elif ref == CELL_C("mos"):
            fmt = PCT1
        kind = "result" if ref in (CELL_C("value"), CELL_C("mos")) else "formula"
        c = put(ws, ref, formula, kind, fmt, bold=(r == CR["own"] and col != "C") or r == CR["med"])
        if col in "FGHIJKLMN":
            c.alignment = Alignment(horizontal="right")
    for col in "BCDFGHIJKLMN":
        ws[f"{col}{CR['own']}"].border = Border(top=THIN)
        ws[f"{col}{CR['n']}"].border = Border(top=THIN)
    for mid, col in (("forward_pe", "G"), ("p_fcf", "H"), ("ev_ebitda", "I")):    # shade the columns in the comps value
        ws.conditional_formatting.add(f"{col}{hr}:{col}{CR['imp_use']}",
                                      FormulaRule(formula=[f'{CA[mid]}="Yes"'], fill=fill(SHADE)))

    results = [("value", "Comps value", "Average of the implied prices in the shaded columns, at the chosen statistic"),
               ("mos", "Comps margin of safety V comps / P0 − 1", "Compare with the DDM margin of safety (row 77)"),
               ("verdict", "DDM vs comps", "The TA's check: both above 0 undervalued, both below 0 overvalued"),
               ("peers", "Peers in the comps", ""), ("flags", "Comps flags", "")]
    for key, text, why in results:
        label(ws, f"B{CR[key]}", text, bold=key in ("value", "mos"))
        if key not in ("value", "mos"):
            put(ws, CELL_C(key), form[CELL_C(key)], "formula")
        if why:
            note(ws, f"D{CR[key]}", why)
    ws[CELL_C("flags")].alignment = Alignment(wrap_text=False)
    label(ws, f"B{CR['notes']}", "Currency notes")
    put(ws, CELL_C("notes"), ws[CELL_C("notes")].value, "data")
    cf_mos(ws, CELL_C("mos"), A["buy"])
    cf_verdict(ws, CELL_C("verdict"))

    # raw inputs behind the peer table
    section(ws, CR["raw_title"], "Data for the peer table (Yahoo; a blue cell can be typed over with Bloomberg RV)",
            cols="BCDEFGHIJKLMNOPQR")
    rh = CR["raw_head"]
    raw_heads = {"B": "Raw inputs", "C": "Ticker", "F": "Mkt cap, USD m", "G": "FCF, USD m", "H": "FCF year",
                 "I": "Div. rate", "J": "Price", "K": "Fwd P/E", "L": "Trail. P/E", "M": "EV/EBITDA", "N": "P/B",
                 "O": "P/S", "P": "EV/Sales", "Q": "Reports in", "R": "FX rate"}
    for col, text in raw_heads.items():
        c = put(ws, f"{col}{rh}", text, "formula", bold=True)
        c.fill, c.border = fill(HEAD), Border(bottom=THIN)
    fmts = {"F": "#,##0", "G": "#,##0", "H": "0", "I": PRICE3, "J": PRICE, "K": "0.00", "L": "0.00", "M": "0.00",
            "N": "0.00", "O": "0.00", "P": "0.00", "Q": None, "R": "0.0000"}
    for i in range(N_PEERS):
        q = CR["raw0"] + i
        label(ws, f"B{q}", f"Data, peer {i + 1}")
        put(ws, f"C{q}", form[f"C{q}"], "formula")
        for col, fmt in fmts.items():
            put(ws, f"{col}{q}", ws[f"{col}{q}"].value, "data", fmt)
    note(ws, f"B{CR['raw0'] + N_PEERS}", "Yahoo's ratios as given (forwardPE, trailingPE, enterpriseToEbitda, priceToBook, "
                                         "priceToSalesTrailing12Months, enterpriseToRevenue). FCF of the last fiscal year, "
                                         "converted to USD when the company reports in another currency.")
    for col in "LMNOPQR":
        ws.column_dimensions[col].width = 11


def fill_comps(ws, c, source=None):
    """Write the blue cells of the comps block from comps_from_snapshot() output; peers only into empty yellow cells."""
    s = c["stock"]
    m = lambda x: x / 1e6 if x is not None else None           # noqa: E731
    vals = {"eps_fwd": s["eps_fwd"], "shares": m(s["shares"]), "net_debt": m(s["net_debt"]), "ebitda": m(s["ebitda"]),
            "fcf": m(s["fcf"]), "revenue": m(s["revenue"]), "bvps": s["bvps"]}
    for key, v in vals.items():
        ws[CELL_C(key)].value = v
    fy = f"FY{s['fcf_fy']}, " if s["fcf_fy"] else ""
    note(ws, f"D{CR['fcf']}", f"{fy}cash flow statement" + (f", converted at {s['fx']:.4f} from {s['fin']}" if s["fin"] else ""))
    if s["fin"]:
        conv = f"converted at {s['fx']:.4f} from {s['fin']}" if s["fx"] else f"left out: in {s['fin']}, no exchange rate"
        note(ws, f"D{CR['net_debt']}", f"Total debt − cash, {conv} (Yahoo's EV mixes currencies)")
        for key in ("ebitda", "revenue"):
            note(ws, f"D{CR[key]}", f"Yahoo, {conv}")
        parts = s["notes"][-1].split("; ")
        if len(parts) >= 3:                    # "...converted ...; forward EPS <how>; book value <how>"
            note(ws, f"D{CR['eps_fwd']}", "Yahoo, Earnings Estimate, next year; " + parts[-2])
            note(ws, f"D{CR['bvps']}", "Yahoo; " + parts[-1])
    else:
        note(ws, f"D{CR['net_debt']}", "Yahoo enterprise value − market cap, as the report")
        for key in ("ebitda", "revenue", "eps_fwd", "bvps"):
            note(ws, f"D{CR[key]}", next(x[4] for x in STOCK_DATA if x[0] == key))
    raws = {r["ticker"]: r for r in c["raw"]}
    for i in range(N_PEERS):
        r, q = CR["peer0"] + i, CR["raw0"] + i
        t = str(ws[f"C{r}"].value or "").strip().upper()
        raw = raws.get(t)
        ws[f"D{r}"].value = (raw["name"] + (f" · reports in {raw['fin']}" if raw["fin"] else "")) if raw else None
        for key, col in RAW.items():
            v = None
            if raw:
                v = {"mcap": m(raw["market_cap"]), "fcf": m(raw["fcf"]), "fy": raw["fcf_fy"], "rate": raw["dividend_rate"],
                     "fin": raw["fin"]}.get(key, raw.get(key))
            ws[f"{col}{q}"].value = v
    ws[CELL_C("notes")].value = "; ".join(c["peer_notes"] + s["notes"]) or None
    if source and not ws[CELL_C("source")].value:
        ws[CELL_C("source")].value = source


def sheet_peers(ws):
    return [str(ws[f"C{CR['peer0'] + i}"].value).strip().upper() for i in range(N_PEERS)
            if str(ws[f"C{CR['peer0'] + i}"].value or "").strip()]


def comps_choices(ws):
    """comps_primary and comps_stat of a sheet, in the report's terms."""
    primary = [mid for mid in COMPS_USE_LABELS if ws[CELL_C(mid)].value == "Yes"]
    return primary, COMPS_STATS.get(ws[CELL_C("stat")].value, "median")


def fill_example_comps(ws):
    """Example NKE: the TA notebook's comparables (forward EPS × average forward P/E of LULU, DECK, ADDYY), on the CSV."""
    mult = pd.read_csv(TA / "r2_multiples.csv", index_col=0)
    peers = mult[(mult["group"] == "NKE") & (mult["role"] == "peer")]
    for i, (p, row) in enumerate(peers.iterrows()):
        ws[f"C{CR['peer0'] + i}"].value = p
        ws[f"K{CR['raw0'] + i}"].value = float(row["forwardPE"])
        ws[f"D{CR['peer0'] + i}"].value = {"ADDYY": "Adidas ADR (reports in EUR)"}.get(p, p)
    ws[CELL_C("eps_fwd")].value = float(mult.loc["NKE", "forwardEps"])
    for key, v in (("stat", "Average"), ("forward_pe", "Yes"), ("p_fcf", "No"), ("ev_ebitda", "No"),
                   ("source", "TA notebook, course/ta-code/r2_multiples.csv")):
        ws[CELL_C(key)].value = v
    example_comps_note(ws)


def example_comps_note(ws):
    """The note on Example NKE's comps value. build_comps resets it to the generic note, so a refresh writes it again."""
    mult = pd.read_csv(TA / "r2_multiples.csv", index_col=0)
    peers = mult[(mult["group"] == "NKE") & (mult["role"] == "peer")]
    v = float(mult.loc["NKE", "forwardEps"]) * peers["forwardPE"].mean()
    note(ws, f"D{CR['value']}", f"TA's method on r2_multiples.csv: {v:.2f} (the notebook printed 18.80 on an older download)")


# ---------------------------------------------------------------- Summary sheet

SUMMARY_COLS = [   # header, key in the stock sheet, number format, width
    ("Ticker", None, None, 10), ("Company", "name", None, 26), ("Price P0", "P0", PRICE, 10),
    ("Payout discounted", "basis", None, 20), ("D0 used", "D0u", PRICE3, 9), ("Div. yield", "yield_", PCT, 9), ("β", "beta", BETA, 7), ("k", "k", PCT, 8), ("g1", "g1", PCT, 8), ("T", "T", INT, 5),
    ("g2", "g2", PCT, 8), ("GGM V0", "V_ggm", PRICE, 10), ("GGM MoS", "mos_ggm", PCT1, 9),
    ("Two-stage V0", "V_2s", PRICE, 12), ("Two-stage MoS", "mos_2s", PCT1, 12), ("Method", "method", None, 10),
    ("Fair value", "V0", PRICE, 10), ("MoS", "mos", PCT1, 9), ("Signal", "signal", None, 11), ("Flags", "flags", None, 70),
    ("Alpha: closes in one year", "alpha_close", PCT, 27), ("Alpha: never closes", "alpha_never", PCT, 13),
]
SUM_HDR, SUM_ROW0 = 5, 6
SUM_COLS = [get_column_letter(2 + i) for i in range(len(SUMMARY_COLS))]
# The comparables, from column Y: X is typed by hand by the team ("Analysts_Estimate_avg") and left alone
SUMMARY_COMPS = [("Comps value", "V_comp", PRICE, 12), ("Comps MoS", "mos_comp", PCT1, 11),
                 ("DDM vs comps", "verdict", None, 15), ("Peers", "peers_c", None, 34), ("Comps flags", "flags_c", None, 70)]
COMPS_COL0 = 25                                            # column Y
SUM_COMPS_COLS = [get_column_letter(COMPS_COL0 + i) for i in range(len(SUMMARY_COMPS))]


def summary_row(ws, r):
    for (head, key, fmt, _), col in zip(SUMMARY_COLS, SUM_COLS):
        if key is None:
            put(ws, f"{col}{r}", None, "input")
            continue
        formula = f'=IF($B{r}="","",IFERROR(INDIRECT("\'"&$B{r}&"\'!{CELL[key]}"),""))'
        bold = key in ("V0", "mos", "alpha_close", "alpha_never")
        put(ws, f"{col}{r}", formula, "formula", fmt, bold=bold)
    summary_comps_row(ws, r)


def summary_comps_row(ws, r):
    for (head, key, fmt, _), col in zip(SUMMARY_COMPS, SUM_COMPS_COLS):
        formula = f'=IF($B{r}="","",IFERROR(INDIRECT("\'"&$B{r}&"\'!{CELL[key]}"),""))'
        put(ws, f"{col}{r}", formula, "formula", fmt, bold=key == "V_comp")


def summary_comps(ws):
    """The comps columns of Summary, written (or rewritten) for every prepared row: also upgrades an older workbook."""
    for (head, key, fmt, width), col in zip(SUMMARY_COMPS, SUM_COMPS_COLS):
        c = put(ws, f"{col}{SUM_HDR}", head, "formula", bold=True)
        c.fill, c.border = fill(HEAD), Border(bottom=THIN)
        c.alignment = Alignment(horizontal="left" if key in ("peers_c", "flags_c") else "center")
        ws.column_dimensions[col].width = width
    last = SUM_ROW0
    while ws[f"C{last + 1}"].value is not None:
        last += 1
    for r in range(SUM_ROW0, last + 1):
        summary_comps_row(ws, r)
    first_col = COMPS_COL0
    for cf in list(ws.conditional_formatting._cf_rules):   # no stacked copies of the comps rules
        if all(rg.min_col >= first_col for rg in cf.sqref.ranges):
            del ws.conditional_formatting._cf_rules[cf]
    col = dict((key, c) for (_, key, _, _), c in zip(SUMMARY_COMPS, SUM_COMPS_COLS))
    cf_mos(ws, f"{col['mos_comp']}{SUM_ROW0}:{col['mos_comp']}{last}", "$D$4")
    cf_verdict(ws, f"{col['verdict']}{SUM_ROW0}:{col['verdict']}{last}")


def build_summary(ws):
    title(ws, "DDM valuation: summary", "One row per stock sheet. Type a sheet name under Ticker, or let the script do it.")
    label(ws, "B4", "Buy threshold: MoS ≥")
    put(ws, "D4", "=" + inp("buy"), "link", PCT1)
    for (head, key, fmt, width), col in zip(SUMMARY_COLS, SUM_COLS):
        c = put(ws, f"{col}{SUM_HDR}", head, "formula", bold=True)
        c.fill, c.border = fill(HEAD), Border(bottom=THIN)
        c.alignment = Alignment(horizontal="left" if key in (None, "name", "basis", "flags") else "center")
        ws.column_dimensions[col].width = width
    ws.column_dimensions["A"].width = 2
    for r in range(SUM_ROW0, SUM_ROW0 + SUMMARY_ROWS):
        summary_row(ws, r)
    format_summary(ws, SUM_ROW0 + SUMMARY_ROWS - 1)
    summary_comps(ws)
    ws.freeze_panes = f"C{SUM_ROW0}"
    ws.sheet_view.showGridLines = False


def format_summary(ws, last):
    col = {key: c for (_, key, _, _), c in zip(SUMMARY_COLS, SUM_COLS)}
    for key in ("mos_ggm", "mos_2s", "mos"):
        cf_mos(ws, f"{col[key]}{SUM_ROW0}:{col[key]}{last}", "$D$4")
    cf_signal(ws, f"{col['signal']}{SUM_ROW0}:{col['signal']}{last}")


def add_to_summary(ws, ticker):
    r = SUM_ROW0
    while ws[f"B{r}"].value not in (None, ""):
        if str(ws[f"B{r}"].value).upper() == ticker.upper():
            return
        r += 1
    if ws[f"C{r}"].value is None:          # past the prepared rows
        summary_row(ws, r)
        format_summary(ws, r)
    put(ws, f"B{r}", ticker, "input")


# ---------------------------------------------------------------- data

def buybacks(yf, tk, t, info, as_of, st=None):
    """Last fiscal year's buybacks and diluted shares, as dividend_basis in build_stock_report.py, plus checks.
    A foreign company's statements are in its own currency: buybacks are converted to the price currency at the
    price date, and shares are counted in ADRs (ADR_SHARES), so buybacks per share are per ADR like the price."""
    st = st if st is not None else retry(lambda: statements_of(tk), f"{t} statements")
    out = {"buyback_fy": None, "shares_fy": None, "bps_avg": None, "shares_chg": None, "ni_growth": None, "fy": None,
           "fx": None, "fx_src": None, "fin": None, "adr": None}
    if st.empty:
        print(f"  {t}: no financial statements on Yahoo, so no buyback data")
        return out
    fin, cur = info.get("financialCurrency"), info.get("currency")
    fx = 1.0
    if fin and cur and fin != cur:
        fx, out["fx_src"] = fx_rate(yf, fin, cur, as_of)
        if fx is None:
            print(f"  {t}: statements in {fin}, price in {cur}, and no exchange rate on Yahoo: no buyback data")
            return out
        out["fx"], out["fin"] = fx, fin
        out["adr"] = ADR_SHARES.get(t)
        if out["adr"] is None:
            print(f"  {t}: statements in {fin}: add its shares per ADR to ADR_SHARES (1 assumed)")
    ratio = out["adr"] or 1
    buy = -st["Repurchase Of Capital Stock"].fillna(0.0) * fx      # no line: no buybacks, as in the report script
    shares = st["Diluted Average Shares"].where(st["Diluted Average Shares"] > 0) / ratio
    out["fy"] = [d.year for d in st.index]
    if np.isfinite(shares.iloc[-1]):
        out["buyback_fy"], out["shares_fy"] = float(buy.iloc[-1]) / 1e6, float(shares.iloc[-1]) / 1e6
    per_share = (buy / shares).iloc[-GROWTH_YEARS:].dropna()
    if len(per_share) == GROWTH_YEARS:
        out["bps_avg"] = float(per_share.mean())
    if len(st) > GROWTH_YEARS:
        cagr = lambda s: (s.iloc[-1] / s.iloc[-1 - GROWTH_YEARS]) ** (1 / GROWTH_YEARS) - 1   # noqa: E731
        sh, ni = shares, st["Net Income"]
        if sh.iloc[-1] > 0 and sh.iloc[-1 - GROWTH_YEARS] > 0:
            out["shares_chg"] = float(cagr(sh))
        if ni.iloc[-1] > 0 and ni.iloc[-1 - GROWTH_YEARS] > 0:
            out["ni_growth"] = float(cagr(ni))
    return out


def growth_estimate(yf, t, info):
    """Yahoo's earnings growth estimates (Analysis, Growth Estimates) for the current and next fiscal year, and their
    average: the default g1. From the home listing when the US line has few analysts (ESTIMATES_FROM)."""
    src = ESTIMATES_FROM.get(t, t)
    tk = yf.Ticker(src)
    out = {"g_yahoo": None, "g_cy": None, "g_ny": None, "g_src": src, "g_analysts": None, "g_fy": None, "g_next": False}
    try:
        ge = retry(lambda: tk.growth_estimates, f"{src} growth estimates")
        cy, ny = (float(ge.loc[p, "stockTrend"]) if p in ge.index else np.nan for p in ("0y", "+1y"))
    except Exception:
        cy = ny = np.nan
    try:
        n = retry(lambda: tk.earnings_estimate, f"{src} earnings estimates").loc[["0y", "+1y"], "numberOfAnalysts"]
        out["g_analysts"] = [int(x) if np.isfinite(x) else None for x in n]
    except Exception:
        pass
    try:
        end = (info if src == t else retry(lambda: tk.info, f"{src} info")).get("nextFiscalYearEnd")
    except Exception:
        end = None
    vals = [x for x in (cy, ny) if np.isfinite(x)]
    if not vals:
        print(f"  {t}: no growth estimates on Yahoo ({src})")
        return out
    out.update(g_yahoo=float(np.mean(vals)), g_cy=cy if np.isfinite(cy) else None, g_ny=ny if np.isfinite(ny) else None)
    if t in G1_NEXT_YEAR:                      # next year alone, the team's choice for this stock
        if np.isfinite(ny):
            out.update(g_yahoo=float(ny), g_next=True)
        else:
            print(f"  {t}: no next-year growth estimate on Yahoo ({src}), so the average is used")
    if end:
        out["g_fy"] = pd.Timestamp(end, unit="s").year
    few = [x for x in (out["g_analysts"] or []) if x is not None and x < MIN_ANALYSTS]
    if few:
        print(f"  {t}: Yahoo growth estimates from {src} rest on only {min(few)} analysts")
    return out


def download(tickers, as_of_arg):
    """Prices, dividends and Yahoo fields for each ticker, beta on SPY, and the 10-year yield."""
    import yfinance as yf
    yf.set_tz_cache_location(str(Path(tempfile.gettempdir()) / "matterhorn-yfinance"))   # not in the repo
    start = (pd.Timestamp.today() - pd.DateOffset(years=HISTORY_YEARS)).strftime("%Y-%m-%d")
    universe = sorted(set(tickers) | {"SPY"})
    print(f"Downloading {', '.join(tickers)} and SPY ...")
    adj = retry(lambda: yf.download(universe, start=start, auto_adjust=True, progress=False)["Close"], "adjusted prices")
    close = retry(lambda: yf.download(universe, start=start, auto_adjust=False, progress=False)["Close"], "closes")
    now = datetime.now(ZoneInfo("America/New_York"))       # before the close, today's bar is an intraday price
    if close.index[-1].date() == now.date() and (now.hour, now.minute) < (16, 15):
        adj, close = adj.iloc[:-1], close.iloc[:-1]
    rates = pd.concat([fred_series("DGS1MO"), fred_series("DGS10")], axis=1) / 100
    cutoff = pd.Timestamp(as_of_arg) if as_of_arg else close.index[-1]

    out = {}
    for t in tickers:
        c = close[t].dropna().loc[:cutoff] if t in close else pd.Series(dtype=float)
        if c.empty:
            print(f"  {t}: no prices on Yahoo up to {cutoff:%d %b %Y}. Check the ticker (Yahoo format, e.g. NESN.SW). Skipped")
            continue
        as_of = c.index[-1]
        tk = yf.Ticker(t)
        divs = retry(lambda: tk.dividends, f"{t} dividends")
        if getattr(divs.index, "tz", None) is not None:
            divs.index = divs.index.tz_localize(None)
        divs.index = pd.DatetimeIndex(divs.index).normalize()
        typed = []
        for date, amount, source in MISSING_DIVIDENDS.get(t, []):
            date = pd.Timestamp(date)
            if not (abs(divs.index - date) <= pd.Timedelta(days=20)).any():
                divs.loc[date] = amount
                typed.append(f"{amount:g} ex {date:%d %b %Y} typed in ({source})")
        divs = divs.sort_index().loc[:as_of]
        D0 = float(divs.loc[divs.index > as_of - pd.Timedelta(days=365)].sum())
        years = list(range(as_of.year - HIST_YEARS, as_of.year))          # complete calendar years
        dps = {y: float(divs[divs.index.year == y].sum()) for y in years}
        last, first = years[-1], years[-1] - 5
        cagr = (dps[last] / dps[first]) ** (1 / 5) - 1 if dps.get(first, 0) > 0 and dps[last] > 0 else None

        info = retry(lambda: tk.info, f"{t} info")
        growth = growth_estimate(yf, t, info)
        st = retry(lambda: statements_of(tk), f"{t} statements")
        try:                                   # the stock report's forward EPS: this line's own consensus, next year
            eps_next = float(retry(lambda: tk.earnings_estimate, f"{t} earnings estimates").loc["+1y", "avg"])
        except Exception:
            eps_next = None
        eps_next = eps_next if eps_next is not None and np.isfinite(eps_next) else None

        a = adj[[t, "SPY"]].loc[:as_of].ffill()
        R = a.resample("ME").last().pct_change().loc[:complete_month_end(as_of)]
        rf_m = (rates["DGS1MO"].loc[:as_of].ffill() / 12).resample("ME").mean().reindex(R.index).ffill()
        Re = R.sub(rf_m, axis=0).dropna().iloc[-WINDOW:]
        beta = float(Re[t].cov(Re["SPY"]) / Re["SPY"].var()) if len(Re) > 2 else None

        num = lambda key: float(info[key]) if isinstance(info.get(key), (int, float)) else None   # noqa: E731
        out[t] = {
            "ticker": t, "name": info.get("longName") or info.get("shortName") or t,
            "sector": " / ".join(x for x in (info.get("sector"), info.get("industry")) if x),
            "currency": info.get("currency"), "as_of": as_of.to_pydatetime(), "P0": float(c.iloc[-1]), "D0": D0,
            "div_rate": num("dividendRate"), "eps_ttm": num("trailingEps"), "eps_fwd": num("forwardEps"),
            "roe": num("returnOnEquity"), "dps_cagr": cagr, "beta_calc": beta,
            "beta_yahoo": num("beta"), "dps": dps, "months": len(Re), "beta_end": Re.index[-1] if len(Re) else None,
            "cagr_years": (first, last), "country": info.get("country"), **growth, **buybacks(yf, tk, t, info, as_of, st),
            "comps_info": {k: info.get(k) for k in INFO_KEYS + ["industryKey"]}, "comps_st": to_records(st),
            "eps_next": eps_next,
        }
        out[t]["typed_divs"] = typed
        if D0 <= 0:
            print(f"  {t}: no dividend in the last 12 months, so the DDM does not apply")
        elif out[t]["div_rate"] and D0 < 0.8 * out[t]["div_rate"]:
            print(f"  {t}: D0 {D0:.3f} is well below Yahoo's dividend rate {out[t]['div_rate']:.3f}: a recent raise, or "
                  "a payment missing from Yahoo's history? If missing, add it to MISSING_DIVIDENDS")
        for x in typed:
            print(f"  {t}: dividend of {x}")
        if len(Re) < WINDOW:
            print(f"  {t}: only {len(Re)} months of returns for beta, not {WINDOW}")

    as_of = max((d["as_of"] for d in out.values()), default=cutoff.to_pydatetime())
    dgs10 = rates["DGS10"].dropna().loc[:as_of]
    return out, {"as_of": as_of, "rf": float(dgs10.iloc[-1]), "rf_date": dgs10.index[-1]}


def fill_data(ws, d, downloaded):
    """Write the blue cells of a stock sheet. Assumptions (yellow) are not touched."""
    for key in ("ticker", "name", "sector", "currency", "as_of", "P0", "D0", "div_rate", "eps_ttm", "eps_fwd", "roe",
                "dps_cagr", "g_yahoo", "beta_calc", "beta_yahoo", "buyback_fy", "shares_fy", "bps_avg", "shares_chg",
                "ni_growth"):
        ws[CELL[key]].value = d[key]
    ws[CELL["source"]].value = f"Yahoo Finance and FRED, downloaded {downloaded}"
    note(ws, f"D{ROWS['P0']}", f"Close of {d['as_of']:%d %b %Y}, not adjusted")
    note(ws, f"D{ROWS['D0']}", "Dividends paid in the 12 months to the price date" +
         ("".join(f". Includes {x}" for x in d["typed_divs"])))
    if d["country"]:
        fin = f", reports in {d['fin']}" if d["fin"] else ""
        note(ws, f"D{ROWS['currency']}", f"Company based in {d['country']}{fin}" +
             ("" if d["country"] == "United States" else ": this line trades in " + str(d["currency"])))
    note(ws, f"D{ROWS['g_yahoo']}", growth_note(d))
    first, last = d["cagr_years"]
    note(ws, f"D{ROWS['dps_cagr']}", f"{first}–{last}, calendar years: see the table below")
    if d["beta_end"] is not None:
        note(ws, f"D{ROWS['beta_calc']}", f"{d['months']} complete months to {d['beta_end']:%b %Y}, excess of the 1-month T-bill")
    if d["fy"]:
        fy = d["fy"]
        note(ws, f"D{ROWS['buyback_fy']}", f"FY{fy[-1]}, Repurchase Of Capital Stock, cash flow statement" +
             (f", from {d['fin']} at {d['fx']:.4f} ({d['fx_src']})" if d["fx"] else ""))
        if d["fx"]:
            per = d["adr"] or 1
            note(ws, f"D{ROWS['shares_fy']}", f"Per ADR: 1 ADR = {per:g} share{'s' if per != 1 else ''}"
                                              f"{'' if d['adr'] else ' (assumed)'}, as the price and dividends")
        note(ws, f"D{ROWS['bps_avg']}", f"FY{fy[-GROWTH_YEARS] if len(fy) >= GROWTH_YEARS else '?'}–FY{fy[-1]}: "
                                        "a check, buybacks are lumpy and cut first in a downturn")
        if len(fy) > GROWTH_YEARS:
            span = f"FY{fy[-1 - GROWTH_YEARS]}–FY{fy[-1]}"
            note(ws, f"D{ROWS['shares_chg']}", f"{span}, diluted average shares. Negative: buybacks shrink it")
            note(ws, f"D{ROWS['ni_growth']}", f"{span}: total growth, compare g1 with it when buybacks are in")
    for i, (year, value) in enumerate(d["dps"].items()):
        r = HIST_ROW + 2 + i
        ws[f"B{r}"].value = str(year)
        ws[f"C{r}"].value = value


def growth_note(d):
    """Where row g_yahoo comes from: the two estimates, the analysts and the page."""
    if d["g_yahoo"] is None:
        return f"No growth estimates on Yahoo ({d['g_src']})"
    fy = d["g_fy"]
    years = [f"FY{fy}" if fy else "current fiscal year", f"FY{fy + 1}" if fy else "next"]
    parts = [f"{y} {g:.1%}" for y, g in zip(years, (d["g_cy"], d["g_ny"])) if g is not None]
    n = [x for x in (d["g_analysts"] or []) if x]
    page = d["g_src"] + (f" (same company, more analysts than on {d['ticker']})" if d["g_src"] != d["ticker"] else "")
    analysts = f", {min(n)}–{max(n)} analysts" if n and min(n) != max(n) else f", {n[0]} analysts" if n else ""
    if d.get("g_next"):
        current = f"; {years[0]} {d['g_cy']:.1%} not used" if d["g_cy"] is not None else ""
        return (f"Next fiscal year{f' FY{fy + 1}' if fy else ''} {d['g_ny']:.1%}{current}: Yahoo, Analysis, Growth "
                f"Estimates, {page}{analysts}. Next year only, the team's choice of {G1_NEXT_YEAR_DATE}")
    return f"Average of {' and '.join(parts)}: Yahoo, Analysis, Growth Estimates, {page}{analysts}"


def yahoo_g1_value(d):
    """g1 from Yahoo's average growth estimate, rounded to 0.1%; else the 5-year dividend CAGR, clipped; else 5%."""
    if d["g_yahoo"] is not None:
        return round(d["g_yahoo"], 3)
    print(f"  {d['ticker']}: no Yahoo growth estimate, so g1 starts at the dividend CAGR or {G1_DEFAULT:.0%}")
    if d["dps_cagr"] is None:
        return G1_DEFAULT
    lo, hi = G1_BOUNDS
    return round(min(max(d["dps_cagr"], lo), hi), 3)


def new_sheet_assumptions(ws, d):
    """A new sheet: g1 from Yahoo, the payout with buybacks (the team's rule for every stock, 7 Nov 2026; P/FCF in the
    comps value is set in build_comps), and a non-US company's ERP. T stays at its default: the team sets it by hand."""
    ws[CELL["g1"]].value = yahoo_g1_value(d)
    ws[CELL["basis"]].value = DIVS_BB
    country = d["country"]
    if country and country != "United States":
        note(ws, f"D{ROWS['rf']}", "From Inputs: the US 10-year, as the price and dividends of this line are in "
                                   f"{d['currency']}")
        if country in COUNTRY_ERP:
            erp, rating, crp = COUNTRY_ERP[country]
            put(ws, CELL["erp"], erp, "input", PCT)
            note(ws, f"D{ROWS['erp']}", f"Damodaran, {country}, {ERP_DATE}. Total ERP: mature market 4.23% + country "
                                        f"risk premium {crp:.2%} (Moody's {rating}). Typed here, not on Inputs")
        else:
            print(f"  {d['ticker']}: based in {country}, not in COUNTRY_ERP: type its Damodaran ERP in the sheet")


# ---------------------------------------------------------------- workbook

def set_market(wsi, market):
    wsi[INP["as_of"]].value = market["as_of"]
    wsi[INP["rf"]].value = market["rf"]
    note(wsi, f"D{INP['as_of'][1:]}", "Set by the script: the latest close it used. Final run: --as-of 2026-11-06")
    note(wsi, f"D{INP['rf'][1:]}", f"FRED DGS10 on {market['rf_date']:%d %b %Y}, set by the script")


def new_workbook():
    wb = Workbook()
    build_summary(wb.active)
    wb.active.title = "Summary"
    build_inputs(wb.create_sheet("Inputs"))
    dgs10 = fred_series("DGS10").dropna() / 100       # so the template works before any stock is added
    set_market(wb["Inputs"], {"as_of": dgs10.index[-1].to_pydatetime(), "rf": float(dgs10.iloc[-1]),
                              "rf_date": dgs10.index[-1]})
    build_stock(wb.create_sheet("Template"))
    build_comps(wb["Template"])
    ex = wb.create_sheet("Example NKE")
    build_stock(ex)
    fill_example(ex)
    build_comps(ex)
    fill_example_comps(ex)
    return wb


def save(wb, path):
    wb.calculation = CalcProperties(fullCalcOnLoad=True)   # openpyxl stores no results: Excel computes on open
    wb.active = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def yaml_peers(t):
    """The peers of runs/round2/inputs/<TICKER>.yaml, if the stock has a report."""
    import yaml
    path = REPO / "runs" / "round2" / "inputs" / f"{t}.yaml"
    if not path.exists():
        return []
    return [str(p).upper() for p in (yaml.safe_load(path.read_text()) or {}).get("peers") or []]


def propose_peers(yf, t, info):
    """A later ticker without peers: the largest US-listed companies of its Yahoo industry. To check on Bloomberg RV."""
    key = info.get("industryKey")
    try:
        top = yf.Industry(key).top_companies if key else None
    except Exception:
        top = None
    if top is None or len(top) == 0:
        return [], key
    same = {t.upper(), *(x.upper() for x in ESTIMATES_FROM.get(t, "").split()), "GOOGL" if t == "GOOG" else "GOOG"}
    return [x.upper() for x in top.index if "." not in x and x.upper() not in same][:N_PEERS], key


def choose_peers(yf, ws, t, d):
    """The peers of a sheet: typed in it; else the stock's YAML; else PEERS; else proposed from Yahoo's industry."""
    typed = sheet_peers(ws)
    if typed:
        return typed, None if ws[CELL_C("source")].value else "Typed in the sheet"
    for peers, source in ((yaml_peers(t), f"From {t}.yaml (the stock report's peers)"),
                          (PEERS.get(t, []), f"Proposed by Claude, {PEERS_DATES.get(t, PEERS_DATE)}: check on Bloomberg RV")):
        if peers:
            break
    else:
        peers, key = propose_peers(yf, t, d["comps_info"])
        source = f"Proposed from Yahoo's industry list ({key}), {PEERS_DATE}: check on Bloomberg RV"
        print(f"  {t}: peers proposed from Yahoo's industry ({key}): {', '.join(peers) or 'none found'}")
    for i in range(N_PEERS):
        ws[f"C{CR['peer0'] + i}"].value = peers[i] if i < len(peers) else None
    return peers, source


def download_peers(peers):
    """Yahoo info and statements of each peer, once even when several stocks share it, as the stock report."""
    import yfinance as yf
    out = {}
    print(f"Downloading {len(peers)} peers for the comparables ...")
    for p in sorted(peers):
        tk = yf.Ticker(p)
        try:
            i = retry(lambda: tk.info, f"{p} info")
            st = retry(lambda: statements_of(tk), f"{p} statements")
        except SystemExit as e:
            print(f"  {p}: {e}. Left out of the comps")
            continue
        if not i.get("marketCap"):
            print(f"  {p}: Yahoo has no market data. Check the ticker; left out of the comps")
            continue
        out[p] = ({k: i.get(k) for k in INFO_KEYS}, to_records(st))
    return out


def add_stocks(wb, tickers, as_of_arg, g1_yahoo=False):
    import yfinance as yf
    data, market = download(tickers, as_of_arg)
    if not data:
        raise SystemExit("Nothing downloaded: no workbook written")
    downloaded = datetime.now(ZoneInfo("Europe/Zurich")).strftime("%d %b %Y %H:%M")
    wsi = wb["Inputs"]
    set_market(wsi, market)
    write_inputs_text(wsi)
    for name in wb.sheetnames:            # sheets from an older version of the script, the Template included
        if name not in ("Summary", "Inputs", "Example NKE"):
            update_layout(wb[name])
        if name not in ("Summary", "Inputs"):
            build_comps(wb[name])          # every stock sheet has the comps block from row 101
    if "Example NKE" in wb.sheetnames:
        if wb["Example NKE"][CELL_C("eps_fwd")].value is None:
            fill_example_comps(wb["Example NKE"])
        else:
            example_comps_note(wb["Example NKE"])     # build_comps above reset it
    erp_us = wsi[INP["erp"]].value if isinstance(wsi[INP["erp"]].value, (int, float)) else ERP_DEFAULT

    sheets, peers_of, sources = {}, {}, {}
    for t, d in data.items():
        if t in wb.sheetnames:
            ws, status = wb[t], "refreshed, assumptions kept"
            if g1_yahoo:
                ws[CELL["g1"]].value = yahoo_g1_value(d)
                status = "refreshed, g1 from Yahoo, other assumptions kept"
        else:
            at = wb.sheetnames.index("Template") if "Template" in wb.sheetnames else len(wb.sheetnames)
            ws, status = wb.create_sheet(t, at), "added"
            build_stock(ws)
            new_sheet_assumptions(ws, d)
            build_comps(ws)
        fill_data(ws, d, downloaded)
        add_to_summary(wb["Summary"], t)
        sheets[t] = (ws, status)
        peers_of[t], sources[t] = choose_peers(yf, ws, t, d)
    summary_comps(wb["Summary"])

    peer_data = download_peers({p for ps in peers_of.values() for p in ps})
    infos = [d["comps_info"] for d in data.values()] + [i for i, _ in peer_data.values()]
    fx = fetch_fx(fx_pairs(infos), market["as_of"])

    print(f"\n{'':6}{'P0':>9}{'D0 used':>9}{'beta':>7}{'ERP':>7}{'k':>8}{'g1':>7}{'T':>3}{'GGM':>9}{'2-stage':>9}"
          f"{'comps':>9}{'MoS':>8}{'comps MoS':>10}  DDM vs comps   (rf {market['rf']:.2%})")
    for t, d in data.items():
        ws, status = sheets[t]
        # the values Excel will show, for a quick read in the terminal
        num = lambda key, dflt: ws[CELL[key]].value if isinstance(ws[CELL[key]].value, (int, float)) else dflt  # noqa: E731
        beta = num("beta_over", d["beta_calc"] or 0.0)
        erp = num("erp", erp_us)
        k = market["rf"] + beta * erp
        g1, g2, T = num("g1", G1_DEFAULT), num("g2", G2_DEFAULT), int(num("T", T_DEFAULT))
        g = num("g", g2)
        with_bb = ws[CELL["basis"]].value == DIVS_BB and d["buyback_fy"] is not None and d["shares_fy"]
        D = d["D0"] + (d["buyback_fy"] / d["shares_fy"] if with_bb else 0.0)
        v_ggm = gordon(D, k, g) if D > 0 and k > g else None
        v_two = two_stage(D, k, g1, g2, T) if D > 0 and k > g2 else None
        v0 = v_ggm if ws[CELL["method"]].value == "GGM" else v_two
        mos = v0 / d["P0"] - 1 if v0 is not None else None

        # the comparables, with the stock report's code on the same data as the sheet
        peers = [p for p in peers_of[t] if p in peer_data]
        snap = {"ticker": t, "peers": peers, "fx": fx, "info": {t: d["comps_info"], **{p: peer_data[p][0] for p in peers}},
                "statements": {t: d["comps_st"], **{p: peer_data[p][1] for p in peers}}}
        primary, stat = comps_choices(ws)
        cp = comps_from_snapshot(snap, d["P0"], D, d["eps_next"], primary, stat)
        fill_comps(ws, cp, sources[t])
        v_c = cp["V_comp"]
        mos_c = v_c / d["P0"] - 1 if v_c is not None else None
        verdict = methods_verdict(mos, mos_c)

        f = lambda x, w=9, fmt="{:.2f}": (fmt.format(x) if x is not None else "n/a").rjust(w)   # noqa: E731
        basis = "with buybacks" if with_bb else "dividends"
        print(f"{t:6}{d['P0']:9.2f}{D:9.3f}{beta:7.3f}{erp:7.2%}{k:8.2%}{g1:7.1%}{T:3d}{f(v_ggm)}{f(v_two)}"
              f"{f(v_c)}{f(mos, 8, '{:+.1%}')}{f(mos_c, 10, '{:+.1%}')}  {verdict:14} {basis}, {status}")
        if not with_bb and d["buyback_fy"] and d["shares_fy"] and d["buyback_fy"] / d["shares_fy"] > d["D0"]:
            print(f"{'':6}buybacks ({d['buyback_fy'] / d['shares_fy']:.2f} a share) exceed dividends: "
                  f"consider {DIVS_BB} in the sheet")
        missing = [p for p in peers_of[t] if p not in peer_data]
        if len(peers_of[t]) < 5 or missing:
            print(f"{'':6}comps: {len(peers)} peers with data" + (f", no data for {', '.join(missing)}" if missing else ""))


def main():
    ap = argparse.ArgumentParser(description="Build the Round 2 DDM workbook (GGM and two-stage), or add stocks to it.")
    ap.add_argument("tickers", nargs="*", help="Yahoo tickers to add or refresh, e.g. KO PEP NESN.SW")
    ap.add_argument("--as-of", help="Price date, YYYY-MM-DD. The final numbers use 2026-11-06. Default: latest close")
    ap.add_argument("--out", type=Path, default=WORKBOOK, help=f"Workbook path (default {WORKBOOK.relative_to(REPO)})")
    ap.add_argument("--new", action="store_true", help="Start a new workbook even if one exists (loses your edits)")
    ap.add_argument("--g1-yahoo", action="store_true",
                    help="Also reset g1 of stocks already in the workbook to Yahoo's average earnings growth estimate "
                         "(new sheets always start from it)")
    args = ap.parse_args()

    path = args.out.resolve()
    if (path.parent / f"~${path.name}").exists():
        raise SystemExit(f"{path.name} is open in Excel: close it, then run again")
    tickers = [t.strip().upper() for t in args.tickers if t.strip()]

    if path.exists() and not args.new:
        if not tickers:
            raise SystemExit(f"{path} exists. Give tickers to add stocks, or --new to start a blank one (loses your edits)")
        wb = load_workbook(path)
    else:
        wb = new_workbook()
    if tickers:
        add_stocks(wb, tickers, args.as_of, args.g1_yahoo)
    save(wb, path)
    print(f"\nWrote {path.relative_to(REPO) if path.is_relative_to(REPO) else path}")


if __name__ == "__main__":
    main()
