#!/usr/bin/env python3
"""DDM valuation workbook for Round 2: Gordon Growth Model and two-stage DDM, one sheet per stock.

    python3 scripts/build_ddm_workbook.py                          the blank template
    python3 scripts/build_ddm_workbook.py KO PEP JNJ               add stocks, or refresh their data
    python3 scripts/build_ddm_workbook.py KO --as-of 2026-11-06    prices of a given date (final numbers)

Writes runs/round2/inputs/DDM_valuation.xlsx (or --out). Close it in Excel first.

The workbook does the valuation with Excel formulas, so every assumption can be changed in Excel:
  Summary      one row per stock: values, margin of safety, signal, flags
  Inputs       shared by all stocks: rf (10-year Treasury), ERP, buy threshold, flag levels
  <TICKER>     data, CAPM, growth assumptions, GGM, two-stage DDM with its schedule, sensitivity grids
  Template     a blank stock sheet, to duplicate by hand
  Example NKE  the TA notebook's Nike case, which checks the formulas (GGM 23.24, two-stage 29.78)

A stock already in the workbook gets new data (blue cells) only: your assumptions (yellow) stay.
The formulas follow the Round 2 cheat sheet (§3-§4) and scripts/build_stock_report.py:
k = rf10 + beta x ERP, beta on SPY over 60 complete months, D0 = dividends of the last 12 months,
MoS = V0 / P0 - 1.
"""

import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_stock_report import (ERP_DEFAULT, HISTORY_YEARS, WINDOW, complete_month_end,  # noqa: E402
                                fred_series, gordon, retry, two_stage)

REPO = Path(__file__).resolve().parent.parent
WORKBOOK = REPO / "runs" / "round2" / "inputs" / "DDM_valuation.xlsx"

G1_DEFAULT, T_DEFAULT, G2_DEFAULT = 0.05, 5, 0.02   # as in runs/round2/inputs/_TEMPLATE.yaml
G1_BOUNDS = (0.0, 0.15)                             # the 5-year dividend CAGR used as default g1 is clipped to this
T_MAX = 20                                          # rows of the two-stage schedule
HIST_YEARS = 6                                      # calendar years in the dividend table
SUMMARY_ROWS = 20                                   # rows prepared in Summary; more are added when needed

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


