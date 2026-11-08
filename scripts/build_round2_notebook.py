#!/usr/bin/env python3
"""Build and run the Round 2 calculations notebook for the TA: report/Matterhorn_Round2_Calculations.ipynb.

    python scripts/build_round2_notebook.py

The notebook recomputes, step by step, every number of the Round 2 report that comes from Python and is not in
DDM_valuation.xlsx: the Round 1 performance, the index model on the SAA (beta_S, sigma2(eps), IR), the value-trap
check, Treynor-Black and the trades. It carries its own data (the inputs our scripts used, from runs/round2/2026-11-06/),
so it runs offline with pandas and numpy only, and every result is checked against the number in the report.

Reads   data/holdings.json                                   Round 1 shares, cash, SAA weights, dividends from PRTU
        runs/round2/2026-11-06/round1_prices.json            Round 1 closes and the dividends reinvested (Yahoo + PRTU)
        runs/round2/2026-11-06/fred_DGS1MO.csv               1-month T-bill for the Round 1 Sharpe Ratio (FRED)
        runs/round2/2026-11-06/<T>_data.json, <T>_figures.json   each stock's download and the report's numbers
        runs/round2/2026-11-06/round1_performance.json, portfolio.json   the report's numbers, to check against
        runs/round2/inputs/portfolio.yaml                    the stocks and the TE target
Writes  report/Matterhorn_Round2_Calculations.ipynb, executed (outputs saved)
"""

import base64
import gzip
import json
import sys
from pathlib import Path

import nbformat
import pandas as pd
import yaml
from nbclient import NotebookClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_stock_report as bsr                                  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
AS_OF = "2026-11-06"
RUN = REPO / "runs" / "round2" / AS_OF
OUT = REPO / "report" / "Matterhorn_Round2_Calculations.ipynb"
GITHUB = "https://github.com/Baumender2026/Matterhorn-Capital-Management"
TRAP_ITEMS = ["Total Revenue", "Gross Profit", "Net Income", "Stockholders Equity", "Total Assets", "Total Debt",
              "Free Cash Flow", "Cash Dividends Paid", "Repurchase Of Capital Stock"]


def series(s, digits=None):
    s = s.dropna()
    return {d.strftime("%Y-%m-%d"): (round(float(v), digits) if digits else float(v)) for d, v in s.items()}


def collect():
    holdings = json.loads((REPO / "data" / "holdings.json").read_text())
    r1 = holdings["rounds"][0]
    prices = json.loads((RUN / "round1_prices.json").read_text())
    fred = pd.read_csv(RUN / "fred_DGS1MO.csv")
    pf_cfg = yaml.safe_load((REPO / "runs" / "round2" / "inputs" / "portfolio.yaml").read_text())
    stocks = [str(t) for t in pf_cfg["stocks"]]
    perf = json.loads((RUN / "round1_performance.json").read_text())
    pf = json.loads((RUN / "portfolio.json").read_text())
    saa = {h["ticker"]: h["target_weight"] for h in r1["holdings"] if h["target_weight"] > 0}

    data = {
        "about": {
            "as_of": AS_OF,
            "round1": "Yahoo Finance closes (not adjusted) of the Round 1 ETFs, 16 Oct - 6 Nov 2026, and the dividends "
                      "reinvested: Yahoo, plus BND, BNDX and TIP of 2 Nov 2026 from Bloomberg PRTU (8 Nov 2026). "
                      "1-month T-bill: FRED DGS1MO, downloaded 8 Nov 2026.",
            "stocks": "Yahoo Finance, downloaded 8 Nov 2026 (see downloaded_at): month-end adjusted closes of the stock, "
                      "SPY and the SAA ETFs; annual statements of the stock and its peers; EPS estimates. FRED DGS1MO "
                      "(1-month T-bill) and the DDM inputs of DDM_valuation.xlsx (sheet of each stock).",
        },
        "round1": {"start": r1["start_date"], "end": AS_OF, "cash": r1["cash"],
                   "holdings": [{k: h[k] for k in ("ticker", "name", "asset_class", "shares", "target_weight")}
                                for h in r1["holdings"]],
                   "close": prices["close"], "dividends": prices["dividends"],
                   "rf_DGS1MO": {d: float(v) for d, v in zip(fred["observation_date"], pd.to_numeric(fred["DGS1MO"], errors="coerce"))
                                 if pd.notna(v)}},
        "saa_weights": saa, "stocks": {}, "te_target": pf_cfg["te_target"], "te_floor": 0.02,
        "report": {"round1": {"metrics": perf["metrics"], "nav_end": perf["nav_end"], "positions": perf["positions"],
                              "trading_days": perf["trading_days"]},
                   "portfolio": {k: pf[k] for k in ("nav", "active", "risk", "stocks", "etfs", "cash")}, "stocks": {}},
    }
    rf_ref = None
    for t in stocks:
        snap = json.loads((RUN / f"{t}_data.json").read_text())
        fig = json.loads((RUN / f"{t}_figures.json").read_text())
        adj = bsr.frame(snap["adj"]).loc[:AS_OF].ffill()
        cols = [t, "SPY", *saa]
        month_end = adj[cols].resample("ME").last()
        month_end = month_end.loc[:bsr.complete_month_end(pd.Timestamp(AS_OF))]
        rates = bsr.frame(snap["rates"]).loc[:AS_OF]
        rf_daily = rates["DGS1MO"].ffill()
        if rf_ref is None:
            rf_ref = rf_daily
        elif not rf_daily.equals(rf_ref):
            raise SystemExit(f"{t}: its DGS1MO series differs from {stocks[0]}'s; store one per stock")
        firms = [t, *snap["peers"]]
        data["stocks"][t] = {
            "name": fig["name"], "downloaded_at": snap["downloaded_at"], "peers": snap["peers"],
            "ddm": {k: fig[k] for k in ("P0", "D0", "D0_div", "basis", "beta", "rf10", "erp", "g1", "T", "g2", "method", "V_comp")},
            "probability_gap_closes": fig["probability"],
            "month_end_adj": {c: series(month_end[c]) for c in cols},
            "statements": {f: {i: v for i, v in snap["statements"][f].items() if i in TRAP_ITEMS} for f in firms},
            "estimates": {"eps_ago": snap["estimates"]["eps_ago"], "eps_cur": snap["estimates"]["eps_cur"],
                          "eps_fwd": fig["eps_fwd"], "eps_ttm": fig["eps_ttm"]},
        }
        data["report"]["stocks"][t] = {k: fig[k] for k in (
            "beta_S", "sigma2_eps", "alpha", "alpha_closed", "alpha_never", "ir", "ir_never", "V0", "V_gordon", "V_2stage",
            "V_ddm_beta1", "mos", "k", "trap", "red_flags", "trap_verdict", "earnings_falling", "saa_excess", "saa_vol",
            "fy_labels", "window")}
    data["rf_DGS1MO_daily"] = series(rf_ref)
    return data, stocks


