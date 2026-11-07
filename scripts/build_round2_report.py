#!/usr/bin/env python3
"""Assemble the Round 2 report from the files promoted into report/figures/, and export it.

    python scripts/build_round2_report.py            refresh report/round2-equity.dc.html
    python scripts/build_round2_report.py --pdf      and export report/pdf/Matterhorn_Round2_Equity.pdf

The report is an ordinary .dc.html: write its text by hand. Only the blocks between <!-- auto:NAME --> and
<!-- /auto:NAME --> are rewritten, from what scripts/promote.py put in report/figures/:
  round2-round1_performance.json   Round 1 results and positions (scripts/round1_performance.py)
  round1-report_figures.json       the Round 1 report's ex-ante figures, to compare with
  round2-<TICKER>.dc.html          two pages per stock (scripts/build_stock_report.py)
  round2-portfolio.json            Treynor-Black and the new portfolio (scripts/build_round2_portfolio.py)
What is not there yet shows as a placeholder; an empty stock slot shows the stock layout with [TO FILL].
The page numbers in the footers are rewritten every time. The layout is Round 1's (report/round1-saa.dc.html).
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_stock_report as bsr                                  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
REPORT = REPO / "report"
SOURCE = REPORT / "round2-equity.dc.html"
FIGURES = REPORT / "figures"
PDF = REPORT / "pdf" / "Matterhorn_Round2_Equity.pdf"
SLOTS = 6
FINAL_DATE = "2026-11-06"          # the guidelines: Round 1 performance to Friday 6 November, trades at that close

INK, MUTED, CARD, LINE, LINE_B, REF = "#111111", "#615e5b", "#f3efeb", "#e9eaeb", "#d8d3cc", "#888888"
MONO = "font-family:'Geist Mono',monospace;"
SANS = "font-family:'Geist',sans-serif;"
DASH = "—"


# ---------------------------------------------------------------- formatting, as printed in Round 1

def minus(s):
    return s.replace("-", "−")


def pct(x, d=2, plus=False):
    return DASH if x is None else minus(f"{x * 100:+.{d}f}%" if plus else f"{x * 100:.{d}f}%")


def num(x, d=2):
    return DASH if x is None else minus(f"{x:,.{d}f}")


def usd(x, d=0):
    return DASH if x is None else minus(f"USD {x:,.{d}f}")


def short(s):
    return pd.Timestamp(s).strftime("%d.%m.%y")


def long_date(s):
    t = pd.Timestamp(s)
    return f"{t.day} {t:%B %Y}"


def esc(s):
    return html.escape(str(s), quote=False)


# ---------------------------------------------------------------- blocks, copied from the Round 1 markup

def stat_row(items):
    cells = "".join(f'<div style="display:flex;flex-direction:column;gap:4px;"><span style="font-size:10px;font-weight:600;letter-spacing:0.3px;'
                    f'text-transform:uppercase;color:{MUTED};">{a}</span><span style="{MONO}font-size:20px;font-weight:600;">{b}</span>'
                    f'<span style="font-size:10px;color:{MUTED};">{c}</span></div>' for a, b, c in items)
    return (f'<div style="background:{CARD};border-radius:20px;padding:14px 20px;display:grid;grid-template-columns:repeat({len(items)},1fr);'
            f'gap:14px;">{cells}</div>')


def title(text, right=""):
    t = f'<span style="font-size:12px;font-weight:600;letter-spacing:0.36px;text-transform:uppercase;">{text}</span>'
    return f'<div style="display:flex;justify-content:space-between;align-items:baseline;">{t}{right}</div>' if right else t


def caption(text):
    return f'<span style="font-size:10.5px;line-height:1.45;color:{MUTED};font-style:italic;">{text}</span>'


def table(head, rows, size=12, pad=5):
    """head: [(title, align)]; rows: (cells, kind) with kind "", "group", "muted", "total". A cell is text or (text, extra style)."""
    ths = "".join(f'<th style="padding:6px 0{" 6px 12px" if i else ""};font-weight:600;text-align:{h[1]};{h[2] if len(h) > 2 else ""}">{h[0]}</th>'
                  for i, h in enumerate(head))
    out = [f'<table style="width:100%;border-collapse:collapse;font-size:{size}px;"><thead><tr style="border-bottom:1px solid {INK};font-size:10px;'
           f'letter-spacing:0.3px;text-transform:uppercase;color:{MUTED};">{ths}</tr></thead><tbody>']
    last = max((i for i, r in enumerate(rows) if r[1] != "group"), default=-1)
    for n, (cells, kind) in enumerate(rows):
        if kind == "group":
            out.append(f'<tr style="background:{CARD};"><td colspan="{len(head)}" style="padding:4px 6px;font-size:10px;font-weight:600;'
                       f'letter-spacing:0.3px;text-transform:uppercase;color:{MUTED};">{cells}</td></tr>')
            continue
        style = f"border-bottom:1px solid {INK if n == last or kind == 'total' else LINE};"
        style += f"color:{MUTED};" if kind == "muted" else "font-weight:600;" if kind == "total" else ""
        tds = []
        for i, c in enumerate(cells):
            txt, ex = c if isinstance(c, tuple) else (c, "")
            al = head[i][1]
            lead = f"padding:{pad}px 0;" if i == 0 else f"padding:{pad}px 0 {pad}px 12px;"
            font = "" if i == 0 else MONO
            tds.append(f'<td style="{lead}text-align:{al};{font}{ex}">{txt}</td>')
        out.append(f'<tr style="{style}">{"".join(tds)}</tr>')
    out.append("</tbody></table>")
    return "".join(out)


def figure(text, legend, svg):
    items = "".join(f'<span style="display:flex;align-items:center;gap:5px;"><span style="{sw}"></span>{name}</span>' for name, sw in legend)
    return (f'<div style="background:{CARD};border-radius:20px;padding:16px 22px 12px;display:flex;flex-direction:column;gap:8px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:16px;"><span style="font-size:12px;font-weight:600;'
            f'letter-spacing:0.36px;text-transform:uppercase;">{text}</span><span style="display:flex;gap:12px;font-size:10px;color:{MUTED};">{items}</span></div>'
            f'{svg}</div>')


def t_(x, y, s, anchor="middle", size=9, fill=MUTED, family="Geist Mono"):
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{family}" font-size="{size}" fill="{fill}">{s}</text>'


def nice_step(span, n=4):
    raw = span / n
    mag = 10 ** __import__("math").floor(__import__("math").log10(raw))
    return next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)


# ---------------------------------------------------------------- 01 — Round 1 results

def nav_chart(perf):
    """Figure 1, in the style of the Round 1 report's Figure 2: plot 40–530 × 10–204, Geist Mono 9 labels."""
    W, X0, X1, Y0, Y1 = 600, 40, 530, 10, 204
    if not perf:
        return f'<svg viewBox="0 0 {W} 230" style="width:100%;height:auto;display:block;overflow:visible;">{t_(285, 110, "[Run scripts/round1_performance.py and promote it]", size=10)}</svg>'
    s = perf["nav_series"]
    vals = [p["index"] for p in s]
    lo, hi = min(vals + [100]), max(vals + [100])
    pad = (hi - lo) * 0.12 or 0.5
    lo, hi = lo - pad, hi + pad
    step = nice_step(hi - lo)
    X = lambda i: X0 + i / max(len(s) - 1, 1) * (X1 - X0)
    Y = lambda v: Y1 - (v - lo) / (hi - lo) * (Y1 - Y0)
    body = ""
    v = (int(lo / step) + 1) * step
    while v < hi:
        body += f'<line x1="{X0}" x2="{X1}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{LINE_B}" stroke-width="0.8"></line>'
        body += t_(32, Y(v) + 3, f"{v:.1f}", "end")
        v += step
    ticks = sorted({0, len(s) - 1, *range(0, len(s), 5)})
    for i in ticks:
        body += t_(X(i), 222, pd.Timestamp(s[i]["date"]).strftime("%d.%m"))
    body += f'<line x1="{X0}" x2="{X1}" y1="{Y(100):.1f}" y2="{Y(100):.1f}" stroke="{REF}" stroke-width="1.4" stroke-dasharray="5 4"></line>'
    pts = " ".join(f"{X(i):.1f},{Y(p['index']):.1f}" for i, p in enumerate(s))
    body += f'<polyline points="{pts}" fill="none" stroke="{INK}" stroke-width="2"></polyline>'
    body += t_(X1 + 6, Y(vals[-1]) + 3, f"Round 1 {vals[-1]:.2f}", "start", 10, INK, "Geist")
    return f'<svg viewBox="0 0 {W} 230" style="width:100%;height:auto;display:block;overflow:visible;">{body}</svg>'


