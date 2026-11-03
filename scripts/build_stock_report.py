#!/usr/bin/env python3
"""Build the two-page Round 2 stock report (valuation dossier) for one stock.

    python3 scripts/build_stock_report.py <TICKER>                      latest close
    python3 scripts/build_stock_report.py <TICKER> --as-of 2026-11-06   final numbers
    python3 scripts/build_stock_report.py --selftest               checks against the TA's numbers

One run = one as-of date: everything goes to runs/round2/<as-of>/, next to the inputs it used.
Reads   runs/round2/inputs/<TICKER>.yaml           peers, growth inputs, thesis, catalysts
Saves   runs/round2/<as-of>/<TICKER>_data.json     the download, so the report can be reproduced
Writes  runs/round2/<as-of>/<TICKER>.yaml          a copy of the inputs this run used
        runs/round2/<as-of>/<TICKER>.dc.html       the two A4 pages
        runs/round2/<as-of>/<TICKER>.pdf           the export (Chrome, headless)
        runs/round2/<as-of>/<TICKER>_figures.json  every computed number and the flags
Promote the final ones into report/ with scripts/promote.py.

The formulas follow the TA's 02_round2_lecture.ipynb and the Round 2 cheat sheet. Differences:
  * Beta and residual risk use our own SAA (data/holdings.json) and complete months only.
  * Alpha allows a probability: alpha = p * alpha_closed + (1 - p) * alpha_never.
    p = 1 is the TA's alpha closed, p = 0 is the TA's alpha never.
  * The earnings test compares forward EPS with last year's adjusted EPS, so a one-off
    write-down cannot fake a rise (the cheat sheet's "careful" on GIS).

Fair value is the DDM value. The comparables are a double check and do not feed it; only a stock
with no dividend, where the DDM does not apply, falls back on them.

An existing snapshot for the date is reused, unless --refresh is given or the peers changed.
"""

import argparse
import html
import json
import math
import re
import subprocess
import sys
import tempfile
import time
import warnings
from datetime import datetime
from pathlib import Path
from string import Template
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yaml

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "runs" / "round2"             # one folder per as-of date
INPUTS, TA = RUNS / "inputs", REPO / "course" / "ta-code"
SHELL = REPO / "report" / "templates" / "stock-report.dc.html"
HOLDINGS = REPO / "data" / "holdings.json"
RUNTIME = "../../../report/runtime"         # support.js and doc-page.js, relative to runs/round2/<as-of>/
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="

WINDOW = 60                                 # months, as in Round 1
ERP_DEFAULT = 0.06114                       # Bloomberg CRP, Class 5; the notebook says to recompute it
ENTRY_DATE = pd.Timestamp("2026-11-06")     # prices of the new positions
CHALLENGE_END = pd.Timestamp("2026-12-27")  # General guidelines: the challenge ends on 27 December
IR_BUFFETT = 0.64                           # cheat sheet §9, credibility benchmark
HISTORY_YEARS = 7                           # price history downloaded for the 60-month window

INK, MUTED, CARD, LINE, LINE_B = "#111111", "#615e5b", "#f3efeb", "#e9eaeb", "#d8d3cc"
REF, RANGE, RANGE_HI = "#888888", "#cfc8be", "#a39c92"
MONO = "font-family:'Geist Mono',monospace;"
SUB = '<sub style="font-size:72%;line-height:0;">{}</sub>'
P_0, D_0, D_1, V_0, G_1, G_2, R_F = ("P" + SUB.format(0), "D" + SUB.format(0), "D" + SUB.format(1), "V" + SUB.format(0),
                                     "g" + SUB.format(1), "g" + SUB.format(2), "r" + SUB.format("f"))
LOGO = "M2.94 25.24A16 16 0 1 1 29.06 25.24L16 12.18ZM16 12.18V32A16 16 0 0 0 26.54 28.04Z"

INFO_KEYS = ["longName", "shortName", "sector", "industry", "currency", "financialCurrency", "fullExchangeName",
             "marketCap", "enterpriseValue", "currentPrice", "fiftyTwoWeekLow", "fiftyTwoWeekHigh",
             "sharesOutstanding", "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months",
             "enterpriseToEbitda", "enterpriseToRevenue", "forwardEps", "trailingEps", "bookValue", "ebitda",
             "totalRevenue", "dividendRate", "dividendYield", "targetMeanPrice", "targetLowPrice", "targetHighPrice",
             "numberOfAnalystOpinions"]
STATEMENT_ITEMS = ["Total Revenue", "Gross Profit", "Net Income", "Diluted EPS", "Diluted Average Shares", "EBITDA",
                   "Stockholders Equity", "Total Assets", "Total Debt", "Free Cash Flow",
                   "Cash Dividends Paid", "Repurchase Of Capital Stock"]

# id, column title, kind for the sanity filter
MULTIPLES = [("forward_pe", "Fwd P/E", "earnings"), ("trailing_pe", "Trail. P/E", "earnings"),
             ("p_fcf", "P/FCF", "earnings"), ("ev_ebitda", "EV/EBITDA", "earnings"), ("pb", "P/B", "positive"),
             ("ps", "P/S", "positive"), ("ev_sales", "EV/Sales", "positive"), ("yield", "Div. yield", "yield")]
SHOWN = ("forward_pe", "p_fcf", "ev_ebitda")   # the multiples printed in the report; the others stay in figures.json

# metric, characteristic of Class 5, higher is better, percent format
TRAP_METRICS = [("ROE", "Profitability", True, True), ("ROA", "Profitability", True, True),
                ("FCF margin", "Profitability", True, True), ("revenue growth", "Growth", True, True),
                ("gross margin", "Growth", True, True), ("debt / equity", "Safety", False, False),
                ("payout / FCF", "Payout", False, False)]


# ---------------------------------------------------------------- formulas (cheat sheet §3-§9)

def gordon(D0, k, g):
    """V0 = D0 (1 + g) / (k - g), requires k > g."""
    return D0 * (1 + g) / (k - g)


def two_stage(D0, k, g1, g2, T):
    """V0 = sum of the discounted dividends of years 1..T + discounted Gordon terminal value at T."""
    t = np.arange(1, int(T) + 1)
    D = D0 * (1 + g1) ** t
    TV = D[-1] * (1 + g2) / (k - g2)
    return float((D / (1 + k) ** t).sum() + TV / (1 + k) ** T)


def pv_terminal(D0, k, g1, g2, T):
    return D0 * (1 + g1) ** T * (1 + g2) / (k - g2) / (1 + k) ** T


def alpha_closed(V0, P0, k):
    """Annual alpha if the price reaches the value within one year."""
    return (1 + k) * (V0 - P0) / P0


def alpha_never(D0, P0, g, k):
    """Annual alpha if the gap never closes: D1 / P0 + g - k."""
    return D0 * (1 + g) / P0 + g - k


def implied_growth(P0, D0, k):
    """Reverse Gordon: the constant growth the price implies."""
    return (k * P0 - D0) / (P0 + D0)


def regress_on_saa(r_i, r_s):
    """R_i^e = a + beta R_S^e + eps. Returns beta and the annualised residual variance (§6)."""
    beta, a = np.polyfit(r_s, r_i, 1)
    eps = r_i - (a + beta * r_s)
    return float(beta), float(eps.var() * 12)


def metrics(f):
    """The TA's 6 metrics plus ROA, one row per fiscal year, from one firm's statements."""
    f = f.reindex(columns=STATEMENT_ITEMS).dropna(subset=["Total Revenue"]).sort_index()
    eq = f["Stockholders Equity"].where(f["Stockholders Equity"] > 0)   # negative equity: ROE and D/E are meaningless
    rev = f["Total Revenue"]
    payout = -(f["Cash Dividends Paid"].fillna(0) + f["Repurchase Of Capital Stock"].fillna(0))
    return pd.DataFrame({
        "ROE": f["Net Income"] / eq,
        "ROA": f["Net Income"] / f["Total Assets"],
        "FCF margin": f["Free Cash Flow"] / rev,
        "revenue growth": rev / rev.shift(1) - 1,
        "gross margin": f["Gross Profit"] / rev,
        "debt / equity": f["Total Debt"] / eq,
        "payout / FCF": payout / f["Free Cash Flow"],
    })


def trap_table(m, peers):
    """Level vs the peer median and trend vs the stock's own past average, last fiscal year (Checkpoint 2)."""
    vt = pd.DataFrame({"value": m.iloc[-1], "peer": pd.concat([p.iloc[-1] for p in peers], axis=1).median(axis=1),
                       "own": m.iloc[:-1].mean()})
    high = pd.Series({name: hb for name, _, hb, _ in TRAP_METRICS})
    better = lambda a, b: ((a > b) == high).where(a.notna() & b.notna())
    vt["better_than_peers"] = better(vt["value"], vt["peer"])
    vt["improving"] = better(vt["value"], vt["own"])
    vt["red_flag"] = (vt["better_than_peers"] == False) & (vt["improving"] == False)   # noqa: E712
    return vt.loc[[name for name, *_ in TRAP_METRICS]]


def trap_verdict(red_flags, earnings_falling):
    """Red flags plus falling earnings: value trap. Either one alone: watch."""
    if red_flags and earnings_falling:
        return "Fail"
    return "Watch" if red_flags or earnings_falling else "Pass"


# ---------------------------------------------------------------- data

def to_records(df):
    """DataFrame indexed by date to JSON-safe {column: {date: value}}."""
    out = {}
    for c in df.columns:
        s = df[c].dropna()
        out[str(c)] = {d.strftime("%Y-%m-%d"): float(v) for d, v in s.items()}
    return out