def build_inputs(ws):
    title(ws, "DDM valuation: inputs shared by all stocks",
          "Change the yellow cells. Every stock sheet and the Summary follow them.")
    widths(ws, {"A": 2, "B": 40, "C": 14, "D": 70})
    section(ws, 5, "Market and rules")
    rows = [
        ("as_of", "Price date", "data", None, DATE, "Set by the script: the latest close it used"),
        ("rf", "Risk-free rate rf, 10-year Treasury", "data", None, PCT, "FRED DGS10, set by the script"),
        ("erp", "Equity risk premium ERP", "input", ERP_DEFAULT, PCT,
         "Bloomberg CRP, Class 5: the same for all stocks. Refresh it before the final run"),
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
    steps = [
        "1. Add stocks: python3 scripts/build_ddm_workbook.py KO PEP (from the repo root, with this file closed in Excel).",
        "    It adds one sheet per ticker and a row in Summary. Run it again for a stock already here and only the blue cells change.",
        "2. Or by hand: right-click Template > Move or Copy > Create a copy, rename it to the ticker, type the blue cells,",
        "    then type the sheet name in the Ticker column of Summary.",
        "3. In each stock sheet, set the yellow cells: g1 (Bloomberg BDVD or EE), T, g2, the method, and the β override if you use Bloomberg BETA.",
        "4. Final numbers: run the script again with --as-of 2026-11-06 (the challenge uses the close of Friday 6 November).",
        "5. Don't insert rows or columns in the stock sheets: Summary reads fixed cells.",
    ]
    for i, text in enumerate(steps):
        label(ws, f"B{22 + i}", text)

    section(ws, 30, "Formulas (Round 2 cheat sheet §3–§4)")
    formulas = [
        "Cost of equity:  k = rf + β × ERP, with β the slope of 60 monthly excess returns on SPY",
        "Gordon Growth Model:  V0 = D0 (1 + g) / (k − g), needs k > g. For a mature company with stable growth",
        "Two-stage DDM:  V0 = Σ D0 (1 + g1)^t / (1 + k)^t for t = 1 … T  +  [D_T (1 + g2) / (k − g2)] / (1 + k)^T",
        "    For a company not yet in its normal state. g1 can be above k; g2 must be below k",
        "Margin of safety:  MoS = V0 / P0 − 1 (cheat sheet). Discount to value = 1 − P0 / V0 (Class 5, Graham)",
        "D0: dividends per share paid over the last 12 months. The first dividend discounted is D1 = D0 (1 + g)",
    ]
    for i, text in enumerate(formulas):
        label(ws, f"B{31 + i}", text)
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
    ("payout", "Payout D0 / EPS", "formula", '=IF(N({eps_ttm})>0,{D0}/{eps_ttm},"")', PCT1,
     "Above 100%: earnings don't cover the dividend"),
    ("roe", "ROE", "data", None, PCT1, ""),
    ("g_sust", "Sustainable growth ROE × (1 − payout)", "formula",
     '=IF(AND(ISNUMBER({roe}),ISNUMBER({payout})),{roe}*(1-{payout}),"")', PCT, "A ceiling for long-run growth"),
    ("dps_cagr", "Dividend growth, last 5 years (CAGR)", "data", None, PCT, "Calendar years: see the table below"),
    ("eps_growth", "EPS growth next year (consensus)", "data", None, PCT, ""),
    ("beta_calc", "β, 60 months on SPY", "data", None, BETA, "Monthly excess returns, as in the cheat sheet"),
    ("beta_yahoo", "β, Yahoo", "data", None, BETA, "Reference only"),
    ("section", "Cost of equity (CAPM)"),
    ("rf", "Risk-free rate rf, 10-year Treasury", "link", "=" + inp("rf"), PCT, "From Inputs"),
    ("erp", "Equity risk premium ERP", "link", "=" + inp("erp"), PCT, "From Inputs"),
    ("beta_over", "β override (optional)", "input", None, BETA, "e.g. Bloomberg BETA. Leave empty to use the 60-month β"),
    ("beta", "β used", "formula", "=IF(ISNUMBER({beta_over}),{beta_over},N({beta_calc}))", BETA, ""),
    ("k", "Cost of equity k = rf + β × ERP", "formula", "={rf}+{beta}*{erp}", PCT, ""),
    ("section", "Growth assumptions"),
    ("g1", "g1, growth in stage 1", "input", G1_DEFAULT, PCT, "Bloomberg BDVD or EE (consensus)"),
    ("T", f"T, years in stage 1 (1–{T_MAX})", "input", T_DEFAULT, INT, "Years the company needs to reach its normal state"),
    ("g2", "g2, growth after T (terminal)", "input", G2_DEFAULT, PCT, "Below k, close to long-run economic growth"),
    ("g", "g, Gordon growth", "input", "={g2}", PCT, "Equal to g2 unless you type a number here"),
    ("method", "Method for the fair value", "input", "Two-stage", None,
     "Two-stage: not yet in its normal state. GGM: mature, stable growth"),
    ("section", "Gordon Growth Model"),
    ("D1", "D1 = D0 × (1 + g)", "formula", "={D0}*(1+{g})", PRICE3, ""),
    ("V_ggm", "Value V0 = D1 / (k − g)", "formula",
     '=IF(N({D0})<=0,"n/a: no dividend",IF({k}>{g},{D1}/({k}-{g}),"n/a: k ≤ g"))', PRICE, ""),
    ("mos_ggm", "Margin of safety V0 / P0 − 1", "formula",
     '=IF(AND(ISNUMBER({V_ggm}),N({P0})>0),{V_ggm}/{P0}-1,"")', PCT1, ""),
    ("disc_ggm", "Discount to value 1 − P0 / V0", "formula",
     '=IF(AND(ISNUMBER({V_ggm}),N({V_ggm})>0),1-{P0}/{V_ggm},"")', PCT1, "Class 5: buy below 80% of value = at least 20% here"),
    ("implied_g", "Growth implied by the price", "formula",
     '=IF(N({P0})>0,({k}*{P0}-{D0})/({P0}+{D0}),"")', PCT, "Reverse Gordon: the constant g that gives V0 = P0"),
    ("section", "Two-stage DDM"),
    ("pv1", "PV of the dividends of years 1 to T", "formula", "=SUM({pv_col})", PRICE, "Schedule on the right"),
    ("DT", "D_T, dividend in year T", "formula", "={D0}*(1+{g1})^{T}", PRICE3, ""),
    ("TV", "Terminal value at T = D_T (1 + g2) / (k − g2)", "formula",
     '=IF({k}>{g2},{DT}*(1+{g2})/({k}-{g2}),"n/a: k ≤ g2")', PRICE, ""),
    ("pv_tv", "PV of the terminal value", "formula", '=IF(ISNUMBER({TV}),{TV}/(1+{k})^{T},"")', PRICE, ""),
    ("V_2s", "Value V0", "formula",
     '=IF(N({D0})<=0,"n/a: no dividend",IF(ISNUMBER({pv_tv}),{pv1}+{pv_tv},"n/a: k ≤ g2"))', PRICE, ""),
    ("tv_share", "Terminal value, share of V0", "formula",
     '=IF(AND(ISNUMBER({V_2s}),N({V_2s})>0),{pv_tv}/{V_2s},"")', PCT1, "A high share means the value rests on g2 and k"),
    ("mos_2s", "Margin of safety V0 / P0 − 1", "formula",
     '=IF(AND(ISNUMBER({V_2s}),N({P0})>0),{V_2s}/{P0}-1,"")', PCT1, ""),
    ("disc_2s", "Discount to value 1 − P0 / V0", "formula",
     '=IF(AND(ISNUMBER({V_2s}),N({V_2s})>0),1-{P0}/{V_2s},"")', PCT1, ""),
    ("section", "Fair value"),
    ("fv_method", "Method", "formula", "={method}", None, "Chosen in Growth assumptions"),
    ("V0", "Fair value V0", "result", '=IF({method}="GGM",{V_ggm},{V_2s})', PRICE, ""),
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
GRID1_ROW = SCHED_ROW + T_MAX + 4                        # title of the first sensitivity grid
GRID2_ROW = GRID1_ROW + 9


def flags_formula():
    a = A
    parts = (f'IF(N({a["D0"]})<=0,"No dividend: DDM not applicable. ","")'
             f'&IF(AND(ISNUMBER({a["mos"]}),N({a["mos"]})>{inp("flag_up")}),'
             f'"Upside above "&TEXT({inp("flag_up")},"0%")&": check the inputs (value trap?). ","")'
             f'&IF({a["k"]}-{a["g2"]}<{inp("spread")},"k − g2 below "&TEXT({inp("spread")},"0%")&". ","")'
             f'&IF(AND(ISNUMBER({a["payout"]}),N({a["payout"]})>1),"Payout above 100%. ","")'
             f'&IF({a["g"]}>={a["k"]},"GGM not valid: g ≥ k. ","")'
             f'&IF(AND({a["currency"]}<>"",{a["currency"]}<>"USD"),"In "&{a["currency"]}&": rf and ERP are US figures. ","")')
    return f'=IF(N({a["P0"]})<=0,"",IF(({parts})="","None",TRIM({parts})))'


def two_stage_cell(k, g2):
    """Closed-form two-stage value for one cell of the grid; k and g2 are cell references."""
    D0, g1, T = A["D0"], A["g1"], A["T"]
    stage1 = f"IF(ABS({k}-{g1})<1E-9,{D0}*{T},{D0}*(1+{g1})/({k}-{g1})*(1-((1+{g1})/(1+{k}))^{T}))"
    terminal = f"{D0}*(1+{g1})^{T}*(1+{g2})/(({k}-{g2})*(1+{k})^{T})"
    return f'=IF({k}<={g2},"n/a",{stage1}+{terminal})'


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
        elif isinstance(content, str) and content.startswith("="):
            content = content.format(**A)
        bold = key in ("V_ggm", "V_2s")
        put(ws, f"C{r}", content, kind, fmt, bold=bold)
        if why:
            note(ws, f"D{r}", why)
    ws[CELL["flags"]].alignment = Alignment(wrap_text=False)

    dv = DataValidation(type="list", formula1='"Two-stage,GGM"', allow_blank=False, showErrorMessage=True,
                        errorTitle="Method", error="Choose Two-stage or GGM")
    dv.add(CELL["method"])
    dvt = DataValidation(type="whole", operator="between", formula1="1", formula2=str(T_MAX), showErrorMessage=True,
                         errorTitle="T", error=f"T is a whole number of years from 1 to {T_MAX}")
    dvt.add(CELL["T"])
    ws.add_data_validation(dv)
    ws.add_data_validation(dvt)
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

    # two-stage schedule
    section(ws, ROW0, "Two-stage schedule (stage 1)", cols="FGHIJ")
    for col, text in zip("FGHIJ", ("Year t", "Stage", "Dividend D_t", "Discount factor", "PV of D_t")):
        c = put(ws, f"{col}{SCHED_ROW - 1}", text, "formula", bold=True)
        c.alignment = Alignment(horizontal="center")
    for t in range(1, T_MAX + 1):
        r = SCHED_ROW + t - 1
        put(ws, f"F{r}", t, "formula", INT).alignment = Alignment(horizontal="center")
        put(ws, f"G{r}", f'=IF(F{r}<={A["T"]},"Stage 1","")', "formula").alignment = Alignment(horizontal="center")
        put(ws, f"H{r}", f'=IF(F{r}<={A["T"]},{A["D0"]}*(1+{A["g1"]})^F{r},"")', "formula", PRICE3)
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
         lambda k, g: f'=IF({k}<={g},"n/a",{A["D0"]}*(1+{g})/({k}-{g}))')

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