def contribution_chart(perf):
    """Figure 2: contribution of each position to the return, horizontal bars from zero."""
    if not perf:
        return f'<svg viewBox="0 0 600 120" style="width:100%;height:auto;display:block;overflow:visible;">{t_(300, 60, "[No data yet]", size=10)}</svg>'
    rows = sorted([p for p in perf["positions"] if p["shares_start"]], key=lambda p: p["contribution"], reverse=True)
    lim = max(abs(p["contribution"]) for p in rows) * 1.35 or 0.001     # room for the value labels
    X0, X1, top, rh = 70, 560, 6, 19
    X = lambda c: X0 + (c + lim) / (2 * lim) * (X1 - X0)
    H = top + rh * len(rows) + 22
    step = nice_step(2 * lim, 4)
    body = ""
    v = -int(lim / step) * step
    while v <= lim + 1e-12:
        x = X(v)
        body += f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{top + rh * len(rows)}" stroke="{INK if abs(v) < 1e-12 else LINE_B}" stroke-width="0.8"></line>'
        body += t_(x, H - 4, minus(f"{v * 100:+.1f}%" if abs(v) > 1e-12 else "0"))
        v += step
    for i, p in enumerate(rows):
        y = top + i * rh + 4
        x0, x1 = sorted((X(0), X(p["contribution"])))
        body += t_(X0 - 10, y + 9, p["ticker"], "end", 9.5, INK)
        body += f'<rect x="{x0:.1f}" y="{y:.1f}" width="{max(x1 - x0, 0.6):.1f}" height="11" fill="{INK}"></rect>'
        right = p["contribution"] >= 0
        body += t_((x1 + 5) if right else (x0 - 5), y + 9, pct(p["contribution"], 2, True), "start" if right else "end", 9)
    return f'<svg viewBox="0 0 600 {H}" style="width:100%;height:auto;display:block;overflow:visible;">{body}</svg>'