def frame(records):
    df = pd.DataFrame({c: pd.Series(v, dtype=float) for c, v in records.items()})
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def retry(fn, what, tries=3):
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:                 # network / Yahoo hiccup: retry, then fail
            err = e
            time.sleep(2 * (attempt + 1))
    raise SystemExit(f"Download failed for {what}: {err}")


def saa_weights():
    """Our SAA: the target weights of Round 1, without the unused cash leg."""
    h = json.loads(HOLDINGS.read_text())["rounds"][0]["holdings"]
    return pd.Series({x["ticker"]: x["target_weight"] for x in h if x["target_weight"] > 0})


def fred_series(sid):
    try:
        s = pd.read_csv(FRED + sid, index_col=0, parse_dates=True, na_values=".").iloc[:, 0].dropna()
        return s.loc["2016":].rename(sid)
    except Exception as e:                     # FRED is down: the TA's copy is good enough for history
        print(f"WARNING: FRED {sid} unavailable ({e}); using course/ta-code/r2_rates.csv")
        return pd.read_csv(TA / "r2_rates.csv", index_col=0, parse_dates=True)[sid].dropna()


def statements_of(tk):
    st = pd.concat([tk.income_stmt, tk.balance_sheet, tk.cashflow])
    st = st[~st.index.duplicated()].T.sort_index()
    st.index = pd.to_datetime(st.index)
    return st.reindex(columns=STATEMENT_ITEMS).dropna(subset=["Total Revenue"])


def download(cfg, as_of_arg):
    import yfinance as yf
    yf.set_tz_cache_location(str(Path(tempfile.gettempdir()) / "matterhorn-yfinance"))   # not in the repo
    t, peers = cfg["ticker"], list(cfg["peers"])
    print(f"Downloading {t} and {len(peers)} peers ...")

    start = (pd.Timestamp.today() - pd.DateOffset(years=HISTORY_YEARS)).strftime("%Y-%m-%d")
    universe = sorted({t, "SPY", *saa_weights().index})

    def prices(adjusted):      # yf.download reports a failed ticker as an empty column, not an error
        px = yf.download(universe, start=start, auto_adjust=adjusted, progress=False)["Close"]
        empty = [c for c in universe if c not in px or px[c].dropna().empty]
        if empty:
            raise ValueError("no prices for " + ", ".join(empty))
        return px

    adj = retry(lambda: prices(True), "adjusted prices")
    close = retry(lambda: prices(False), "closes")

    now = datetime.now(ZoneInfo("America/New_York"))       # before the close, today's bar is an intraday price
    if close.index[-1].date() == now.date() and (now.hour, now.minute) < (16, 15):
        adj, close = adj.iloc[:-1], close.iloc[:-1]
    as_of = pd.Timestamp(as_of_arg) if as_of_arg else close[t].dropna().index[-1]
    if close[t].loc[:as_of].empty:
        raise SystemExit(f"No close for {t} on or before {as_of.date()}")
    as_of = close[t].loc[:as_of].dropna().index[-1]

    tk = yf.Ticker(t)
    divs = retry(lambda: tk.dividends, "dividends")
    divs.index = divs.index.tz_localize(None).normalize()
    estimate = retry(lambda: tk.earnings_estimate, "estimates")
    cal = retry(lambda: tk.calendar, "calendar") or {}
    dates = cal.get("Earnings Date") or []

    infos, statements = {}, {}
    for s in [t] + peers:
        tks = yf.Ticker(s)
        i = retry(lambda: tks.info, f"{s} info")
        if not i.get("marketCap"):
            raise SystemExit(f"Yahoo has no market data for peer {s}: check the ticker in the YAML")
        infos[s] = {k: i.get(k) for k in INFO_KEYS}
        statements[s] = to_records(retry(lambda: statements_of(tks), f"{s} statements"))

    snap = {
        "ticker": t, "peers": peers, "as_of": as_of.strftime("%Y-%m-%d"),
        "downloaded_at": datetime.now(ZoneInfo("Europe/Zurich")).isoformat(timespec="minutes"),
        "info": infos, "statements": statements,
        "dividends": {d.strftime("%Y-%m-%d"): float(v) for d, v in divs.items()},
        "estimates": {"eps_ago": float(estimate.loc["0y", "yearAgoEps"]), "eps_cur": float(estimate.loc["0y", "avg"]),
                      "eps_next": float(estimate.loc["+1y", "avg"]), "growth_next": float(estimate.loc["+1y", "growth"])},
        "next_earnings": str(dates[0]) if dates else None,
        "latest_close": close[t].dropna().index[-1].strftime("%Y-%m-%d"),
        "adj": to_records(adj), "close": to_records(close[[t]]),
        "rates": to_records(pd.concat([fred_series("DGS1MO"), fred_series("DGS10")], axis=1)),
    }
    path = RUNS / snap["as_of"] / f"{t}_data.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, indent=1))
    print(f"Saved {path.name}")
    return snap


def load_or_download(cfg, as_of_arg, refresh):
    if as_of_arg and not refresh:
        path = RUNS / as_of_arg / f"{cfg['ticker']}_data.json"
        if path.exists():
            snap = json.loads(path.read_text())
            if sorted(snap["peers"]) == sorted(cfg["peers"]):
                print(f"Using saved data {path.name} (downloaded {snap['downloaded_at']})")
                return snap
    return download(cfg, as_of_arg)


# ---------------------------------------------------------------- analysis

def complete_month_end(as_of):
    """The last month-end whose month has finished: month-ends up to here are complete."""
    next_day = as_of + pd.offsets.BDay(1)
    return next_day.to_period("M").start_time - pd.Timedelta(days=1)


def sane(value, kind):
    """A multiple we can use, or None. Negative or absurd multiples are not meaningful."""
    if value is None or not np.isfinite(value):
        return None
    if kind == "earnings" and not 0 < value <= 100:
        return None
    if kind == "positive" and value <= 0:
        return None
    if kind == "yield" and value <= 0:
        return None
    return float(value)


def stats_of(values):
    v = np.array([x for x in values if x is not None], dtype=float)
    if len(v) == 0:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None, "q1": None, "q3": None}
    q1, q3 = np.percentile(v, [25, 75])
    return {"n": len(v), "mean": float(v.mean()), "median": float(np.median(v)), "min": float(v.min()),
            "max": float(v.max()), "q1": float(q1), "q3": float(q3)}


def last_fcf(statements):
    """Free cash flow (operating cash flow - capex) of the latest fiscal year, or None."""
    fcf = statements.get("Free Cash Flow") or {}
    return fcf[max(fcf)] if fcf else None


def peer_multiples(i, fcf):
    price, rate, cap = i.get("currentPrice"), i.get("dividendRate"), i.get("marketCap")
    y = rate / price * 100 if rate and price else None
    return {"forward_pe": i.get("forwardPE"), "trailing_pe": i.get("trailingPE"), "p_fcf": cap / fcf if cap and fcf else None,
            "ev_ebitda": i.get("enterpriseToEbitda"),
            "pb": i.get("priceToBook"), "ps": i.get("priceToSalesTrailing12Months"), "ev_sales": i.get("enterpriseToRevenue"),
            "yield": y}


def short_name(s):
    s = re.sub(r"\b(Incorporated|Inc\.?|Corporation|Corp\.?|Limited|Ltd\.?|PLC|plc|N\.V\.|S\.A\.|AG)(?=\W|$)", "", s or "")
    s = re.sub(r"&?\s*\b(Company|Co\.)(?=\W|$)", "", s)
    s = re.sub(r"^The\s+", "", s)
    return s.strip(" ,.&")


def monthly_excess_returns(snap, t):
    """Returns on complete months, as in Round 1: the stock, SPY and the SAA ETFs, in excess of the
    1-month T-bill, last WINDOW months. Also the daily rates (decimal). The Round 2 portfolio uses it too."""
    as_of = pd.Timestamp(snap["as_of"])
    adj = frame(snap["adj"]).loc[:as_of].ffill()
    R = adj.resample("ME").last().pct_change()
    R = R.loc[:complete_month_end(as_of)]
    rates = frame(snap["rates"]).loc[:as_of] / 100
    rf_m = (rates["DGS1MO"].ffill() / 12).resample("ME").mean().reindex(R.index).ffill()   # averaged by month, as in Round 1
    Re = R.sub(rf_m, axis=0)
    est = Re.dropna(subset=[t, "SPY", *saa_weights().index]).iloc[-WINDOW:]
    return est, rates