# ---------------------------------------------------------------- Summary sheet

SUMMARY_COLS = [   # header, key in the stock sheet, number format, width
    ("Ticker", None, None, 10), ("Company", "name", None, 26), ("Price P0", "P0", PRICE, 10), ("D0", "D0", PRICE3, 9),
    ("Yield", "yield_", PCT, 8), ("β", "beta", BETA, 7), ("k", "k", PCT, 8), ("g1", "g1", PCT, 8), ("T", "T", INT, 5),
    ("g2", "g2", PCT, 8), ("GGM V0", "V_ggm", PRICE, 10), ("GGM MoS", "mos_ggm", PCT1, 9),
    ("Two-stage V0", "V_2s", PRICE, 12), ("Two-stage MoS", "mos_2s", PCT1, 12), ("Method", "method", None, 10),
    ("Fair value", "V0", PRICE, 10), ("MoS", "mos", PCT1, 9), ("Signal", "signal", None, 11), ("Flags", "flags", None, 70),
]
SUM_HDR, SUM_ROW0 = 5, 6
SUM_COLS = "BCDEFGHIJKLMNOPQRST"


def summary_row(ws, r):
    for (head, key, fmt, _), col in zip(SUMMARY_COLS, SUM_COLS):
        if key is None:
            put(ws, f"{col}{r}", None, "input")
            continue
        formula = f'=IF($B{r}="","",IFERROR(INDIRECT("\'"&$B{r}&"\'!{CELL[key]}"),""))'
        bold = key in ("V0", "mos")
        put(ws, f"{col}{r}", formula, "formula", fmt, bold=bold)