def round1_blocks(perf, r1):
    m = perf["metrics"] if perf else {}
    n = perf["trading_days"] if perf else None
    need = (m.get("min_days_for_stats") or 20) if perf else 20
    stats_ok = perf and m.get("realised_vol") is not None
    period = f'{short(perf["start_date"])}–{short(perf["as_of"])}' if perf else DASH
    held = r1.get("portfolio", {}) if r1 else {}
    b = {}
    b["r1-period"] = (f'<p style="margin:0;font-size:13px;line-height:1.55;">The Round 1 portfolio from the close of Friday 16 October 2026, when it was entered '
                      f'in Bloomberg, to the close of {long_date(perf["as_of"]) if perf else "[date]"}: {n if perf else "[n]"} trading days. '
                      'Prices are closes, and dividends are reinvested in the ETF that pays them at the ex-date close, as in Bloomberg PRTU.</p>')
    b["r1-stats"] = stat_row([
        ("Return", pct(m.get("total_return"), 2, True), f'USD {perf["nav_start"] / 1e6:.1f}M → {perf["nav_end"] / 1e6:.1f}M' if perf else DASH),
        ("Realised volatility", pct(m.get("realised_vol")),
         f"Target 8%, band 7–9%" if stats_ok else f"Needs {need} daily returns · {n if n is not None else DASH} so far"),
        ("Sharpe Ratio", num(m.get("sharpe")), "Excess of the 1-month T-bill" if stats_ok else f"Needs {need} daily returns"),
        ("Maximum drawdown", pct(m.get("max_drawdown"), 2),
         f'{short(m["max_drawdown_from"])} → {short(m["max_drawdown_to"])}' if perf else DASH)])
    b["r1-figure"] = figure("Figure 1 · NAV of the fund, index 16 October = 100",
                            [("Round 1 portfolio", f"width:14px;height:2px;background:{INK};"), ("Start", f"width:14px;border-top:2px dashed {REF};")],
                            nav_chart(perf))
    rows = [(["Period", period, f"Ex ante, {short(perf['start_date'])}" if perf else DASH], ""),
            (["Trading days", str(n) if perf else DASH, DASH], ""),
            (["Return, cumulative", pct(m.get("total_return"), 2, True), DASH], ""),
            (["Volatility, realised, annualised", pct(m.get("realised_vol")), "Target 8% · band 7–9%"], ""),
            (["Ex-ante volatility", pct(m.get("ex_ante_vol")), held.get("ex_ante_vol", DASH)], ""),
            (["Sharpe Ratio", num(m.get("sharpe")), DASH], ""),
            (["Maximum drawdown", pct(m.get("max_drawdown"), 2), DASH], ""),
            (["1-month 5% VaR", f'{pct(m.get("var_1m_95_pct"))} · {usd(m.get("var_1m_95_usd"))}',
              f'{held.get("var_1m", DASH)} · USD {held.get("var_usd", DASH)}'], "")]
    rows = [([(c[0], SANS), c[1], c[2]], k) for c, k in rows]
    b["r1-table"] = (title("Table 1 · Performance and risk of the Round 1 portfolio")
                     + table([("", "left"), ("Round 1 portfolio", "right"), ("At the start · Round 1 report", "right")], rows))
    draft = "" if perf and perf["as_of"] == FINAL_DATE else (" Draft: the final figures use the close of Friday 6 November." if perf else "")
    window = f'{pd.Timestamp(m["risk_model_window"][0]):%b %Y} – {pd.Timestamp(m["risk_model_window"][1]):%b %Y}' if perf else DASH
    b["r1-note"] = caption(f"Realised volatility and the Sharpe Ratio (on returns in excess of the 1-month T-bill) are computed from daily returns "
                           f"once there are {need}, the rule of our website; with {n if perf else DASH} so far they are not reported. "
                           f"Ex-ante volatility = √(w′Vw) on the current weights and the last 60 complete months ({window}); "
                           f"VaR = 1.645 × σ / √12, as in Round 1.{draft}")

    # --- page 2 of the section: positions and attribution
    head = [("ETF", "left"), ("Shares", "right"), (f"Price {short(perf['start_date'])[:5]}" if perf else "Price, start", "right"),
            (f"Price {short(perf['as_of'])[:5]}" if perf else "Price, now", "right"), ("Weight, start", "right"), ("Weight, now", "right"),
            ("Return", "right"), ("Contribution", "right"), ("Risk contr.", "right")]
    rows = []
    if perf:
        classes = {c["name"]: c for c in perf["asset_classes"]}
        for cls in dict.fromkeys(p["asset_class"] for p in perf["positions"]):
            ps = [p for p in perf["positions"] if p["asset_class"] == cls]
            c = classes[cls]
            if not any(p["shares_start"] for p in ps):
                for p in ps:
                    rows.append(([(p["ticker"], f"{MONO}font-weight:600;"), "0", num(p["price_start"]), num(p["price_now"]), pct(0), pct(0), DASH, pct(0),
                                  pct(0, 1)], "muted"))
                continue
            rows.append((f'{esc(cls)} · {pct(c["weight_start"])} → {pct(c["weight_now"])} of the NAV · contribution {pct(c["contribution"], 2, True)}', "group"))
            for p in ps:
                rows.append(([(p["ticker"], f"{MONO}font-weight:600;"), f'{p["shares_now"]:,.0f}' if p["shares_now"] == int(p["shares_now"]) else f'{p["shares_now"]:,.2f}',
                              num(p["price_start"]), num(p["price_now"]), pct(p["weight_start"]), pct(p["weight_now"]), pct(p["return"], 2, True),
                              pct(p["contribution"], 2, True), pct(p["risk_contribution"], 1)], ""))
        cash_w = perf["cash"] / perf["nav_end"]
        rows.append(([f'Cash ({usd(perf["cash"], 2)})', "", "", "", pct(perf["cash"] / perf["nav_start"]), pct(cash_w), DASH, pct(0), pct(0, 1)], "muted"))
        rows.append((["Total", "", "", "", pct(1), pct(1), pct(m["total_return"], 2, True), pct(m["total_return"], 2, True),
                      pct(sum(p["risk_contribution"] for p in perf["positions"]), 1)], "total"))
    else:
        rows = [(["[No data yet]"] + [DASH] * 8, "")]
    rows = [([(c[0][0], SANS + c[0][1]) if isinstance(c[0], tuple) else (c[0], SANS)] + c[1:], k) if k != "group" else (c, k) for c, k in rows]
    b["r1-positions"] = (title("Table 2 · Positions and contribution to the return")
                         + table(head, rows, size=11.5))
    b["r1-contribution"] = figure("Figure 2 · Contribution to the return, by position", [], contribution_chart(perf))
    b["r1-positions-note"] = caption("Return of each position with dividends reinvested. Contribution = change in the value of the position / NAV at the start: "
                                     "the contributions add up to the return of the portfolio. Risk contribution: share of the ex-ante variance, current weights. "
                                     f"BIL, the cash leg, holds no shares (Round 1, section 09).{draft}")
    nav_m = f'USD {perf["nav_end"] / 1e6:.1f}M' if perf else DASH
    b["cover-nav"] = (f'<span style="font-size:11px;font-weight:600;letter-spacing:0.33px;text-transform:uppercase;color:{MUTED};">'
                      f'NAV · {short(perf["as_of"]) if perf else "[date]"}</span><span style="{MONO}font-size:28px;font-weight:600;">{nav_m}</span>')
    return b