def analyse(cfg, snap):
    t = cfg["ticker"]
    v = cfg.get("valuation") or {}
    a = cfg.get("alpha") or {}
    over = v.get("overrides") or {}
    info = snap["info"][t]
    as_of = pd.Timestamp(snap["as_of"])
    flags = []     # (text, also printed in the report)

    def given(name, default, source):
        """An input, unless the YAML overrides it (e.g. with a Bloomberg figure)."""
        if name in over:
            return float(over[name]["value"]), over[name].get("source", "Override")
        return default, source

    est, rates = monthly_excess_returns(snap, t)
    W = saa_weights()
    if len(est) < WINDOW:
        flags.append((f"Only {len(est)} months of returns, not {WINDOW}", True))
    R_S = est[list(W.index)] @ W
    mu_S, sigma_S = R_S.mean() * 12, R_S.std() * math.sqrt(12)

    # --- inputs of the DDM (§3)
    close = frame(snap["close"])[t].dropna()
    P0, src_p = given("P0", float(close.iloc[-1]), f"Close {as_of:%d.%m.%y}, not adjusted")
    divs = pd.Series(snap["dividends"], dtype=float)
    divs.index = pd.to_datetime(divs.index)
    ttm = float(divs.loc[(divs.index > as_of - pd.Timedelta(days=365)) & (divs.index <= as_of)].sum())

    f = frame({k: {d: x for d, x in s.items()} for k, s in snap["statements"][t].items()}).reindex(columns=STATEMENT_ITEMS)
    last = f.iloc[-1]
    div_cash = -float(np.nan_to_num(last["Cash Dividends Paid"]))
    buy_cash = -float(np.nan_to_num(last["Repurchase Of Capital Stock"]))
    shares_fy = float(last["Diluted Average Shares"]) if np.isfinite(last["Diluted Average Shares"]) else None
    basis = v.get("dividend_basis", "dividends")
    if basis == "dividends_plus_buybacks" and shares_fy:
        D0_default = ttm + buy_cash / shares_fy
        src_d = "Dividends, 12 months + last FY buybacks per share"
    else:
        D0_default, src_d = ttm, "Dividends paid, last 12 months"
    D0, src_d = given("D0", D0_default, src_d)
    if buy_cash > div_cash and basis == "dividends":
        flags.append(("Buybacks exceed dividends: the DDM on dividends alone undervalues the stock", True))

    beta, src_b = given("beta", float(est[t].cov(est["SPY"]) / est["SPY"].var()), f"Slope on SPY, {len(est)} months")
    rf10, src_rf = given("rf10", float(rates["DGS10"].dropna().iloc[-1]), f"FRED DGS10, {rates['DGS10'].dropna().index[-1]:%d.%m.%y}")
    erp = float(v.get("erp", ERP_DEFAULT))
    src_erp = v.get("erp_source", "Bloomberg CRP, Class 5")
    k = rf10 + beta * erp

    method = v.get("method", "two_stage")
    if D0 <= 0:
        method = "none"
    g1, g2, T = float(v.get("g1", 0.0)), float(v.get("g2", 0.02)), int(v.get("T", 5))
    if method != "none" and k <= g2:
        raise SystemExit(f"k ({k:.2%}) must be above g2 ({g2:.2%})")

    def ddm(kk, gg):
        if method == "none" or kk <= gg:
            return None
        return gordon(D0, kk, gg) if method == "gordon" else two_stage(D0, kk, g1, gg, T)

    V_gordon = gordon(D0, k, g2) if D0 > 0 and k > g2 else None
    V_2stage = two_stage(D0, k, g1, g2, T) if D0 > 0 and k > g2 else None
    V_ddm = ddm(k, g2)
    pv_tv = pv_terminal(D0, k, g1, g2, T) if method == "two_stage" and V_ddm else None
    V_ddm_beta1 = ddm(rf10 + erp, g2)
    k_grid = [k + d for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    g_grid = [g2 + d for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    grid = [[ddm(kk, gg) for gg in g_grid] for kk in k_grid]

    # --- comparables
    rows = []
    for p in snap["peers"]:
        m = peer_multiples(snap["info"][p], last_fcf(snap["statements"][p]))
        rows.append({"ticker": p, "name": (cfg.get("peer_names") or {}).get(p) or short_name(snap["info"][p].get("longName")),
                     "market_cap": snap["info"][p].get("marketCap"),
                     **{mid: sane(m[mid], kind) for mid, _, kind in MULTIPLES}})
        cur = snap["info"][p].get("financialCurrency")
        if cur and cur != "USD":
            flags.append((f"{p} reports in {cur}: its ratios are fine, but check it on Bloomberg RV", False))

    price_now = info.get("currentPrice") or P0
    shares = (info.get("marketCap") or 0) / price_now or info.get("sharesOutstanding")
    market_cap = P0 * shares
    net_debt = (info.get("enterpriseValue") or market_cap) - (info.get("marketCap") or market_cap)
    ev = market_cap + net_debt
    eps_fwd, src_fe = given("forward_eps", snap["estimates"]["eps_next"], "Yahoo consensus")
    eps_ttm = info.get("trailingEps")
    bvps, ebitda, revenue = info.get("bookValue"), info.get("ebitda"), info.get("totalRevenue")
    fcf = last_fcf(snap["statements"][t])

    per_share = lambda x: x / shares
    implied = {        # price at a given multiple, for each multiple
        "forward_pe": lambda m: eps_fwd * m,
        "trailing_pe": lambda m: eps_ttm * m if eps_ttm and eps_ttm > 0 else None,
        "p_fcf": lambda m: per_share(m * fcf) if fcf and fcf > 0 else None,
        "ev_ebitda": lambda m: per_share(m * ebitda - net_debt) if ebitda and ebitda > 0 else None,
        "pb": lambda m: bvps * m if bvps and bvps > 0 else None,
        "ps": lambda m: per_share(revenue * m) if revenue else None,
        "ev_sales": lambda m: per_share(m * revenue - net_debt) if revenue else None,
        "yield": lambda m: D0 / (m / 100) if D0 > 0 else None,
    }
    own = {"forward_pe": P0 / eps_fwd if eps_fwd and eps_fwd > 0 else None,
           "trailing_pe": P0 / eps_ttm if eps_ttm and eps_ttm > 0 else None,
           "p_fcf": market_cap / fcf if fcf and fcf > 0 else None,
           "ev_ebitda": ev / ebitda if ebitda and ebitda > 0 else None,
           "pb": P0 / bvps if bvps and bvps > 0 else None,
           "ps": market_cap / revenue if revenue else None,
           "ev_sales": ev / revenue if revenue else None,
           "yield": D0 / P0 * 100 if D0 > 0 else None}
    own = {mid: sane(own[mid], kind) for mid, _, kind in MULTIPLES}

    comps = {}
    for mid, _, kind in MULTIPLES:
        st = stats_of([r[mid] for r in rows])
        for key in ("mean", "median", "min", "max"):
            st[f"price_{key}"] = implied[mid](st[key]) if st[key] is not None else None
        st["own"] = own[mid]
        comps[mid] = st

    primary = list(v.get("comps_primary") or ["forward_pe", "ev_ebitda"])
    outside = [mid for mid in primary if mid not in SHOWN]
    if outside:
        raise SystemExit(f"comps_primary can only use the multiples in the report ({', '.join(SHOWN)}), not {', '.join(outside)}")
    stat = v.get("comps_stat", "median")
    prices = [comps[mid][f"price_{stat}"] for mid in primary if comps[mid][f"price_{stat}"] is not None]
    V_comp = float(np.mean(prices)) if prices else None
    if len(snap["peers"]) < 5:
        flags.append((f"Only {len(snap['peers'])} peers: the template asks for 5 or 6", True))

    # --- fair value: the DDM. The comps are a double check, unless there is no DDM at all
    if V_ddm is None and V_comp is None:
        raise SystemExit("Neither the DDM nor the comparables give a value")
    V0 = V_ddm if V_ddm is not None else V_comp
    if V_ddm is None:
        flags.append(("No dividend, so no DDM: the fair value comes from the comparables", True))
    mos = V0 / P0 - 1
    mos_ddm = V_ddm / P0 - 1 if V_ddm else None
    mos_comp = V_comp / P0 - 1 if V_comp else None
    if mos_ddm is not None and mos_comp is not None:
        methods = "undervalued" if mos_ddm > 0 and mos_comp > 0 else "overvalued" if mos_ddm < 0 and mos_comp < 0 else "mixed: check"
    else:
        methods = "one method only"
    if methods == "mixed: check":
        flags.append(("DDM and comparables disagree (the TA's \"mixed: check\")", True))
    if mos_ddm is not None and mos_ddm > 0.5:
        flags.append(("DDM upside above +50%: more likely a wrong input or a value trap (cheat sheet)", True))
    if method != "none" and k - g2 < 0.03:
        flags.append((f"k − g2 is only {pct(k - g2, 1, False)}: the DDM is very sensitive to the inputs", True))

    # --- value-trap check (Checkpoint 2)
    m = metrics(f)
    peer_metrics = {p: metrics(frame(snap["statements"][p])) for p in snap["peers"]}
    vt = trap_table(m, list(peer_metrics.values()))
    red = list(vt.index[vt["red_flag"]])
    eps_ago, eps_cur = snap["estimates"]["eps_ago"], snap["estimates"]["eps_cur"]
    falling = bool(eps_fwd < eps_ago)
    verdict = trap_verdict(red, falling)
    n_years = len(m)
    peer_path = {}      # peer median by position from the latest fiscal year
    for name in m.columns:
        peer_path[name] = [float(pd.Series([pm[name].iloc[-(n_years - i)] if len(pm) >= n_years - i else np.nan
                                            for pm in peer_metrics.values()]).median())
                           for i in range(n_years)]
    if eps_ttm is not None and eps_ttm <= 0:
        flags.append(("Trailing EPS is negative: forward vs trailing is meaningless, use adjusted EPS", False))

    roe_fwd = eps_fwd / bvps if bvps and bvps > 0 and eps_fwd else None
    payout_fwd = D0 / eps_fwd if eps_fwd and eps_fwd > 0 else None
    g_sust = (eps_fwd - D0) / bvps if roe_fwd is not None and D0 >= 0 else None
    pb_just = roe_fwd * payout_fwd / (k - g2) if roe_fwd and payout_fwd and k > g2 else None

    # --- index model on the SAA and alpha
    beta_S, s2_eps = regress_on_saa(est[t], R_S)
    sig_eps = math.sqrt(s2_eps)
    p = float(a.get("probability_gap_closes", 1.0))
    a_never = alpha_never(D0, P0, g2, k)
    a_closed = alpha_closed(V0, P0, k)
    alpha = p * a_closed + (1 - p) * a_never
    ir = alpha / sig_eps

    if alpha < 0:
        flags.append(("Negative alpha: weight 0 (long-only)", True))
    if ir > IR_BUFFETT:
        flags.append((f"IR of {ir:.2f} is above Buffett's {IR_BUFFETT:.2f}: the alpha is probably too optimistic", True))
    if verdict == "Fail" and p > 0 and alpha > 0:
        flags.append(("The value-trap check fails but the alpha assumes the gap closes: use probability 0 or drop the stock", True))

    n_issues = len(cfg.get("issues") or [])
    if n_issues not in (2, 3):
        flags.append((f"{n_issues} specific issues: the template asks for 2 or 3", True))

    catalysts = cfg.get("catalysts") or []
    if not catalysts:
        flags.append(("No catalyst: use alpha never (probability 0)", True))
    for c in catalysts:
        d = pd.Timestamp(c["date"]) if c.get("date") else None
        if d is None or not ENTRY_DATE <= d <= CHALLENGE_END:
            flags.append((f"Catalyst outside {ENTRY_DATE:%d %b}–{CHALLENGE_END:%d %b}: {c.get('event', '?')}", True))
    if snap.get("latest_close", snap["as_of"]) > snap["as_of"]:
        flags.append((f"Peer multiples and consensus are from {snap['latest_close']}, later than the price date: re-run sooner or check them", True))
    if as_of != ENTRY_DATE:
        flags.append((f"Price date is {as_of:%d.%m.%y}, not the close of 6 Nov: re-run on 7–8 November", False))

    if alpha < 0:
        signal = "No position: negative alpha"
    elif verdict == "Fail":
        signal = "Value trap: gap assumed not to close" if p == 0 else "Value trap: review the alpha"
    else:
        signal = "Long candidate"

    target_mean = info.get("targetMeanPrice")
    fy_labels = [f"FY{d.year % 100:02d}" for d in m.index]
    fig = {
        "ticker": t, "as_of": snap["as_of"], "downloaded_at": snap["downloaded_at"],
        "name": cfg.get("name") or short_name(info.get("longName")), "exchange": info.get("fullExchangeName"),
        "sector": info.get("sector"), "industry": info.get("industry"), "currency": info.get("currency"),
        "P0": P0, "D0": D0, "beta": beta, "rf10": rf10, "erp": erp, "k": k, "g1": g1, "g2": g2, "T": T, "method": method,
        "sources": {"P0": src_p, "D0": src_d, "beta": src_b, "rf10": src_rf, "erp": src_erp, "forward_eps": src_fe},
        "V_gordon": V_gordon, "V_2stage": V_2stage, "V_ddm": V_ddm, "pv_tv": pv_tv, "tv_share": pv_tv / V_ddm if pv_tv else None,
        "V_ddm_beta1": V_ddm_beta1, "V_comp": V_comp, "V0": V0, "mos": mos, "mos_ddm": mos_ddm,
        "mos_comp": mos_comp, "methods_verdict": methods, "implied_g": implied_growth(P0, D0, k) if D0 > 0 else None,
        "k_grid": k_grid, "g_grid": g_grid, "grid": grid,
        "market_cap": market_cap, "enterprise_value": ev, "net_debt": net_debt, "shares": shares, "ebitda": ebitda, "revenue": revenue, "fcf_last": fcf,
        "bvps": bvps, "eps_ttm": eps_ttm, "eps_ago": eps_ago, "eps_cur": eps_cur, "eps_fwd": eps_fwd,
        "eps_growth_next": snap["estimates"]["growth_next"], "dividend_yield": D0 / P0, "week52_low": info.get("fiftyTwoWeekLow"),
        "week52_high": info.get("fiftyTwoWeekHigh"), "target_mean": target_mean, "target_low": info.get("targetLowPrice"),
        "target_high": info.get("targetHighPrice"), "n_analysts": info.get("numberOfAnalystOpinions"),
        "target_up": target_mean / P0 - 1 if target_mean else None,
        "next_earnings": snap.get("next_earnings") if snap.get("next_earnings") and pd.Timestamp(snap["next_earnings"]) >= as_of else None,
        "peers": rows, "comps": comps, "comps_primary": primary, "comps_stat": stat,
        "fy_labels": fy_labels, "metrics": {c: [None if pd.isna(x) else float(x) for x in m[c]] for c in m.columns},
        "peer_median": {c: [None if pd.isna(x) else x for x in peer_path[c]] for c in m.columns},
        "fcf": [None if pd.isna(x) else float(x) for x in f["Free Cash Flow"]],
        "payout_cash": [float(-(np.nan_to_num(a1) + np.nan_to_num(b1))) for a1, b1 in zip(f["Cash Dividends Paid"], f["Repurchase Of Capital Stock"])],
        "trap": {name: {k1: (None if (isinstance(x, float) and np.isnan(x)) else (bool(x) if isinstance(x, (bool, np.bool_)) else x))
                        for k1, x in row.items()} for name, row in vt.to_dict("index").items()},
        "red_flags": red, "earnings_falling": falling, "trap_verdict": verdict,
        "roe_fwd": roe_fwd, "payout_fwd": payout_fwd, "g_sust": g_sust, "pb_just": pb_just, "pb": own["pb"],
        "beta_S": beta_S, "sigma2_eps": s2_eps, "sigma_eps": sig_eps, "vol": float(est[t].std() * math.sqrt(12)),
        "te_per_unit": float((est[t] - R_S).std() * math.sqrt(12)), "score": alpha / s2_eps,
        "window": [est.index[0].strftime("%Y-%m"), est.index[-1].strftime("%Y-%m")], "saa_vol": float(sigma_S), "saa_excess": float(mu_S),
        "alpha_never": a_never, "alpha_closed": a_closed, "probability": p, "alpha": alpha, "ir": ir,
        "ir_closed": a_closed / sig_eps, "ir_never": a_never / sig_eps,
        "signal": signal, "flags": [x[0] for x in flags], "flags_report": [x[0] for x in flags if x[1]],
    }
    return fig


# ---------------------------------------------------------------- formatting

def minus(s):
    return s.replace("-", "−")


def num(x, d=2, plus=False, none="n/a"):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return none
    return minus(f"{x:+,.{d}f}" if plus else f"{x:,.{d}f}")


def pct(x, d=1, plus=False, none="n/a"):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return none
    return minus(f"{x * 100:+.{d}f}%" if plus else f"{x * 100:.{d}f}%")


def usd(x, none="n/a"):
    return none if x is None else f"USD {x:,.2f}"


def mult(x, d=1, none="n/m"):
    return none if x is None else f"{x:.{d}f}x"


def bn(x, none="n/a"):
    return none if not x else f"{x / 1e9:,.1f}bn"


def day(s):
    return pd.Timestamp(s).strftime("%d.%m.%y") if s else "n/a"


def tokens(fig):
    """The values YAML text can use as {name}: they update when the report is re-run."""
    c = fig["comps"]
    grid_cells = [x for row in fig["grid"] for x in row if x is not None]
    return {
        "P0": usd(fig["P0"]), "D0": usd(fig["D0"]), "V0": usd(fig["V0"]), "V_ddm": usd(fig["V_ddm"]), "V_comp": usd(fig["V_comp"]),
        "V_ddm_beta1": usd(fig["V_ddm_beta1"]), "V_gordon": usd(fig["V_gordon"]),
        "mos": pct(fig["mos"], 0, True), "mos_ddm": pct(fig["mos_ddm"], 0, True), "mos_comp": pct(fig["mos_comp"], 0, True),
        "k": pct(fig["k"], 2), "beta": num(fig["beta"]), "rf10": pct(fig["rf10"], 2), "erp": pct(fig["erp"], 2),
        "g1": pct(fig["g1"], 1), "g2": pct(fig["g2"], 1), "T": str(fig["T"]), "implied_g": pct(fig["implied_g"], 1),
        "alpha": pct(fig["alpha"], 1), "alpha_closed": pct(fig["alpha_closed"], 1), "alpha_never": pct(fig["alpha_never"], 1),
        "ir": num(fig["ir"]),
        "eps_ago": num(fig["eps_ago"]), "eps_cur": num(fig["eps_cur"]), "eps_fwd": num(fig["eps_fwd"]), "eps_ttm": num(fig["eps_ttm"]),
        "eps_growth": pct(fig["eps_growth_next"], 1), "yield": pct(fig["dividend_yield"], 1),
        "fpe": mult(c["forward_pe"]["own"]), "fpe_med": mult(c["forward_pe"]["median"]), "tpe": mult(c["trailing_pe"]["own"]),
        "ev_ebitda": mult(c["ev_ebitda"]["own"]), "ev_ebitda_med": mult(c["ev_ebitda"]["median"]),
        "pfcf": mult(c["p_fcf"]["own"]), "pfcf_med": mult(c["p_fcf"]["median"]),
        "pb": mult(fig["pb"], 2), "pb_just": mult(fig["pb_just"], 2), "roe_fwd": pct(fig["roe_fwd"], 1),
        "payout_fwd": pct(fig["payout_fwd"], 0), "retention": pct(1 - fig["payout_fwd"], 0) if fig["payout_fwd"] is not None else "n/a",
        "g_sust": pct(fig["g_sust"], 1), "de": num(fig["metrics"]["debt / equity"][-1]),
        "payout_fcf": num(fig["metrics"]["payout / FCF"][-1]), "target": usd(fig["target_mean"]), "target_up": pct(fig["target_up"], 0, True),
        "fy": fig["fy_labels"][-1], "fy_prev": fig["fy_labels"][-2] if len(fig["fy_labels"]) > 1 else "",
        "red_flags": ", ".join(fig["red_flags"]) or "no metric", "tv_share": pct(fig["tv_share"], 0), "verdict": fig["trap_verdict"],
        "grid_above": f"{sum(x >= fig['P0'] for x in grid_cells)} of {len(grid_cells)}",
    }


def rich(text, tok):
    """YAML text to HTML: {tokens}, **bold**. Everything else is escaped."""
    if not text:
        return '<span style="font-weight:600;">[TO FILL]</span>'
    try:
        s = str(text).strip().format_map(tok)
    except KeyError as e:
        raise SystemExit(f"Unknown token {e} in the YAML text: {str(text)[:60]}... Known: {', '.join(sorted(tok))}")
    return re.sub(r"\*\*(.+?)\*\*", r'<span style="font-weight:600;">\1</span>', html.escape(s, quote=False))


# ---------------------------------------------------------------- HTML blocks (inline styles, as in Round 1)

DDM_ROW = 22    # px: the DDM inputs and the sensitivity matrix share it, so their rows line up
SECTION = "font-size:12.5px;font-weight:600;letter-spacing:0.38px;text-transform:uppercase;"
SMALL_CAP = f"font-size:9.6px;font-weight:600;letter-spacing:0.29px;text-transform:uppercase;color:{MUTED};"
BODY = "margin:0;font-size:12px;line-height:1.55;"
NOTE = f"margin:0;font-size:9.8px;line-height:1.45;font-style:italic;color:{MUTED};"


def tag(text):
    return (f'<span style="background:{INK};color:#ffffff;{MONO}font-size:9.6px;font-weight:500;letter-spacing:0.29px;text-transform:uppercase;'
            f'padding:2.5px 9px;border-radius:999px;white-space:nowrap;">{text}</span>')


def table(head, rows, size=11, pad=3.2, first=0, gutter=6, row_h=None):
    """head: [(title, align, extra style)], rows: [(cells, row options)], a cell is a string or (string, extra style).
    row_h: a fixed row height, so that two tables side by side line up."""
    fixed = f"height:{row_h}px;" if row_h else ""
    ths = "".join(f'<th style="padding:{pad + 0.8}px 0 {pad + 0.8}px {gutter if i else first}px;font-weight:600;text-align:{al};{ex}">{ti}</th>'
                  for i, (ti, al, ex) in enumerate(head))
    out = [f'<table style="width:100%;border-collapse:collapse;font-size:{size}px;">'
           f'<thead><tr style="{fixed}border-bottom:1px solid {INK};font-size:9.4px;letter-spacing:0.28px;text-transform:uppercase;color:{MUTED};">{ths}</tr></thead><tbody>']
    for r, (cells, opt) in enumerate(rows):
        opt = opt or {}
        border = INK if (opt.get("line") or r == len(rows) - 1) else LINE
        style = f"{fixed}border-bottom:1px solid {border};"
        if opt.get("bg"):
            style += f"background:{opt['bg']};"
        if opt.get("bold"):
            style += "font-weight:600;"
        if opt.get("muted"):
            style += f"color:{MUTED};"
        tds = []
        for i, c in enumerate(cells):
            txt, ex = c if isinstance(c, tuple) else (c, "")
            al = head[i][1] if i < len(head) else "left"
            left = gutter if i else first
            tds.append(f'<td style="padding:{pad}px 0 {pad}px {left}px;text-align:{al};vertical-align:top;{ex}">{txt}</td>')
        out.append(f'<tr style="{style}">{"".join(tds)}</tr>')
    out.append("</tbody></table>")
    return "".join(out)


def tx(x, y, s, anchor="start", size=8, fill=MUTED, weight=None, family="Geist Mono", halo=None):
    w = f' font-weight="{weight}"' if weight else ""
    h = f' paint-order="stroke" stroke="{halo}" stroke-width="2.6"' if halo else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{family}" font-size="{size}" fill="{fill}"{w}{h}>{s}</text>'


def ln(x1, y1, x2, y2, stroke=LINE_B, width=0.8, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}"{d}></line>'


def rc(x, y, w, h, fill, rx=0):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{h:.1f}" fill="{fill}" rx="{rx}"></rect>'


def dot(x, y, r, fill=INK, ring=CARD):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{ring}" stroke-width="1.5"></circle>'


def polyline(pts, stroke=INK, width=2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<polyline points="{p}" fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"{d}></polyline>'


def svg(w, h, body):
    return f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto;display:block;overflow:visible;">{body}</svg>'


def nice_ticks(lo, hi, n=5):
    span = hi - lo or abs(hi) or 1
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    start = math.ceil(lo / step) * step
    return [start + i * step for i in range(int((hi - start) / step + 1e-9) + 1)]


def mini_line(title, values, peers, labels, fmt, W=153, H=64):
    L, R, T, B = 26, 5, 17, 12
    pts = [(i, v) for i, v in enumerate(values) if v is not None]
    ppts = [(i, v) for i, v in enumerate(peers or []) if v is not None]
    n = len(values)
    all_v = [v for _, v in pts + ppts]
    head = tx(0, 9, title, size=10, fill=INK, weight=500, family="Geist")
    if not all_v:
        return svg(W, H, head)
    lo, hi = min(all_v), max(all_v)
    if lo == hi:
        lo, hi = lo - 0.01, hi + 0.01
    pad = (hi - lo) * 0.14
    lo, hi = lo - pad, hi + pad
    X = lambda i: L + i / max(n - 1, 1) * (W - L - R)
    Y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    body = head + tx(W, 9, fmt(values[-1]) if values[-1] is not None else "n/m", "end", 9.4, INK, 600)
    for v in nice_ticks(lo, hi, 3)[:4]:
        body += ln(L, Y(v), W - R, Y(v), INK if abs(v) < 1e-12 else LINE_B, 0.6)
        body += tx(L - 3, Y(v) + 2.8, fmt(v, True), "end", 8)
    if ppts:
        body += polyline([(X(i), Y(v)) for i, v in ppts], REF, 1.2, "3 2.4")
    if pts:
        body += polyline([(X(i), Y(v)) for i, v in pts], INK, 1.5)
        body += dot(X(pts[-1][0]), Y(pts[-1][1]), 2.2)
    body += tx(X(0), H - 1, labels[0], "start", 8) + tx(X(n - 1), H - 1, labels[-1], "end", 8)
    return svg(W, H, body)


def mini_bars(title, a, b, labels, W=153, H=64):
    L, R, T, B = 30, 1, 17, 12
    if all(x is None for x in a + b):               # nothing to draw (an empty stock slot)
        return svg(W, H, tx(0, 9, title, size=10, fill=INK, weight=500, family="Geist"))
    a, b = [x or 0 for x in a], [x or 0 for x in b]
    hi = max(a + b + [1])
    lo = min(a + b + [0])
    slot = (W - L - R) / len(a)
    bw = min((slot - 4) / 2, 20)
    Y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    body = tx(0, 9, title, size=10, fill=INK, weight=500, family="Geist")
    for v in nice_ticks(lo, hi, 2)[:3]:
        body += ln(L, Y(v), W - R, Y(v), INK if abs(v) < 1e-9 else LINE_B, 0.6)
        body += tx(L - 3, Y(v) + 2.8, minus(f"{v / 1e6:,.0f}"), "end", 8)
    for i, (x, y) in enumerate(zip(a, b)):
        cx = L + i * slot + slot / 2
        body += rc(cx - bw - 0.5, min(Y(x), Y(0)), bw, abs(Y(x) - Y(0)), INK, 0.8)
        body += rc(cx + 0.5, min(Y(y), Y(0)), bw, abs(Y(y) - Y(0)), RANGE_HI, 0.8)
    body += tx(L, H - 1, labels[0], "start", 8) + tx(W - R, H - 1, labels[-1], "end", 8)
    return svg(W, H, body)


def stat(label, value, sub):
    return (f'<div style="display:flex;flex-direction:column;gap:4px;min-width:0;"><span style="{SMALL_CAP}white-space:nowrap;">{label}</span>'
            f'<span style="{MONO}font-size:18px;font-weight:600;white-space:nowrap;">{value}</span>'
            f'<span style="font-size:9.4px;color:{MUTED};white-space:nowrap;">{sub}</span></div>')


def legend_item(text, kind):
    swatch = {"solid": f"width:14px;height:2px;background:{INK};", "dash": f"width:14px;border-top:1.5px dashed {REF};",
              "bar": f"width:10px;height:6px;background:{RANGE_HI};", "bar_dark": f"width:10px;height:6px;background:{INK};"}[kind]
    return f'<span style="display:flex;align-items:center;gap:4px;"><span style="{swatch}"></span>{text}</span>'


def legend(items):
    return f'<span style="display:flex;gap:12px;font-size:9.6px;color:{MUTED};">{"".join(legend_item(a, b) for a, b in items)}</span>'


def card(title, right, content, pad="12px 14px 11px"):
    return (f'<div style="background:{CARD};border-radius:16px;padding:{pad};display:flex;flex-direction:column;gap:8px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:12px;"><span style="{SECTION}font-size:11px;">{title}</span>{right}</div>'
            f'{content}</div>')


def footer(page, total):
    return (f'<div style="margin-top:auto;display:flex;justify-content:space-between;align-items:center;font-size:10px;color:{MUTED};">'
            f'<div style="display:flex;align-items:center;gap:7px;"><svg width="14" height="14" viewBox="0 0 32 32" style="flex:none;display:block;"><path d="{LOGO}" fill="{INK}"></path></svg>'
            f'<span>Matterhorn Capital Management · AMC 2026 Round 2 · Group 3</span></div><span style="{MONO}">{page:02d} / {total:02d}</span></div>')


def blocks(cfg, fig):
    tok = tokens(fig)
    txt = cfg.get("text") or {}
    t = fig["ticker"]
    fy = fig["fy_labels"][-1]
    c = fig["comps"]
    b = {"title": f"{fig['name']} ({t}) · Matterhorn Capital Management", "runtime": RUNTIME, "ticker": t}

    # --- header
    meta = " · ".join(x for x in [fig["exchange"], fig["sector"], fig["industry"], fig["currency"], f"Price date {day(fig['as_of'])}"] if x)
    b["header"] = (
        '<div style="display:flex;flex-direction:column;gap:6px;">'
        f'<div style="display:flex;align-items:baseline;gap:10px;"><h2 style="margin:0;font-size:30px;line-height:1.1;font-weight:600;letter-spacing:-0.9px;">{html.escape(fig["name"])}</h2>'
        f'<span style="{MONO}font-size:15px;font-weight:600;">{t}</span></div>'
        f'<span style="{MONO}font-size:10px;color:{MUTED};">{html.escape(meta)}</span></div>')

    # --- stat card, in the order of the reasoning
    b["stats"] = (
        f'<div style="background:{CARD};border-radius:16px;padding:13px 16px;display:grid;grid-template-columns:repeat(6,auto);justify-content:space-between;gap:8px;">'
        + stat("Fair value", num(fig["V0"]), "DDM" if fig["V_ddm"] is not None or fig.get("placeholder") else "Comparables: no DDM")
        + stat("Price", num(fig["P0"]), f"USD, close {day(fig['as_of'])}")
        + stat("Margin of safety", pct(fig["mos"], 1, True), f"{V_0} / {P_0} − 1")
        + stat("Alpha, annual", pct(fig["alpha"], 1, True), f"IR {num(fig['ir'])}")
        + stat("Market cap", bn(fig["market_cap"]), "USD")
        + stat("Dividend yield", pct(fig["dividend_yield"], 1), f"D0 USD {num(fig['D0'])}")
        + "</div>")

    # --- investment case: fair value, price, margin of safety and alpha, catalyst, decision
    case = cfg.get("case") or {}
    chance = fig["probability"]
    assumption = ("[assumption]" if chance is None else "the gap closes within one year" if chance == 1 else "the gap never closes" if chance == 0
                  else f"a {chance * 100:.0f}% chance that the gap closes within one year")
    step = lambda label, content: (f'<div style="display:grid;grid-template-columns:112px 1fr;gap:14px;border-top:1px solid {LINE};padding-top:6px;">'
                                   f'<span style="{SMALL_CAP}padding-top:3px;">{label}</span><div style="display:flex;flex-direction:column;gap:5px;">{content}</div></div>')
    events = "".join(f'<p style="{BODY}"><span style="font-weight:600;">{rich(x.get("event"), tok)}</span> · <span style="{MONO}font-size:10.4px;">{rich(x.get("date_label") or str(x.get("date")), tok)}</span>. '
                     f'{rich(x.get("why"), tok)} {rich(x.get("effect"), tok)}</p>' for x in cfg.get("catalysts") or []) or f'<p style="{BODY}">{rich(None, tok)}</p>'
    b["case"] = (step("Fair value vs price", f'<p style="{BODY}">{rich(case.get("value"), tok)}</p>')
                 + step("Margin of safety and alpha", f'<p style="{BODY}">Margin of safety {pct(fig["mos"], 1, True)}, alpha {pct(fig["alpha"], 1, True)} a year (IR {num(fig["ir"])}), assuming {assumption}.</p>')
                 + step("Catalyst", events)
                 + step("Decision", f'<p style="{BODY}"><span style="font-weight:600;">{html.escape(fig["signal"])}.</span> {rich(case.get("decision"), tok)}</p>'))

    # --- method
    m = cfg.get("method_text") or {}
    col = "display:flex;flex-direction:column;gap:4px;border-top:1px solid #111111;padding-top:6px;"
    b["method"] = (f'<div style="display:grid;grid-template-columns:1.22fr 1fr;gap:20px;"><div style="{col}"><span style="{SMALL_CAP}">Why this method</span><p style="{BODY}font-size:11.6px;">{rich(m.get("why"), tok)}</p></div>'
                   f'<div style="{col}"><span style="{SMALL_CAP}">Methods that do not fit</span><p style="{BODY}font-size:11.6px;">{rich(m.get("not_suitable"), tok)}</p></div></div>')

    # --- DDM inputs
    v = cfg.get("valuation") or {}
    src = fig["sources"]
    two = fig["method"] == "two_stage"
    inp = [(f"{P_0}, price", usd(fig["P0"]), src["P0"]), (f"{D_0}, dividend", usd(fig["D0"]), src["D0"]),
           ("β on SPY", num(fig["beta"]), src["beta"]), (f"{R_F}, 10-year yield", pct(fig["rf10"], 2), src["rf10"]),
           ("ERP", pct(fig["erp"], 2), src["erp"]), (f"k = {R_F} + β ERP", pct(fig["k"], 2), "CAPM"),
           (f"{G_1}, first stage", pct(fig["g1"], 1) if two else "not used", rich(v.get("g1_source"), tok) if two else "Gordon: one growth rate"),
           ("T, years", (str(fig["T"]) if fig["T"] is not None else "n/a") if two else "not used", rich(v.get("T_source"), tok) if two else ""),
           (f"{G_2}, terminal", pct(fig["g2"], 1), rich(v.get("g2_source"), tok))]
    rows = [([(a1, ""), (a2, f"{MONO}font-weight:500;white-space:nowrap;"), (a3, f"color:{MUTED};font-size:9.8px;")], {}) for a1, a2, a3 in inp]
    used = lambda on: {"bold": True, "bg": CARD} if on else {}
    rows[-1] = (rows[-1][0], {"line": True})
    rows.append((["Gordon value", (usd(fig["V_gordon"]), f"{MONO}white-space:nowrap;"), (f"{pct(fig['V_gordon'] / fig['P0'] - 1, 0, True) if fig['V_gordon'] else 'n/a'} vs price", "")], used(fig["method"] == "gordon")))
    rows.append((["Two-stage value", (usd(fig["V_2stage"]), f"{MONO}white-space:nowrap;"),
                  (f"{pct(fig['V_2stage'] / fig['P0'] - 1, 0, True) if fig['V_2stage'] else 'n/a'} vs price" + (f"; {pct(fig['tv_share'], 0)} terminal value" if fig["tv_share"] else ""), "")], used(two)))
    b["ddm_inputs"] = table([("Input", "left", "width:27%;"), ("Value", "right", "width:17%;"), ("Source or reason", "left", "")], rows, size=10.8, pad=3.3, first=4, gutter=9, row_h=DDM_ROW)

    # --- sensitivity
    if fig["method"] == "none":
        b["sensitivity"] = f'<p style="{BODY}">The company pays no dividend, so the DDM does not apply: the fair value comes from the comparables.</p>'
    else:
        head = [(f"k \\ {G_2}", "left", "text-transform:none;")] + [(pct(g, 1), "right", "") for g in fig["g_grid"]]
        rows = []
        for i, kk in enumerate(fig["k_grid"]):
            cells = [(pct(kk, 2), f"{MONO}font-weight:{600 if i == 2 else 400};")]
            for j, val in enumerate(fig["grid"][i]):
                bg = ""
                if i == 2 and j == 2:
                    bg = f"background:{RANGE};font-weight:600;"
                elif val is not None and val >= fig["P0"]:
                    bg = f"background:{CARD};"
                cells.append((num(val, 2, none="n/m"), f"{MONO}{bg}padding-right:3px;"))
            rows.append((cells, {}))
        base = fig["grid"][2]
        rows.append(([("Upside", "font-size:9.8px;")] + [(pct(x / fig["P0"] - 1, 0, True) if x else "n/m", f"{MONO}font-size:9.8px;padding-right:3px;") for x in base], {"muted": True}))
        b["sensitivity"] = table(head, rows, size=10.8, pad=3.3, row_h=DDM_ROW) + (
            f'<p style="{NOTE}">{"Two-stage" if two else "Gordon"} DDM value, USD. Shaded: at or above the price of {num(fig["P0"])}. Dark: base case. Upside at the base k.</p>'
            f'<p style="{BODY}font-size:11.2px;line-height:1.5;">{rich(m.get("sensitivity"), tok)}</p>')

    # --- comps table: a double check
    shown = [m for m in MULTIPLES if m[0] in SHOWN]
    stats = (("average", "mean"), ("median", "median"))
    stat_name = dict((key, name) for name, key in stats)[fig["comps_stat"]]
    shade = lambda mid: f"background:{CARD};" if mid in fig["comps_primary"] else ""
    fmt_m = lambda x: "n/m" if x is None else f"{x:.1f}x"
    cap = lambda x: f"{x / 1e9:,.1f}" if x else "n/a"     # every real stock and peer has one: the download checks it
    head = [("Company", "left", "width:44%;"), ("Cap, bn", "right", "width:11%;")] + [(ti, "right", "width:15%;" + shade(mid)) for mid, ti, _ in shown]
    rows = []
    for r in fig["peers"]:
        rows.append(([f'<span style="{MONO}font-weight:600;">{r["ticker"]}</span> {html.escape(r["name"])}', (cap(r["market_cap"]), MONO)]
                     + [(fmt_m(r[mid]), f"{MONO}{shade(mid)}") for mid, _, _ in shown], {}))
    rows[-1] = (rows[-1][0], {"line": True})
    for name, key in stats:
        rows.append(([(f"Peer {name}", "font-weight:500;"), ""] + [(fmt_m(c[mid][key]), f"{MONO}font-weight:500;{shade(mid)}") for mid, _, _ in shown], {}))
    rows.append(([f'<span style="{MONO}font-weight:600;">{t}</span> {html.escape(fig["name"])}', (cap(fig["market_cap"]), f"{MONO}font-weight:600;")]
                 + [(fmt_m(c[mid]["own"]), f"{MONO}font-weight:600;{shade(mid)}") for mid, _, _ in shown], {"line": True}))
    for name, key in stats:
        rows.append(([(f"Implied price at peer {name}", ""), ""] + [(num(c[mid][f"price_{key}"], 2), f"{MONO}{shade(mid)}") for mid, _, _ in shown], {}))
    b["comps"] = table(head, rows, size=10.8, pad=2.8)
    fv_comp = f"{usd(fig['V_comp'])} ({pct(fig['mos_comp'], 0, True)})" if fig["V_comp"] else "n/a"
    b["comps_note"] = f'<p style="{NOTE}">Comps value {fv_comp}: average of the {stat_name} implied prices in shaded columns. P/FCF on last FY\'s FCF. n/m: negative or above 100x.</p>'

    # --- value-trap table
    rows = []
    fmt_t = lambda x, is_pct: ("n/m" if x is None else pct(x, 1) if is_pct else num(x, 2))
    for name, char, _, is_pct in TRAP_METRICS:
        r = fig["trap"][name]
        lvl = {True: "better", False: "worse"}.get(r["better_than_peers"], "n/a")
        trd = {True: "improving", False: "worsening"}.get(r["improving"], "n/a")
        red = bool(r["red_flag"])
        rows.append(([(char, f"color:{MUTED};font-size:9.8px;"), name[0].upper() + name[1:], (fmt_t(r["value"], is_pct), f"{MONO}font-weight:500;"), (fmt_t(r["peer"], is_pct), MONO),
                      (fmt_t(r["own"], is_pct), MONO), lvl, trd, ("Red flag" if red else "", "font-weight:600;")], {"bg": CARD} if red else {}))
    b["trap_table"] = table([("Characteristic", "left", "width:13%;"), ("Metric", "left", "width:16%;"), (fy, "right", ""), ("Peer median", "right", ""), ("Own past avg.", "right", ""),
                             ("Vs peers", "left", "padding-left:14px;"), ("Trend", "left", ""), ("", "left", "")],
                            [([x[0], x[1], x[2], x[3], x[4], (x[5], "padding-left:14px;"), x[6], x[7]], o) for x, o in rows], size=10.8, pad=2.1, first=4)

    fl = "n/a" if fig.get("placeholder") else "falling" if fig["earnings_falling"] else "rising"
    verdict_rule = {"Fail": "Red flags and falling earnings: value trap.", "Watch": "Red flags or falling earnings, not both: watch, not a trap.", "Pass": "No red flags, earnings rising: pass."}.get(fig["trap_verdict"], "")
    distorted = fig["eps_ttm"] is not None and abs(fig["eps_ttm"] / fig["eps_ago"] - 1) > 0.2 if fig["eps_ago"] else False
    ttm_note = ("Trailing GAAP EPS: n/a." if fig.get("placeholder") else
                f'Trailing GAAP EPS of {num(fig["eps_ttm"])} ' + ("includes one-off items." if distorted else "is close to the adjusted figure."))
    b["earnings_line"] = (f'<p style="{BODY}font-size:11.2px;line-height:1.5;margin-top:3px;"><span style="font-weight:600;">Earnings test:</span> adjusted EPS {num(fig["eps_ago"])} ({fy}) → {num(fig["eps_cur"])} → {num(fig["eps_fwd"])} (forward): {fl}. '
                          f'{ttm_note}</p>')

    charts = []
    for name in ("ROE", "FCF margin", "revenue growth"):
        vals, peers, lbl = fig["metrics"][name], fig["peer_median"][name], fig["fy_labels"]
        if name == "revenue growth":     # the first year has no growth rate
            vals, peers, lbl = vals[1:], peers[1:], lbl[1:]
        charts.append(mini_line(name[0].upper() + name[1:], vals, peers, lbl, lambda x, axis=False: pct(x, 0 if axis else 1)))
    charts.append(mini_bars("FCF vs payout, USD m", fig["fcf"], fig["payout_cash"], fig["fy_labels"]))
    grid = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;">' + "".join(f"<div>{x}</div>" for x in charts) + "</div>"
    b["evolution"] = card("Evolution vs peer median", legend([(t, "solid"), ("Peer median", "dash"), ("FCF", "bar_dark"), ("Dividends + buybacks", "bar")]), grid, "9px 14px 8px")

    # --- verdict
    b["verdict"] = (f'<div style="display:flex;gap:10px;align-items:flex-start;">{tag(fig["trap_verdict"])}'
                    f'<p style="{BODY}font-size:11.2px;line-height:1.5;"><span style="font-weight:600;">{verdict_rule}</span> {rich(txt.get("value_trap"), tok)}</p></div>')

    # --- alpha
    assume = ("Used: [assumption]" if chance is None else "Used: closes in 1 year" if chance == 1 else "Used: never closes" if chance == 0
              else f"Used: {chance * 100:.0f}% closes in 1 year")
    formula = f"color:{MUTED};font-size:9.8px;"
    rows = [(["Gap closes in 1 year", (f"α closed = (1 + k)({V_0} − {P_0}) / {P_0}", formula), (pct(fig["alpha_closed"], 1, True), MONO), (num(fig["ir_closed"]), MONO)], {}),
            (["Gap never closes", (f"α never = {D_1} / {P_0} + g − k", formula), (pct(fig["alpha_never"], 1, True), MONO), (num(fig["ir_never"]), MONO)], {"line": True}),
            ([assume, ("Goes into Treynor-Black", "font-size:9.8px;"), (pct(fig["alpha"], 1, True), MONO), (num(fig["ir"]), MONO)], {"bg": RANGE, "bold": True})]
    alpha_t = table([("Assumption", "left", "width:36%;"), ("Formula", "left", ""), ("α, annual", "right", "text-transform:none;"), ("IR", "right", "")], rows, size=10.6, pad=2.4, first=4)
    b["alpha"] = (f'<div style="display:grid;grid-template-columns:1.5fr 1fr;gap:18px;align-items:start;">{alpha_t}'
                  f'<p style="{BODY}font-size:11.2px;line-height:1.5;">{rich((cfg.get("alpha") or {}).get("rationale"), tok)} IR {num(fig["ir"])}, against {IR_BUFFETT:.2f} for Buffett.</p></div>')

    # --- issues
    items = cfg.get("issues") or [{}, {}]
    cells = "".join(f'<div style="display:flex;flex-direction:column;gap:3px;border-top:1px solid {INK};padding-top:6px;"><span style="{SECTION}font-size:10.4px;">{rich(x.get("title"), tok)}</span><p style="{BODY}font-size:11.2px;line-height:1.5;">{rich(x.get("text"), tok)}</p></div>' for x in items)
    b["issues"] = f'<div style="display:grid;grid-template-columns:repeat({len(items)},1fr);gap:20px;">{cells}</div>'

    # --- flags and sources
    b["flags"] = (f'<p style="{NOTE}"><span style="font-weight:600;">Model flags:</span> {html.escape("; ".join(fig["flags_report"]))}.</p>' if fig["flags_report"] else "")
    src_items = []
    for i, s in enumerate(cfg.get("sources") or [], 1):
        label = html.escape(s.get("text", ""))
        src_items.append(f'[{i}] <a href="{html.escape(s["url"])}">{label}</a>' if s.get("url") else f"[{i}] {label}")
    data_note = f"Market data: Yahoo Finance and FRED, downloaded {snap_time(fig)}."
    b["sources"] = f'<p style="margin:0;font-size:8.8px;line-height:1.4;color:{MUTED};">{" ".join(src_items)} {data_note}</p>'

    left = f"Stock analysis · Valuation dossier — {t}"
    b["running_left_1"], b["running_left_2"] = left, f"{left} · Checks"
    pages = cfg.get("pages") or {}
    first, total = int(pages.get("first", 1)), int(pages.get("total", 2))
    b["footer_1"], b["footer_2"] = footer(first, total), footer(first + 1, total)
    return b


def snap_time(fig):
    return pd.Timestamp(fig["downloaded_at"]).strftime("%d.%m.%y") if fig.get("downloaded_at") else "n/a"


# ---------------------------------------------------------------- empty slot of the Round 2 report

def placeholder_fig(label, cfg):
    """A stock with every number missing, in the shape analyse() returns: the same layout, no values."""
    n_years, n_peers, n_grid = 4, 6, 5
    numbers = ("P0 D0 beta rf10 erp k g1 g2 T V_gordon V_2stage V_ddm pv_tv tv_share V_ddm_beta1 V_comp V0 mos mos_ddm mos_comp "
               "implied_g market_cap bvps eps_ttm eps_ago eps_cur eps_fwd eps_growth_next dividend_yield target_mean target_up "
               "roe_fwd payout_fwd g_sust pb_just pb beta_S sigma2_eps sigma_eps alpha_never alpha_closed probability alpha ir "
               "ir_closed ir_never").split()
    v = cfg.get("valuation") or {}
    fig = dict.fromkeys(numbers)
    fig.update({
        "placeholder": True, "ticker": label, "name": "[Company name]", "exchange": "[Exchange]", "sector": "[Sector]",
        "industry": "[Industry]", "currency": "USD", "as_of": None, "downloaded_at": None,
        "method": v.get("method") or "two_stage", "sources": dict.fromkeys(("P0", "D0", "beta", "rf10", "erp", "forward_eps"), "n/a"),
        "k_grid": [None] * n_grid, "g_grid": [None] * n_grid, "grid": [[None] * n_grid for _ in range(n_grid)],
        "peers": [{"ticker": "[PEER]", "name": "[Peer name]", "market_cap": None, **dict.fromkeys(m[0] for m in MULTIPLES)} for _ in range(n_peers)],
        "comps": {m[0]: dict.fromkeys(("n", "mean", "median", "min", "max", "q1", "q3", "price_mean", "price_median", "price_min",
                                       "price_max", "own")) for m in MULTIPLES},
        "comps_primary": v.get("comps_primary") or ["forward_pe", "ev_ebitda"], "comps_stat": v.get("comps_stat") or "median",
        "fy_labels": ["[FY]"] * n_years, "metrics": {m[0]: [None] * n_years for m in TRAP_METRICS},
        "peer_median": {m[0]: [None] * n_years for m in TRAP_METRICS}, "fcf": [None] * n_years, "payout_cash": [None] * n_years,
        "trap": {m[0]: {"value": None, "peer": None, "own": None, "better_than_peers": None, "improving": None, "red_flag": False}
                 for m in TRAP_METRICS},
        "red_flags": [], "earnings_falling": False, "trap_verdict": "n/a", "signal": "[Decision]", "flags": [], "flags_report": [],
    })
    return fig


def placeholder_pages(slot, first, total, template=None):
    """The two pages of an empty stock slot: the stock layout, the blank YAML's [TO FILL] text, a dash for every number."""
    cfg = yaml.safe_load((template or INPUTS / "_TEMPLATE.yaml").read_text(encoding="utf-8")) or {}
    cfg["pages"] = {"first": first, "total": total}
    for c in cfg.get("catalysts") or []:
        c["date_label"] = "[date]"                    # not the blank's example date
    b = blocks(cfg, placeholder_fig(f"STOCK {slot}", cfg))
    b = {k: re.sub(r"\bn/[am]\b(?!:)", "—", s) for k, s in b.items()}   # keeps the "n/m: negative or above 100x" note
    return Template(SHELL.read_text(encoding="utf-8")).substitute(b)


# ---------------------------------------------------------------- output

def run_chrome(args, timeout=90):
    return subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=20000", *args],
                          capture_output=True, text=True, timeout=timeout)


def check_overflow(html_path):
    """Pages are fixed, so what does not fit is clipped. Ask Chrome where each page's footer ends."""
    r = run_chrome(["--dump-dom", html_path.as_uri()])
    found = re.search(r'data-overflow="([^"]*)"', r.stdout)
    if not found:
        return None
    return json.loads(html.unescape(found.group(1)))


def build(ticker, as_of_arg, refresh):
    path = INPUTS / f"{ticker}.yaml"
    if not path.exists():
        raise SystemExit(f"No inputs for {ticker}: copy {INPUTS.name}/_TEMPLATE.yaml to {path.name} and fill it in")
    cfg = yaml.safe_load(path.read_text())
    cfg["ticker"] = ticker
    if len(cfg.get("peers") or []) == 0:
        raise SystemExit("List the 5 or 6 peers in the YAML")

    snap = load_or_download(cfg, as_of_arg, refresh)
    fig = analyse(cfg, snap)
    page = Template(SHELL.read_text()).substitute(blocks(cfg, fig))

    run = RUNS / fig["as_of"]                   # the run folder: the as-of date of the prices
    run.mkdir(parents=True, exist_ok=True)
    out_html, out_pdf, out_json = run / f"{ticker}.dc.html", run / f"{ticker}.pdf", run / f"{ticker}_figures.json"
    (run / f"{ticker}.yaml").write_bytes(path.read_bytes())   # the inputs this run used
    out_html.write_text(page)
    out_json.write_text(json.dumps(fig, indent=1, default=str))

    layout = check_overflow(out_html)
    clipped = [p for p in (layout or []) if p["overflow"] > 0]
    if layout is None:
        print("WARNING: could not measure the layout; check the PDF by eye")
    r = run_chrome([f"--print-to-pdf={out_pdf}", out_html.as_uri()])
    if not out_pdf.exists():
        raise SystemExit(f"PDF export failed: {r.stderr[-400:]}")

    print(f"\n{fig['name']} ({ticker}), price {fig['P0']:.2f} on {fig['as_of']}")
    print(f"  k {fig['k']:.2%}  DDM {num(fig['V_ddm'])}  comps {num(fig['V_comp'])}  fair value {fig['V0']:.2f}  MoS {fig['mos']:+.1%}")
    print(f"  alpha {fig['alpha']:+.1%}  IR {fig['ir']:.2f}  beta_S {fig['beta_S']:.2f}  sigma2(eps) {fig['sigma2_eps']:.4f}")
    print(f"  value-trap check: {fig['trap_verdict']}  red flags: {', '.join(fig['red_flags']) or 'none'}")
    for x in fig["flags"]:
        print(f"  FLAG: {x}")
    for p in layout or []:
        print(f"  page '{p['label']}': free space {p['free']}px, overflow {p['overflow']}px")
    print(f"  wrote {out_pdf.name}")
    if clipped:
        raise SystemExit("Too long: " + "; ".join(f"{p['label']} runs {p['overflow']}px past the bottom margin" for p in clipped) + ". Shorten the YAML text.")


# ---------------------------------------------------------------- self test

def selftest():
    """Reproduce the numbers printed in the TA's notebook and cheat sheet."""
    ok = True

    def close_to(name, got, want, tol):
        nonlocal ok
        good = abs(got - want) <= tol
        ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {name}: {got:.4f} (TA: {want})")

    print("Valuation, notebook §4 and §5 (inputs as printed)")
    rf, erp = 0.05, 0.06114
    for s, b, D0, g1, g2, vg, v2 in [("NKE", 1.0369, 1.64, 0.10, 0.04, 23.2381, 29.7820), ("HD", 0.9557, 9.29, 0.06, 0.04, 141.1813, 153.6208),
                                     ("GIS", 0.0102, 2.44, 0.02, 0.02, 81.2631, None)]:
        k = rf + b * erp
        close_to(f"{s} Gordon", gordon(D0, k, g2), vg, 0.05)
        if v2:
            close_to(f"{s} two-stage", two_stage(D0, k, g1, g2, 5), v2, 0.05)
    k_gis = rf + 0.0102 * erp
    close_to("GIS alpha never", alpha_never(2.44, 33.215, 0.02, k_gis), 0.0443, 0.0002)
    close_to("GIS alpha closed", alpha_closed(81.2631, 33.215, k_gis), 1.5198, 0.002)
    close_to("NKE alpha closed", alpha_closed(29.7820, 37.545, rf + 1.0369 * erp), -0.2302, 0.002)

    print("Cheat sheet, Nike worked example (k = 11.30%)")
    close_to("Gordon", gordon(1.64, 0.1130, 0.04), 23.36, 0.01)
    close_to("Two-stage", two_stage(1.64, 0.1130, 0.10, 0.04, 5), 29.95, 0.01)

    print("Value-trap table, notebook Checkpoint 2 (GIS vs KHC, CAG, CPB, TA's CSV)")
    fund = pd.read_csv(TA / "r2_fundamentals.csv", index_col=[0, 1], parse_dates=["Date"])
    vt = trap_table(metrics(fund.loc["GIS"]), [metrics(fund.loc[p]) for p in ("KHC", "CAG", "CPB")])
    want = {"ROE": (-0.01, -0.14, 0.25), "FCF margin": (0.09, 0.09, 0.12), "revenue growth": (-0.05, -0.03, -0.02),
            "gross margin": (0.34, 0.28, 0.34), "debt / equity": (1.89, 1.14, 1.41), "payout / FCF": (1.12, 0.70, 1.24)}
    for name, (a1, a2, a3) in want.items():
        close_to(f"{name}, GIS", vt.loc[name, "value"], a1, 0.006)
        close_to(f"{name}, peer median", vt.loc[name, "peer"], a2, 0.006)
        close_to(f"{name}, own average", vt.loc[name, "own"], a3, 0.006)
    ta_flags = {x for x in vt.index[vt["red_flag"]] if x != "ROA"}
    good = ta_flags == {"revenue growth", "debt / equity"}
    ok &= good
    print(f"  {'ok  ' if good else 'FAIL'} red flags, TA's six metrics: {sorted(ta_flags)} (TA: debt / equity, revenue growth)")
    verdict = trap_verdict(list(vt.index[vt["red_flag"]]), 3.15 < 3.55)
    ok &= verdict == "Fail"
    print(f"  {'ok  ' if verdict == 'Fail' else 'FAIL'} GIS verdict: {verdict} (TA: value-trap risk)")

    print("Index model on the TA's SAA and the TA's CSV (notebook §6; its data ended on 28 Oct, the CSV one day later)")
    W = pd.Series({"SPY": 0.086, "EFA": 0.074, "EEM": 0.070, "IEF": 0.177, "LQD": 0.124, "TIP": 0.200, "GLD": 0.097, "DBC": 0.159})
    px = pd.read_csv(TA / "r2_adj_prices.csv", index_col=0, parse_dates=True)
    rates = pd.read_csv(TA / "r2_rates.csv", index_col=0, parse_dates=True) / 100
    R = px.ffill().resample("ME").last().pct_change().dropna()
    rf_m = (rates["DGS1MO"] / 12).resample("ME").last().reindex(R.index).ffill()
    est = R.sub(rf_m, axis=0).iloc[-WINDOW:]
    R_S = est[list(W.index)] @ W
    for s, b, s2 in [("NKE", 1.9897, 0.0734), ("HD", 1.5049, 0.0468), ("GIS", 0.4700, 0.0443)]:
        got_b, got_s2 = regress_on_saa(est[s], R_S)
        close_to(f"{s} beta on SAA", got_b, b, 0.03)
        close_to(f"{s} sigma2(eps)", got_s2, s2, 0.002)

    print("\nAll checks passed." if ok else "\nSOME CHECKS FAILED.")
    return ok


def main():
    ap = argparse.ArgumentParser(description="Build the Round 2 stock report for one ticker.")
    ap.add_argument("ticker", nargs="?", help="Ticker with a YAML file in runs/round2/inputs/")
    ap.add_argument("--as-of", help="Price date, YYYY-MM-DD. The final reports use 2026-11-06. Default: latest close")
    ap.add_argument("--refresh", action="store_true", help="Download again even if a saved snapshot exists")
    ap.add_argument("--selftest", action="store_true", help="Check the formulas against the TA's numbers")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    if not args.ticker:
        ap.error("give a ticker, or --selftest")
    build(args.ticker.upper(), args.as_of, args.refresh)


if __name__ == "__main__":
    main()