def build_summary(ws):
    title(ws, "DDM valuation: summary", "One row per stock sheet. Type a sheet name under Ticker, or let the script do it.")
    label(ws, "B4", "Buy threshold: MoS ≥")
    put(ws, "D4", "=" + inp("buy"), "link", PCT1)
    for (head, key, fmt, width), col in zip(SUMMARY_COLS, SUM_COLS):
        c = put(ws, f"{col}{SUM_HDR}", head, "formula", bold=True)
        c.fill, c.border = fill(HEAD), Border(bottom=THIN)
        c.alignment = Alignment(horizontal="left" if key in (None, "name", "flags") else "center")
        ws.column_dimensions[col].width = width
    ws.column_dimensions["A"].width = 2
    for r in range(SUM_ROW0, SUM_ROW0 + SUMMARY_ROWS):
        summary_row(ws, r)
    format_summary(ws, SUM_ROW0 + SUMMARY_ROWS - 1)
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
        divs = divs.loc[:as_of]
        D0 = float(divs.loc[divs.index > as_of - pd.Timedelta(days=365)].sum())
        years = list(range(as_of.year - HIST_YEARS, as_of.year))          # complete calendar years
        dps = {y: float(divs[divs.index.year == y].sum()) for y in years}
        last, first = years[-1], years[-1] - 5
        cagr = (dps[last] / dps[first]) ** (1 / 5) - 1 if dps.get(first, 0) > 0 and dps[last] > 0 else None

        info = retry(lambda: tk.info, f"{t} info")
        try:
            eps_growth = float(tk.earnings_estimate.loc["+1y", "growth"])
        except Exception:                      # no estimates on Yahoo for this ticker
            eps_growth = None

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
            "roe": num("returnOnEquity"), "dps_cagr": cagr, "eps_growth": eps_growth, "beta_calc": beta,
            "beta_yahoo": num("beta"), "dps": dps, "months": len(Re), "beta_end": Re.index[-1] if len(Re) else None,
            "cagr_years": (first, last),
        }
        if D0 <= 0:
            print(f"  {t}: no dividend in the last 12 months, so the DDM does not apply")
        if len(Re) < WINDOW:
            print(f"  {t}: only {len(Re)} months of returns for beta, not {WINDOW}")

    as_of = max((d["as_of"] for d in out.values()), default=cutoff.to_pydatetime())
    dgs10 = rates["DGS10"].dropna().loc[:as_of]
    return out, {"as_of": as_of, "rf": float(dgs10.iloc[-1]), "rf_date": dgs10.index[-1]}