# ---------------------------------------------------------------- 02 — the stocks

def sections(doc):
    return re.findall(r'<section class="page"[\s\S]*?</section>', doc)


def stock_blocks(order, first_page, total):
    pages = []
    for slot in range(1, SLOTS + 1):
        t = order[slot - 1] if slot <= len(order) else None
        f = FIGURES / f"round2-{t}.dc.html" if t else None
        if f is not None and f.exists():
            secs = sections(f.read_text(encoding="utf-8"))
            if len(secs) != 2:
                raise SystemExit(f"{f.name}: {len(secs)} pages, expected 2")
        else:
            secs = sections(bsr.placeholder_pages(slot, first_page + 2 * (slot - 1), total))
        pages += [s.replace('<section class="page"', f'<section class="page" data-stock="{t or f"slot {slot}"}"', 1) for s in secs]
    return {"stocks": "\n\n".join(pages)}


# ---------------------------------------------------------------- 03 — Treynor-Black, 04 — portfolio description

def portfolio_blocks(pf, perf):
    s = pf["sleeve"] if pf else None                      # w_A: the share of the portfolio in the stocks
    sl = "% of A"
    k = pf["risk"] if pf else {}
    a = pf["active"] if pf else {}
    te_t = f"{pf['te_target'] * 100:g}%" if pf and pf.get("te_target") else DASH   # 4% or 2.5%
    star = f"w<sub>A</sub>* {pct(a.get('w_A_star'), 1)}"
    bound = {"treynor_black": f"Treynor-Black {star}", "te_target": f"{star}, capped at TE {te_t}",
             "te_floor": f"{star}, raised to TE 2%"}.get(a.get("bound"), "Treynor-Black and the TE budget")
    b = {}
    b["tb-stats"] = stat_row([
        ("In the stocks", pct(s, 1), bound),
        ("Ex-ante TE vs SAA", pct(k.get("te")), "Budget 2–5%"),
        ("Ex-ante volatility", pct(k.get("vol_new")), f'SAA {pct(k.get("vol_saa"))}'),
        ("1-month 5% VaR", pct(k.get("var_new")), f'SAA {pct(k.get("var_saa"))}')])

    greek = lambda t: f'<span style="text-transform:none;">{t}</span>'          # uppercase would turn α into A
    head = [("Stock", "left", "width:25%;"), (greek("α") + ", annual", "right"), (greek("σ²(ε)"), "right"), (greek("α / σ²(ε)"), "right"),
            ("IR", "right"), (f"Raw, {sl}", "right"), (f"Entered, {sl}", "right"), ("Entered, % of the portfolio", "right")]
    rows = []
    stocks = pf["stocks"] if pf else []
    for i in range(SLOTS):
        x = stocks[i] if i < len(stocks) else None
        if x:
            raw = x.get("weight_sleeve_raw", x["weight_sleeve_tb"])
            flag = (' <span style="font-weight:600;">· set to 0</span>' if x.get("set_to_zero")
                    else ' <span style="font-weight:600;">· negative: flagged</span>' if x["negative"] else "")
            rows.append(([(f'<span style="{MONO}font-weight:600;">{x["ticker"]}</span> {esc(x["name"])}{flag}', SANS), pct(x["alpha"], 1, True),
                          num(x["sigma2_eps"], 4), num(x["score"]), num(x["ir"]), (pct(raw), "font-weight:600;" if x["negative"] else ""),
                          pct(x["weight_sleeve_tb"]), pct(x["weight_sleeve_tb"] * s)], ""))
        else:
            rows.append(([(f'[Stock {i + 1}]', SANS)] + [DASH] * 7, "muted"))
    rows.append(([("Active portfolio A, total", SANS), DASH, DASH, DASH, DASH, pct(1) if pf else DASH, pct(1) if pf else DASH, pct(s)], "total"))
    rows.append(([("Active portfolio A", SANS), pct(a.get("alpha_A"), 1, True), num(a["sigma_eps_A"] ** 2, 4) if a else DASH, DASH,
                  num(a.get("ir_A")), DASH, DASH, DASH], ""))
    zeroed = [x["ticker"] for x in stocks if x.get("set_to_zero")]
    rule = (f"{', '.join(zeroed)}: negative raw weight, entered as 0 by the course rule (Checkpoint 1: weight 0 for a negative alpha, long-only); "
            "the positive weights are rescaled to fill A, and A uses the entered weights. " if zeroed else "A negative weight is shown and flagged, never dropped or rescaled. ")
    size = (f"Size of A: Treynor-Black w<sub>A</sub>* = {pct(a.get('w_A_star'), 1)} (eqs. 11–12). The SAA is the benchmark: "
            f"TE = w<sub>A</sub> × {pct(a.get('te_per_unit'))} (the TE of A against the SAA), so the 2% floor and our {te_t} target allow "
            f"w<sub>A</sub> from {pct(a.get('w_A_lo'))} to {pct(a.get('w_A_hi'))}; w<sub>A</sub> = {pct(s)}. " if a.get("w_A_hi") is not None
            else f"Treynor-Black optimal size w<sub>A</sub>* = {pct(a.get('w_A_star'), 1)}, kept inside the TE budget. ")
    b["tb-table"] = (title("Table 3 · Treynor-Black: the stocks inside the active portfolio A" + (f", {pct(s, 1)} of the portfolio" if pf else ""))
                     + table(head, rows, size=11.5, pad=4)
                     + caption("Weights inside A ∝ α / σ²(ε) (Class 3 Part II): weight in the portfolio = weight in A × w<sub>A</sub>. "
                               + rule + size +
                               f"Sharpe Ratio of the SAA {num(a.get('sharpe_saa'))}, {num(a.get('sharpe_at_w_A'))} at w<sub>A</sub> "
                               f"({num(a.get('sharpe_with_active'))} at w<sub>A</sub>*, eq. 16)."))

    head = [("Security", "left"), ("Bloomberg ticker", "left"), ("Ccy", "left"), ("Shares", "right"), ("Trade", "right"), ("Price", "right"), ("Weight", "right")]
    rows = []
    etfs = pf["etfs"] if pf else [{"name": p["name"], "bloomberg": f'{p["ticker"]} US Equity', "currency": "USD", "ticker": p["ticker"]}
                                  for p in (perf["positions"] if perf else []) if p["shares_now"]]   # BIL: not held
    sign = lambda v: minus(f"{v:+,.0f}") if v else "0"
    for e in etfs:
        if pf and not e["shares_after"] and not e["shares_before"]:
            continue                                                # BIL: not held before or after
        rows.append(([e["name"], (e["bloomberg"], MONO), "USD", f'{e["shares_after"]:,.0f}' if pf else DASH, sign(e["trade"]) if pf else DASH,
                      num(e["price"]) if pf else DASH, pct(e["weight"]) if pf else DASH], ""))
    for i in range(SLOTS):
        x = stocks[i] if i < len(stocks) else None
        if x:
            name = esc(x["name"]) + (" · not bought: negative alpha" if x.get("set_to_zero") else "")
            rows.append(([name, (x["bloomberg"], MONO), x["currency"], f'{x["shares"]:,.0f}', sign(x["shares"]), num(x["price"]),
                          pct(x["weight_total"])], "muted" if not x["shares"] else ""))
        else:
            rows.append(([f"[Stock {i + 1}]", (f"[TICKER] US Equity", MONO), "USD"] + [DASH] * 4, "muted"))
    rows.append(([f'Cash, rounding leftover ({usd(pf["cash"]["usd"], 2)})' if pf else "Cash, rounding leftover", "", "USD", "", "", "",
                  pct(pf["cash"]["weight"]) if pf else DASH], "muted"))
    rows.append(([f'Total ({usd(pf["nav"])})' if pf else "Total", "", "USD", "", "", "", pct(pf["total"]["weight"]) if pf else DASH], "total"))
    rows = [([(c[0], SANS)] + c[1:], kd) for c, kd in rows]
    b["portfolio-table"] = title("Table 4 · Portfolio description, as entered in Bloomberg PRTU") + table(head, rows, size=11, pad=4)
    if pf:
        b["portfolio-note"] = caption(f"Price date: close of {long_date(pf['as_of'])} for every position. Every ETF goes to (1 − w<sub>A</sub>) = "
                                      f"{pct(1 - s, 2)} of its SAA weight, so the SAA mix does not change; each stock to w<sub>A</sub> × its weight in A. "
                                      f"Whole shares, rounded down; the rest is cash. The weights add up to {pct(pf['total']['weight'])}. "
                                      f"Ex-ante TE, volatility and VaR on the last {k['months']} complete months ({k['window'][0]} – {k['window'][1]}).")
    else:
        b["portfolio-note"] = caption("Price date: close of Friday 6 November 2026. Every ETF goes to (1 − w<sub>A</sub>) of its SAA weight. Whole shares, rounded down; the rest is cash. "
                                      "Filled by scripts/build_round2_portfolio.py once the stocks are chosen.")
    return b