def md(s):
    return nbformat.v4.new_markdown_cell(s.strip())


def code(s):
    return nbformat.v4.new_code_cell(s.strip())


def cells(data, stocks):
    blob = base64.b64encode(gzip.compress(json.dumps(data, separators=(",", ":")).encode(), 9)).decode()
    p, perf = data["report"]["portfolio"], data["report"]["round1"]["metrics"]
    a = p["active"]
    weights = ", ".join(f"{s['ticker']} {s['weight_total']:.2%}" for s in p["stocks"])
    return [
        md(f"""
# Matterhorn Capital Management · AMC 2026 Round 2 · Group 3
## The calculations behind the report

This notebook goes with **Matterhorn_Round2_Equity.pdf** and **DDM_valuation_submission.xlsx**. The workbook already
holds the dividend discount models, the comparables, the margins of safety and the alphas. This notebook recomputes,
step by step, **the numbers of the report that come from Python and are not in the workbook**, and checks each one
against the number printed in the report.

| Report | Section here | What is computed |
|---|---|---|
| pp. 2–3, Round 1 | 1 | NAV with dividends reinvested, return, realised volatility, Sharpe Ratio, maximum drawdown, ex-ante volatility, 1-month 5% VaR, the attribution table |
| stock pages, section 5 | 2 | Index model on our SAA: β<sub>S</sub>, σ²(ε), the alphas and the IR; the DDM at the workbook's inputs |
| stock pages, section 4 | 3 | Value-trap check: seven metrics against the peer median and the stock's own past, red flags, earnings test |
| p. 12 | 4 | Treynor-Black: weights in the active portfolio A, w<sub>A</sub>*, the tracking-error budget, the trades entered in PRTU, ex-ante TE, volatility and VaR |
| — | 5 | Every check in one table |

**Results in brief** (price date: close of Friday 6 November 2026)

* Round 1: return {perf['total_return']:+.2%}, realised volatility {perf['realised_vol']:.2%} and Sharpe Ratio {perf['sharpe']:.2f}
  (15 daily returns only), maximum drawdown {perf['max_drawdown']:.2%}, ex-ante volatility {perf['ex_ante_vol']:.2%}.
* Treynor-Black: w<sub>A</sub>* = {a['w_A_star']:.1%} is far too large; the 2.5% tracking-error target caps the active
  portfolio at w<sub>A</sub> = {a['w_A']:.2%} of the fund. Stocks: {weights}.
* Ex-ante tracking error against the SAA {p['risk']['te']:.2%} (budget 2–5%), volatility {p['risk']['vol_new']:.2%},
  1-month 5% VaR {p['risk']['var_new']:.2%}.

**How to run it.** Python 3 with `pandas` and `numpy` (`pip install pandas numpy`), then *Run All*. No internet and
no other file are needed: the data are inside the notebook (section 0). The last section shows how the data were
downloaded and the commands that produced the report, from our repository ({GITHUB}).
"""),
        md("""
## 0 · Data

The inputs our scripts used, saved when the report was built, are packed in the next cell (compressed JSON) so the
results are exactly the report's. Sources: Yahoo Finance (prices, statements, estimates), FRED DGS1MO (1-month T-bill),
Bloomberg PRTU (three ETF dividends of 2 November that Yahoo did not have yet), and the DDM inputs of the workbook.
"""),
        code(f'''
import base64, gzip, json, math
import numpy as np
import pandas as pd
pd.set_option("display.width", 160)

DATA = json.loads(gzip.decompress(base64.b64decode("{blob}")))
REPORT = DATA["report"]
STOCKS = list(DATA["stocks"])
W = pd.Series(DATA["saa_weights"])          # the SAA: Round 1 target weights (the passive portfolio and the benchmark)
TRADING_DAYS, Z_95 = 252, 1.645

CHECKS = []
def check(section, item, ours, report, tol):
    """Our number against the report's: ok if they differ by less than tol."""
    ok = (ours == report) if isinstance(report, (str, bool)) else abs(ours - report) <= tol
    CHECKS.append({{"section": section, "item": item, "notebook": ours, "report": report, "ok": ok}})
    return ok

def frame(records):
    df = pd.DataFrame({{c: pd.Series(v, dtype=float) for c, v in records.items()}})
    df.index = pd.to_datetime(df.index)
    return df.sort_index()

for k, v in DATA["about"].items():
    print(f"{{k}}: {{v}}")
print("SAA weights:", W.round(4).to_dict())
'''),
        md("""
## 1 · Round 1 performance (report pp. 2–3)

The Round 1 portfolio from the close of 16 October 2026 to the close of 6 November 2026. Shares are those entered in
Bloomberg PRTU. On an ex-date, a dividend buys more of the ETF that pays it at the previous close, as PRTU reinvests
cash dividends:  units<sub>t</sub> = units<sub>t−1</sub> × (1 + D<sub>t</sub> / P<sub>t−1</sub>).  NAV = cash + Σ units × close.
"""),
        code('''
r1 = DATA["round1"]
tickers = [h["ticker"] for h in r1["holdings"]]
close = frame(r1["close"])[tickers]
div = frame(r1["dividends"]).reindex(index=close.index, columns=tickers).fillna(0.0)
shares = pd.Series({h["ticker"]: float(h["shares"]) for h in r1["holdings"]})

units = shares * (1 + (div / close.shift(1)).fillna(0.0)).cumprod()
mv = close * units
nav = r1["cash"] + mv.sum(axis=1)
daily = nav.pct_change().iloc[1:]

total_return = nav.iloc[-1] / nav.iloc[0] - 1
vol = daily.std(ddof=1) * math.sqrt(TRADING_DAYS)                      # realised, annualised
rf = pd.Series(r1["rf_DGS1MO"]); rf.index = pd.to_datetime(rf.index)
rf_d = rf.reindex(rf.index.union(daily.index)).ffill().reindex(daily.index) / 100 / TRADING_DAYS
excess = daily - rf_d
sharpe = excess.mean() / excess.std(ddof=1) * math.sqrt(TRADING_DAYS)   # on daily excess returns, annualised
index = 100 * nav / nav.iloc[0]
drawdown = index / index.cummax() - 1
trough = drawdown.idxmin(); peak = index.loc[:trough].idxmax()

print(pd.DataFrame({"NAV, USD": nav.map("{:,.2f}".format), "index": index.round(3),
                    "daily return": daily.map("{:+.4%}".format)}).fillna("").to_string())
print(f"\\n{len(daily)} daily returns")
print(f"Return {total_return:+.2%}   realised volatility {vol:.2%}   Sharpe Ratio {sharpe:.2f}   "
      f"max drawdown {drawdown.min():.2%} ({peak:%d.%m} → {trough:%d.%m})")

m = REPORT["round1"]["metrics"]
check("1 Round 1", "NAV, 6 Nov (USD)", round(nav.iloc[-1], 2), REPORT["round1"]["nav_end"], 0.005)
check("1 Round 1", "Return", total_return, m["total_return"], 5e-9)
check("1 Round 1", "Realised volatility", vol, m["realised_vol"], 5e-9)
check("1 Round 1", "Sharpe Ratio", sharpe, m["sharpe"], 5e-8)
_ = check("1 Round 1", "Maximum drawdown", drawdown.min(), m["max_drawdown"], 5e-9)
'''),
        md("""
**Ex-ante risk.** σ = √(w′Vw), with V = 12 × the covariance of the last 60 complete monthly returns (Nov 2021 – Oct 2026,
adjusted closes) and w the weights on 6 November. 1-month 5% VaR = 1.645 × σ / √12. Risk contribution of asset i:
w<sub>i</sub>(Vw)<sub>i</sub> / w′Vw. BIL, the cash leg, has no shares, so weight 0.

The adjusted closes here are from the stock downloads of 8 November; the report's Round 1 run downloaded them about an
hour later. Yahoo revises adjusted prices slightly between downloads, so these figures match the report to the
precision it prints (0.01% for volatility and VaR, 0.1% for risk contributions), not to the last digit.
"""),
        code('''
w_now = mv.iloc[-1] / nav.iloc[-1]
etfs = [t for t in tickers if w_now[t] > 0]
px_m = frame(DATA["stocks"][STOCKS[0]]["month_end_adj"])[etfs]
rets = px_m.pct_change().iloc[1:].dropna().tail(60)
V = 12 * rets.cov().values
w = w_now[etfs].values
sigma = math.sqrt(w @ V @ w)
var_1m = Z_95 * sigma / math.sqrt(12)
rc = pd.Series(w * (V @ w) / (w @ V @ w), index=etfs).reindex(tickers).fillna(0.0)
print(f"Window {rets.index[0]:%b %Y} – {rets.index[-1]:%b %Y} ({len(rets)} months)")
print(f"Ex-ante volatility {sigma:.2%}   1-month 5% VaR {var_1m:.2%} = USD {var_1m * nav.iloc[-1]:,.0f}")

check("1 Round 1", "Ex-ante volatility (0.01%)", round(sigma * 100, 2), round(m["ex_ante_vol"] * 100, 2), 0)
check("1 Round 1", "1-month 5% VaR (0.01%)", round(var_1m * 100, 2), round(m["var_1m_95_pct"] * 100, 2), 0)

# Table 2: positions and contribution to the return
h = pd.DataFrame(r1["holdings"]).set_index("ticker")
t2 = pd.DataFrame({
    "class": h["asset_class"], "shares, start": shares, "shares, now": units.iloc[-1].round(2),
    "price 16.10": close.iloc[0], "price 06.11": close.iloc[-1],
    "weight, start": mv.iloc[0] / nav.iloc[0], "weight, now": w_now,
    "return": (mv.iloc[-1] / mv.iloc[0] - 1).where(mv.iloc[0] > 0),
    "contribution": (mv.iloc[-1] - mv.iloc[0]) / nav.iloc[0],          # adds up to the portfolio's return
    "risk contr.": rc})
print(t2.round(4).to_string())
print(f"\\nSum of the contributions {t2['contribution'].sum():+.4%} = return {total_return:+.4%}")
print(t2.groupby("class")[["weight, start", "weight, now", "contribution", "risk contr."]].sum().round(4).to_string())
for p in REPORT["round1"]["positions"]:
    t = p["ticker"]
    check("1 Round 1", f"{t} contribution", t2.loc[t, "contribution"], p["contribution"], 5e-9)
    check("1 Round 1", f"{t} risk contribution (0.1%)", round(rc[t] * 100, 1), round(p["risk_contribution"] * 100, 1), 0)
'''),
        md("""
## 2 · Index model on our SAA, alphas and IR (stock pages, section 5)

As in the TA's notebook (§6), with our SAA as the passive portfolio S: monthly excess returns over the 1-month T-bill
(FRED DGS1MO, daily rates averaged by month), last 60 complete months. For each stock i:
R<sub>i</sub><sup>e</sup> = a + β<sub>S</sub> R<sub>S</sub><sup>e</sup> + ε,  σ²(ε) = 12 × var(ε).

The DDM inputs are the workbook's (sheet of each stock): k = r<sub>f</sub> + β × ERP, value by the two-stage model or
Gordon. Alphas (Round 2 cheat sheet): α<sub>closed</sub> = (1 + k)(V<sub>0</sub> − P<sub>0</sub>) / P<sub>0</sub> if the gap
closes within a year, α<sub>never</sub> = D<sub>1</sub> / P<sub>0</sub> + g − k if it never closes. IR = α / σ(ε).
"""),
        code('''
def gordon(D0, k, g):
    return D0 * (1 + g) / (k - g)

def two_stage(D0, k, g1, g2, T):
    t = np.arange(1, int(T) + 1)
    D = D0 * (1 + g1) ** t
    return float((D / (1 + k) ** t).sum() + D[-1] * (1 + g2) / (k - g2) / (1 + k) ** T)

rf_m_daily = pd.Series(DATA["rf_DGS1MO_daily"]); rf_m_daily.index = pd.to_datetime(rf_m_daily.index)
rf_month = (rf_m_daily / 100 / 12).resample("ME").mean()

EST, ROWS = {}, []
for t in STOCKS:
    s = DATA["stocks"][t]
    R = frame(s["month_end_adj"]).pct_change()
    Re = R.sub(rf_month.reindex(R.index).ffill(), axis=0)
    est = Re.dropna(subset=[t, "SPY", *W.index]).iloc[-60:]
    EST[t] = est
    R_S = est[list(W.index)] @ W
    beta_S, a = np.polyfit(R_S, est[t], 1)
    s2_eps = float((est[t] - (a + beta_S * R_S)).var() * 12)

    d = s["ddm"]
    k = d["rf10"] + d["beta"] * d["erp"]
    value = (lambda kk: two_stage(d["D0"], kk, d["g1"], d["g2"], d["T"])) if d["method"] == "two_stage" \\
        else (lambda kk: gordon(d["D0"], kk, d["g2"]))
    V0 = value(k)
    a_closed = (1 + k) * (V0 - d["P0"]) / d["P0"]
    a_never = d["D0"] * (1 + d["g2"]) / d["P0"] + d["g2"] - k
    p = s["probability_gap_closes"]                       # 1: the team assumes the gap closes within a year
    alpha = p * a_closed + (1 - p) * a_never
    ir = alpha / math.sqrt(s2_eps)
    ROWS.append({"stock": t, "β (DDM)": d["beta"], "k": k, "V0": V0, "P0": d["P0"], "MoS": V0 / d["P0"] - 1,
                 "V0 at β = 1": value(d["rf10"] + d["erp"]), "β_S": beta_S, "σ²(ε)": s2_eps,
                 "α closed": a_closed, "α never": a_never, "α used": alpha, "IR": ir,
                 "IR never": a_never / math.sqrt(s2_eps), "μ_S": R_S.mean() * 12, "σ_S": R_S.std() * math.sqrt(12)})
    f = REPORT["stocks"][t]
    for item, ours, rep, tol in [("β_S", beta_S, f["beta_S"], 1e-9), ("σ²(ε)", s2_eps, f["sigma2_eps"], 1e-11),
                                 ("k", k, f["k"], 1e-12), ("V0", V0, f["V0"], 1e-9), ("MoS", V0 / d["P0"] - 1, f["mos"], 1e-12),
                                 ("V0 at β = 1", value(d["rf10"] + d["erp"]), f["V_ddm_beta1"], 1e-9),
                                 ("α closed", a_closed, f["alpha_closed"], 1e-12), ("α never", a_never, f["alpha_never"], 1e-12),
                                 ("α used", alpha, f["alpha"], 1e-12), ("IR", ir, f["ir"], 1e-9), ("IR never", a_never / math.sqrt(s2_eps), f["ir_never"], 1e-9),
                                 ("SAA E(R^e)", R_S.mean() * 12, f["saa_excess"], 1e-12), ("SAA σ", R_S.std() * math.sqrt(12), f["saa_vol"], 1e-12)]:
        check("2 Index model", f"{t} {item}", ours, rep, tol)

print(f"Window {est.index[0]:%b %Y} – {est.index[-1]:%b %Y}, {len(est)} months")
pd.DataFrame(ROWS).set_index("stock").T.round(4)
'''),
        md("""
## 3 · Value-trap check (stock pages, section 4)

From the annual statements (Yahoo), as in the TA's Checkpoint 2: ROE, ROA, FCF margin, revenue growth, gross margin,
debt / equity and payout / FCF (payout = dividends + buybacks). The last fiscal year is compared with the peer median
(the same six peers as the comparables) and with the stock's own average of the earlier years. A **red flag** is a
metric worse than the peers *and* worse than its own past. Earnings test: forward EPS against last year's adjusted EPS.
Verdict: red flags and falling earnings = value trap; one of the two = watch; neither = pass.
"""),
        code('''
HIGH_IS_GOOD = {"ROE": True, "ROA": True, "FCF margin": True, "revenue growth": True, "gross margin": True,
                "debt / equity": False, "payout / FCF": False}

ITEMS = ["Total Revenue", "Gross Profit", "Net Income", "Stockholders Equity", "Total Assets", "Total Debt",
         "Free Cash Flow", "Cash Dividends Paid", "Repurchase Of Capital Stock"]

def metrics(st):
    f = frame(st).reindex(columns=ITEMS).dropna(subset=["Total Revenue"])
    eq = f["Stockholders Equity"].where(f["Stockholders Equity"] > 0)       # negative equity: ROE and D/E meaningless
    rev = f["Total Revenue"]
    payout = -(f["Cash Dividends Paid"].fillna(0) + f["Repurchase Of Capital Stock"].fillna(0))   # dividends + buybacks
    return pd.DataFrame({"ROE": f["Net Income"] / eq, "ROA": f["Net Income"] / f["Total Assets"],
                         "FCF margin": f["Free Cash Flow"] / rev, "revenue growth": rev / rev.shift(1) - 1,
                         "gross margin": f["Gross Profit"] / rev, "debt / equity": f["Total Debt"] / eq,
                         "payout / FCF": payout / f["Free Cash Flow"]})

for t in STOCKS:
    s, f = DATA["stocks"][t], REPORT["stocks"][t]
    m = metrics(s["statements"][t])
    peers = [metrics(s["statements"][p]) for p in s["peers"]]
    vt = pd.DataFrame({"value": m.iloc[-1], "peer median": pd.concat([x.iloc[-1] for x in peers], axis=1).median(axis=1),
                       "own past avg.": m.iloc[:-1].mean()})
    high = pd.Series(HIGH_IS_GOOD)
    better = lambda a, b: ((a > b) == high).where(a.notna() & b.notna())
    vt["vs peers"] = better(vt["value"], vt["peer median"]).map({True: "better", False: "worse"}).fillna("n/a")
    vt["trend"] = better(vt["value"], vt["own past avg."]).map({True: "improving", False: "worsening"}).fillna("n/a")
    vt["red flag"] = (vt["vs peers"] == "worse") & (vt["trend"] == "worsening")
    e = s["estimates"]
    falling = e["eps_fwd"] < e["eps_ago"]
    red = list(vt.index[vt["red flag"]])
    verdict = "Fail" if red and falling else "Watch" if red or falling else "Pass"
    print(f"\\n{t} · {s['name']} · last fiscal year {f['fy_labels'][-1]} · peers {', '.join(s['peers'])}")
    print(vt.round(4).to_string())
    print(f"Earnings test: adjusted EPS {e['eps_ago']:.2f} → {e['eps_cur']:.2f} → {e['eps_fwd']:.2f} (forward): "
          f"{'falling' if falling else 'rising'}. Trailing GAAP EPS {e['eps_ttm']:.2f}.  Red flags: {', '.join(red) or 'none'}.  Verdict: {verdict}")
    for name, row in vt.iterrows():
        for col, key in (("value", "value"), ("peer median", "peer"), ("own past avg.", "own")):
            rep = f["trap"][name][key]
            if rep is not None and pd.notna(row[col]):
                check("3 Value trap", f"{t} {name}, {col}", row[col], rep, 1e-12)
    check("3 Value trap", f"{t} red flags", ", ".join(red), ", ".join(f["red_flags"]), 0)
    check("3 Value trap", f"{t} verdict", verdict, f["trap_verdict"], 0)
'''),
        md("""
## 4 · Treynor-Black and the new portfolio (report p. 12)

The steps of the TA's notebook (§7–§10, Class 3 Part II):

* Weights inside the active portfolio A: w<sub>i</sub> ∝ α<sub>i</sub> / σ²(ε<sub>i</sub>). Then α<sub>A</sub>, β<sub>A</sub>, σ²(ε<sub>A</sub>) = Σ w<sub>i</sub>² σ²(ε<sub>i</sub>).
* Optimal size: w<sub>A0</sub> = [α<sub>A</sub> / σ²(ε<sub>A</sub>)] / [E(R<sub>S</sub><sup>e</sup>) / σ<sub>S</sub>²], w<sub>A</sub>* = w<sub>A0</sub> / (1 + (1 − β<sub>A</sub>) w<sub>A0</sub>).
* The SAA is the benchmark: the new portfolio is (1 − w<sub>A</sub>) SAA + w<sub>A</sub> A, so TE = w<sub>A</sub> × sd(R<sub>A</sub> − R<sub>S</sub>) × √12.
  The budget (2–5%; our target 2.5%) bounds w<sub>A</sub>; w<sub>A</sub>* is pushed inside the bounds.
* Every ETF goes to (1 − w<sub>A</sub>) × its SAA weight, so the SAA mix does not change; each stock to w<sub>A</sub> × w<sub>i</sub>.
  Whole shares, rounded down, at the 6 November close; the rest stays in cash.

Monthly returns: those of section 2 (the SAA ETFs from the first stock's download, each stock from its own).
"""),
        code('''
est = EST[STOCKS[0]].drop(columns=[STOCKS[0]]).copy()
for t in STOCKS:
    est[t] = EST[t][t]
R_S = est[list(W.index)] @ W
mu_S, sigma_S = R_S.mean() * 12, R_S.std() * math.sqrt(12)
res = pd.DataFrame(ROWS).set_index("stock")
alpha, s2 = res["α used"], res["σ²(ε)"]

w_i = (alpha / s2) / (alpha / s2).sum()
alpha_A, beta_A, s2_A = (w_i * alpha).sum(), (w_i * res["β_S"]).sum(), (w_i ** 2 * s2).sum()
w_A0 = (alpha_A / s2_A) / (mu_S / sigma_S ** 2)
w_A_star = w_A0 / (1 + (1 - beta_A) * w_A0)
R_A = est[STOCKS] @ w_i[STOCKS]
te_unit = (R_A - R_S).std() * math.sqrt(12)
w_lo, w_hi = DATA["te_floor"] / te_unit, DATA["te_target"] / te_unit
w_A = min(max(w_A_star, w_lo), w_hi)
R_new = (1 - w_A) * R_S + w_A * R_A
mu_N = mu_S + w_A * (alpha_A + (beta_A - 1) * mu_S)
ir_A, sr_S = alpha_A / math.sqrt(s2_A), mu_S / sigma_S

print(pd.DataFrame({"α": alpha, "σ²(ε)": s2, "α/σ²(ε)": alpha / s2, "IR": res["IR"], "weight in A": w_i,
                    "weight in the portfolio": w_A * w_i}).round(4).to_string())
print(f"\\nActive portfolio A: α_A {alpha_A:+.2%}, β_A {beta_A:.4f}, σ(ε_A) {math.sqrt(s2_A):.4f}, IR_A {ir_A:.2f}")
print(f"SAA: E(R^e) {mu_S:.2%}, σ {sigma_S:.2%}, Sharpe {sr_S:.2f}")
print(f"w_A0 {w_A0:.1%} → w_A* {w_A_star:.1%}.  TE per unit of A {te_unit:.2%}: 2% floor → w_A ≥ {w_lo:.2%}, "
      f"{DATA['te_target']:.1%} target → w_A ≤ {w_hi:.2%}.  w_A = {w_A:.2%}")
print(f"Sharpe at w_A {mu_N / (R_new.std() * math.sqrt(12)):.2f};  at w_A* (eq. 16) {math.sqrt(sr_S ** 2 + ir_A ** 2):.2f}")

A = REPORT["portfolio"]["active"]
for item, ours, key in [("α_A", alpha_A, "alpha_A"), ("β_A", beta_A, "beta_A"), ("σ(ε_A)", math.sqrt(s2_A), "sigma_eps_A"),
                        ("IR_A", ir_A, "ir_A"), ("w_A0", w_A0, "w_A0"), ("w_A*", w_A_star, "w_A_star"),
                        ("TE per unit of A", te_unit, "te_per_unit"), ("w_A, lower bound", w_lo, "w_A_lo"),
                        ("w_A, upper bound", w_hi, "w_A_hi"), ("w_A", w_A, "w_A"), ("Sharpe, SAA", sr_S, "sharpe_saa"),
                        ("Sharpe at w_A", mu_N / (R_new.std() * math.sqrt(12)), "sharpe_at_w_A"),
                        ("Sharpe at w_A*", math.sqrt(sr_S ** 2 + ir_A ** 2), "sharpe_with_active")]:
    check("4 Treynor-Black", item, ours, A[key], 1e-9)
for s in REPORT["portfolio"]["stocks"]:
    check("4 Treynor-Black", f"{s['ticker']} weight in A", w_i[s["ticker"]], s["weight_sleeve_tb"], 1e-12)
'''),
        code('''
# Table 4: the portfolio as entered in Bloomberg PRTU
nav_6nov = round(nav.iloc[-1], 2)
rows = []
for t in tickers:
    target = (1 - w_A) * W.get(t, 0.0)
    after = math.floor(target * nav_6nov / close[t].iloc[-1])
    rows.append({"position": t, "shares before": units[t].iloc[-1], "shares after": after,
                 "trade": after - units[t].iloc[-1], "price": close[t].iloc[-1], "value": after * close[t].iloc[-1]})
for t in STOCKS:
    P0 = DATA["stocks"][t]["ddm"]["P0"]
    after = math.floor(w_A * w_i[t] * nav_6nov / P0)
    rows.append({"position": t, "shares before": 0.0, "shares after": after, "trade": float(after), "price": P0, "value": after * P0})
t4 = pd.DataFrame(rows).set_index("position")
cash = nav_6nov - t4["value"].sum()
t4["weight"] = t4["value"] / nav_6nov
print(t4.to_string(formatters={"shares before": "{:,.2f}".format, "shares after": "{:,.0f}".format, "trade": "{:+,.2f}".format,
                                "price": "{:,.2f}".format, "value": "{:,.2f}".format, "weight": "{:.2%}".format}))
print(f"Cash, rounding leftover USD {cash:,.2f} ({cash / nav_6nov:.2%}).  Total USD {nav_6nov:,.2f}: weights add up to "
      f"{(t4['weight'].sum() + cash / nav_6nov):.2%}")

# Ex-ante risk against the SAA, of the portfolio as entered (cash earns the T-bill: zero excess return)
w_new = t4.loc[t4["weight"] > 0, "weight"]
R_N = est[list(w_new.index)] @ w_new
te, vol_N = (R_N - R_S).std() * math.sqrt(12), R_N.std() * math.sqrt(12)
print(f"Ex-ante TE vs SAA {te:.2%}  volatility {vol_N:.2%} (SAA {sigma_S:.2%})  1-month 5% VaR {Z_95 * vol_N / math.sqrt(12):.2%} "
      f"(SAA {Z_95 * sigma_S / math.sqrt(12):.2%})")

P = REPORT["portfolio"]
for e in P["etfs"] + P["stocks"]:
    t = e["ticker"]
    check("4 Portfolio", f"{t} shares", t4.loc[t, "shares after"], e.get("shares_after", e.get("shares")), 0)
check("4 Portfolio", "Cash (USD)", cash, P["cash"]["usd"], 1e-6)
for item, ours, key in [("Ex-ante TE", te, "te"), ("Ex-ante volatility", vol_N, "vol_new"),
                        ("1-month 5% VaR", Z_95 * vol_N / math.sqrt(12), "var_new"), ("SAA volatility", sigma_S, "vol_saa")]:
    check("4 Portfolio", item, ours, P["risk"][key], 1e-12)
'''),
        md("""
## 5 · Every check

Each number above against the one in the report (the report's `figures` files). `ok` means the two agree within the
tolerance shown in the code: rounding error for the computed numbers, the printed precision for the Round 1 ex-ante risk.
"""),
        code('''
pd.set_option("display.max_rows", 300)
checks = pd.DataFrame(CHECKS)
print(f"{checks['ok'].sum()} of {len(checks)} checks agree with the report")
print(checks.groupby("section")["ok"].agg(["sum", "count"]).rename(columns={"sum": "ok", "count": "checks"}).to_string())
assert checks["ok"].all(), checks.loc[~checks["ok"]]
checks
'''),
        md(f"""
## Appendix · How the data were downloaded and the report built

The data in section 0 were downloaded by the scripts of our repository, **{GITHUB}** (folder `scripts/`), and saved in
`runs/round2/2026-11-06/`. The commands, from the repository root:

```bash
pip install -r scripts/requirements.txt
python scripts/build_ddm_workbook.py --as-of 2026-11-06              # the DDM workbook: one sheet per stock (Yahoo, FRED)
python scripts/round1_performance.py --end 2026-11-06                # Round 1 performance, as on our website
python scripts/build_stock_report.py NVDA --as-of 2026-11-06         # each stock's two pages; reads the workbook's inputs
python scripts/build_stock_report.py PEP  --as-of 2026-11-06
python scripts/build_stock_report.py ABBV --as-of 2026-11-06
python scripts/build_stock_report.py DRI  --as-of 2026-11-06
python scripts/build_round2_portfolio.py                             # Treynor-Black and the trades (runs/round2/inputs/portfolio.yaml)
python scripts/promote.py runs/round2/2026-11-06/<file> ...          # copy the outputs used by the report
python scripts/build_round2_report.py --pdf                          # Matterhorn_Round2_Equity.pdf
python scripts/build_round2_notebook.py                              # this notebook
```

To download the raw data again yourself (needs internet and `pip install yfinance`), set `REFRESH = True` in the cell
below. Yahoo revises adjusted prices and statements over time, so a new download can differ slightly from the data
above; the closes of 16 October – 6 November do not change.
"""),
        code('''
REFRESH = False
if REFRESH:
    import yfinance as yf
    px = yf.download(tickers + STOCKS + ["SPY"], start="2019-10-01", end="2026-11-07", auto_adjust=False, progress=False)
    print(px["Close"].loc["2026-10-16":].round(2).tail())
    rf_new = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS1MO")
    print(rf_new.tail())
    print(yf.Ticker("NVDA").income_stmt.loc[["Total Revenue", "Net Income"]])
else:
    print("REFRESH is False: the notebook uses the data saved with the report (section 0).")
'''),
    ]


def main():
    data, stocks = collect()
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.cells = cells(data, stocks)
    NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(REPO)}}).execute()
    OUT.write_text(nbformat.writes(nb))
    print(f"wrote {OUT.relative_to(REPO)} ({OUT.stat().st_size / 1e3:.0f} kB), executed")


if __name__ == "__main__":
    main()