def fill_data(ws, d, downloaded):
    """Write the blue cells of a stock sheet. Assumptions (yellow) are not touched."""
    for key in ("ticker", "name", "sector", "currency", "as_of", "P0", "D0", "div_rate", "eps_ttm", "eps_fwd", "roe",
                "dps_cagr", "eps_growth", "beta_calc", "beta_yahoo"):
        ws[CELL[key]].value = d[key]
    ws[CELL["source"]].value = f"Yahoo Finance and FRED, downloaded {downloaded}"
    note(ws, f"D{ROWS['P0']}", f"Close of {d['as_of']:%d %b %Y}, not adjusted")
    first, last = d["cagr_years"]
    note(ws, f"D{ROWS['dps_cagr']}", f"{first}–{last}, calendar years: see the table below")
    if d["beta_end"] is not None:
        note(ws, f"D{ROWS['beta_calc']}", f"{d['months']} complete months to {d['beta_end']:%b %Y}, excess of the 1-month T-bill")
    for i, (year, value) in enumerate(d["dps"].items()):
        r = HIST_ROW + 2 + i
        ws[f"B{r}"].value = str(year)
        ws[f"C{r}"].value = value


def default_g1(ws, d):
    """New sheet: g1 starts at the 5-year dividend CAGR, clipped, until you type the Bloomberg figure."""
    lo, hi = G1_BOUNDS
    if d["dps_cagr"] is None:
        why = f"Default {G1_DEFAULT:.0%}: no 5-year dividend history. Replace with Bloomberg BDVD or EE"
        g1 = G1_DEFAULT
    else:
        g1 = round(min(max(d["dps_cagr"], lo), hi), 3)
        why = f"Default: 5-year dividend CAGR ({d['dps_cagr']:.1%}). Replace with Bloomberg BDVD or EE"
    ws[CELL["g1"]].value = g1
    note(ws, f"D{ROWS['g1']}", why)
    return g1