# ---------------------------------------------------------------- assemble

def replace_block(doc, name, content):
    pat = re.compile(rf"(<!-- auto:{re.escape(name)} -->)[\s\S]*?(<!-- /auto:{re.escape(name)} -->)")
    if not pat.search(doc):
        raise SystemExit(f"{SOURCE.name}: no <!-- auto:{name} --> block")
    return pat.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(2)}", doc, count=1)


def renumber(doc):
    secs = sections(doc)
    total = len(secs)
    foot = re.compile(rf"(<span style=\"{re.escape(MONO)}\">)\d{{2}} / \d{{2}}(</span>)")
    out, pos = [], 0
    for i, s in enumerate(secs, 1):
        start = doc.index(s, pos)
        out.append(doc[pos:start])
        hits = list(foot.finditer(s))
        if hits:
            h = hits[-1]
            s = s[:h.start()] + f"{h.group(1)}{i:02d} / {total:02d}{h.group(2)}" + s[h.end():]
        out.append(s)
        pos = start + len(secs[i - 1])
    out.append(doc[pos:])
    return "".join(out), total


def load(name):
    p = FIGURES / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def assemble():
    doc = SOURCE.read_text(encoding="utf-8")
    perf, r1, pf = load("round2-round1_performance.json"), load("round1-report_figures.json"), load("round2-portfolio.json")
    if pf and pf.get("status") != "ok":
        raise SystemExit("report/figures/round2-portfolio.json is a stopped run: fix it and promote a clean one\n  " + "\n  ".join(pf.get("problems", [])))
    if pf and perf and pf["as_of"] != perf["as_of"]:
        raise SystemExit(f"The portfolio is for {pf['as_of']} but the Round 1 results are for {perf['as_of']}: promote both from the same run")
    if pf:
        order = [x["ticker"] for x in pf["stocks"]]
    else:
        order = sorted(p.name[len("round2-"):-len(".dc.html")] for p in FIGURES.glob("round2-*.dc.html"))
    if len(order) > SLOTS:
        raise SystemExit(f"{len(order)} stocks promoted, the report has {SLOTS} slots")
    first_stock = len(sections(doc[:doc.index("<!-- auto:stocks -->")])) + 1      # page numbers are rewritten below anyway
    blocks = {**round1_blocks(perf, r1), **stock_blocks(order, first_stock, 0), **portfolio_blocks(pf, perf)}
    for name, content in blocks.items():
        doc = replace_block(doc, name, content)
    doc, total = renumber(doc)
    SOURCE.write_text(doc, encoding="utf-8", newline="\n")
    print(f"{SOURCE.relative_to(REPO)}: {total} pages; Round 1 data {perf['as_of'] if perf else 'missing'}; "
          f"stocks {', '.join(order) or 'none (6 empty slots)'}; portfolio {'from ' + pf['as_of'] if pf else 'placeholders'}")
    return total


def chrome():
    for c in (os.environ.get("CHROME"), r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chrome")):
        if c and Path(c).exists():
            return c
    raise SystemExit("Google Chrome not found: set CHROME to its path")


def export():
    exe = chrome()
    flags = ["--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=30000"]
    dom = subprocess.run([exe, *flags, "--dump-dom", SOURCE.as_uri()], capture_output=True, text=True, encoding="utf-8", timeout=180).stdout
    found = re.search(r'data-overflow="([^"]*)"', dom)
    layout = json.loads(html.unescape(found.group(1))) if found else None
    PDF.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([exe, *flags, f"--print-to-pdf={PDF}", SOURCE.as_uri()], capture_output=True, timeout=180)
    if not PDF.exists():
        raise SystemExit("PDF export failed")
    print(f"wrote {PDF.relative_to(REPO)}")
    if layout is None:
        print("WARNING: could not measure the layout; check every page by eye")
        return
    clipped = [p for p in layout if p["overflow"] > 0]
    for p in layout:
        print(f"  {p['label']}: free {p['free']}px" + (f", OVERFLOW {p['overflow']}px" if p["overflow"] else ""))
    if clipped:
        raise SystemExit("Too long: " + "; ".join(f"{p['label']} runs {p['overflow']}px past the bottom" for p in clipped))


def main():
    ap = argparse.ArgumentParser(description="Assemble the Round 2 report from report/figures/ and export it.")
    ap.add_argument("--pdf", action="store_true", help="Also export report/pdf/Matterhorn_Round2_Equity.pdf and check every page for overflow")
    args = ap.parse_args()
    assemble()
    if args.pdf:
        export()


if __name__ == "__main__":
    main()