# ---------------------------------------------------------------- workbook

def set_market(wsi, market):
    wsi[INP["as_of"]].value = market["as_of"]
    wsi[INP["rf"]].value = market["rf"]
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
    ex = wb.create_sheet("Example NKE")
    build_stock(ex)
    fill_example(ex)
    return wb


def save(wb, path):
    wb.calculation = CalcProperties(fullCalcOnLoad=True)   # openpyxl stores no results: Excel computes on open
    wb.active = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def add_stocks(wb, tickers, as_of_arg):
    data, market = download(tickers, as_of_arg)
    if not data:
        raise SystemExit("Nothing downloaded: no workbook written")
    downloaded = datetime.now(ZoneInfo("Europe/Zurich")).strftime("%d %b %Y %H:%M")
    wsi = wb["Inputs"]
    set_market(wsi, market)
    erp = wsi[INP["erp"]].value if isinstance(wsi[INP["erp"]].value, (int, float)) else ERP_DEFAULT

    print(f"\n{'':6}{'P0':>9}{'D0':>8}{'beta':>7}{'k':>8}{'g1':>7}{'GGM':>9}{'2-stage':>9}   (rf {market['rf']:.2%})")
    for t, d in data.items():
        if t in wb.sheetnames:
            ws, status = wb[t], "refreshed, assumptions kept"
        else:
            at = wb.sheetnames.index("Template") if "Template" in wb.sheetnames else len(wb.sheetnames)
            ws, status = wb.create_sheet(t, at), "added"
            build_stock(ws)
            default_g1(ws, d)
        fill_data(ws, d, downloaded)
        add_to_summary(wb["Summary"], t)

        # the values Excel will show, for a quick read in the terminal
        num = lambda key, dflt: ws[CELL[key]].value if isinstance(ws[CELL[key]].value, (int, float)) else dflt  # noqa: E731
        beta = num("beta_over", d["beta_calc"] or 0.0)
        k = market["rf"] + beta * erp
        g1, g2, T = num("g1", G1_DEFAULT), num("g2", G2_DEFAULT), int(num("T", T_DEFAULT))
        g = num("g", g2)
        ggm = f"{gordon(d['D0'], k, g):9.2f}" if d["D0"] > 0 and k > g else f"{'n/a':>9}"
        two = f"{two_stage(d['D0'], k, g1, g2, T):9.2f}" if d["D0"] > 0 and k > g2 else f"{'n/a':>9}"
        print(f"{t:6}{d['P0']:9.2f}{d['D0']:8.3f}{beta:7.3f}{k:8.2%}{g1:7.1%}{ggm}{two}   {status}")


def main():
    ap = argparse.ArgumentParser(description="Build the Round 2 DDM workbook (GGM and two-stage), or add stocks to it.")
    ap.add_argument("tickers", nargs="*", help="Yahoo tickers to add or refresh, e.g. KO PEP NESN.SW")
    ap.add_argument("--as-of", help="Price date, YYYY-MM-DD. The final numbers use 2026-11-06. Default: latest close")
    ap.add_argument("--out", type=Path, default=WORKBOOK, help=f"Workbook path (default {WORKBOOK.relative_to(REPO)})")
    ap.add_argument("--new", action="store_true", help="Start a new workbook even if one exists (loses your edits)")
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
        add_stocks(wb, tickers, args.as_of)
    save(wb, path)
    print(f"\nWrote {path.relative_to(REPO) if path.is_relative_to(REPO) else path}")


if __name__ == "__main__":
    main()
