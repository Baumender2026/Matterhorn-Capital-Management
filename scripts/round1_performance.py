#!/usr/bin/env python3
"""Round 1 results for the Round 2 report: the performance of the Round 1 portfolio from its start to a
date, and what each position contributed. The calculations are the website's (scripts/update_portfolio.py):
same prices (Yahoo closes), dividends reinvested at the close before the ex-date as in Bloomberg PRTU (with the
dividends listed in data/holdings.json that Yahoo does not have yet), same risk model.

    python scripts/round1_performance.py                    up to the latest close: a draft
    python scripts/round1_performance.py --end 2026-11-06   final: the guidelines measure Round 1 to Friday 6 November

Writes runs/round2/<as-of>/round1_performance.json; promote it with scripts/promote.py.
Stops if the numbers do not match data/portfolio.json for the same date, or if the contributions
of the positions do not add up to the return of the portfolio.
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_portfolio as up                                     # noqa: E402

REPO = Path(__file__).resolve().parent.parent
HOLDINGS, SITE = REPO / "data" / "holdings.json", REPO / "data" / "portfolio.json"
RUNS = REPO / "runs" / "round2"
VOL_TARGET, VOL_BAND = 0.08, (0.07, 0.09)                         # Round 1 guidelines, as in the Round 1 report


def r(x, d=8):
    return None if x is None else round(float(x), d)


def compare_with_site(out):
    """The same numbers as the website, when it shows Round 1 on the same date. Index rounding: 1e-5."""
    if not SITE.exists():
        return "not compared: no data/portfolio.json"
    site = json.loads(SITE.read_text(encoding="utf-8"))
    if site.get("status") != "ok" or site.get("as_of") != out["as_of"] or site.get("current_round") != "Round 1":
        return f"not compared: data/portfolio.json is for {site.get('as_of')} ({site.get('current_round')})"
    m, s = out["metrics"], site["metrics"]
    pairs = [("NAV", out["nav_end"], site["nav"], 0.01), ("total return", m["total_return"], s["total_return"], 1e-5),
             ("max drawdown", m["max_drawdown"], s["max_drawdown"], 1e-5), ("ex-ante vol", m["ex_ante_vol"], s["ex_ante_vol"], 1e-6),
             ("VaR", m["var_1m_95_pct"], s["var_1m_95_pct"], 1e-6)]
    if out["trading_days"] >= up.MIN_STATS_DAYS:   # below it the website shows none; the report gives them anyway
        pairs += [("realised vol", m["realised_vol"], s["realised_vol"], 1e-6), ("Sharpe", m["sharpe"], s["sharpe"], 1e-6)]
    bad = [f"{n}: {a} here, {b} on the site" for n, a, b, tol in pairs
           if (a is None) != (b is None) or (a is not None and abs(a - b) > tol)]
    if bad:
        raise SystemExit("Does not match data/portfolio.json for the same date:\n  " + "\n  ".join(bad))
    return "matches data/portfolio.json"


def main():
    ap = argparse.ArgumentParser(description="Round 1 performance and attribution, for the Round 2 report.")
    ap.add_argument("--end", help="Last date, YYYY-MM-DD (final: 2026-11-06). Default: latest close")
    ap.add_argument("--out", help="Output file. Default: runs/round2/<as-of>/round1_performance.json")
    args = ap.parse_args()

    cfg, rounds = up.load_config(HOLDINGS)
    r1 = next(x for x in rounds if x["id"] == "Round 1")
    tickers = [h["ticker"] for h in r1["holdings"]]
    ny_now = datetime.now(ZoneInfo("America/New_York"))
    today = pd.Timestamp(ny_now.date())
    end = pd.Timestamp(args.end) if args.end else today

    start_dl = min(r1["start"], today - pd.DateOffset(years=up.RISK_YEARS)) - pd.Timedelta(days=10)
    close, adj, div = up.download_prices(tickers, start_dl, end + pd.Timedelta(days=1))
    keep = close.index <= end
    if end == today and ny_now.time() < up.CLOSE_CUTOFF:          # before the close, today's bar is intraday
        keep &= close.index < today
    close, adj, div = close[keep], adj[adj.index.isin(close.index)], div[div.index.isin(close.index)]
    as_of = close[[t for t in tickers]].dropna().index.max()
    if args.end and as_of != end:
        print(f"NOTE: no common close on {end.date()}; using {as_of.date()}")

    nav, cash, mv, px, units = up.round_nav(r1, close, div, as_of)
    last = nav.index[-1]
    nav0, nav1 = float(nav.iloc[0]), float(nav.iloc[-1])
    daily = nav.pct_change().iloc[1:]
    index = 100 * nav / nav0
    drawdown = index / index.cummax() - 1
    trough = drawdown.idxmin()
    peak = index.loc[:trough].idxmax()

    n, vol, sharpe, rf_source = len(daily), None, None, None
    if n >= 2:      # the guidelines ask for both; with fewer than the website's MIN_STATS_DAYS the report says how many
        vol = float(daily.std(ddof=1) * math.sqrt(up.TRADING_DAYS))
        rf, rf_source = up.download_rf(range(daily.index[0].year, today.year + 1))
        if rf is not None:
            rf_d = rf.reindex(rf.index.union(daily.index)).ffill().reindex(daily.index) / 100.0 / up.TRADING_DAYS
            if not rf_d.isna().any():
                ex = daily - rf_d
                sharpe = float(ex.mean() / ex.std(ddof=1) * math.sqrt(up.TRADING_DAYS)) if ex.std(ddof=1) > 0 else None

    w_now = [float(mv[t].iloc[-1]) / nav1 for t in tickers]
    sigma, rc, n_months, m_from, m_to = up.ex_ante(tickers, w_now, adj, last, False)
    var = up.Z_95 * sigma / math.sqrt(12)

    positions = []
    for i, h in enumerate(r1["holdings"]):
        t = h["ticker"]
        mv0, mv1 = float(mv[t].iloc[0]), float(mv[t].iloc[-1])
        positions.append({
            "ticker": t, "name": h["name"], "asset_class": h["asset_class"], "target_weight": r(h["target_weight"], 6),
            "shares_start": float(h["shares"]), "shares_now": r(units[t].iloc[-1], 4),
            "price_start": r(px[t].iloc[0], 4), "price_now": r(px[t].iloc[-1], 4),
            "value_start": r(mv0, 2), "value_now": r(mv1, 2),
            "weight_start": r(mv0 / nav0), "weight_now": r(mv1 / nav1),
            "return": r(mv1 / mv0 - 1) if mv0 else None,           # total return of the position, dividends included
            "contribution": r((mv1 - mv0) / nav0),                 # to the return of the portfolio
            "risk_contribution": r(rc[i]), "target_risk_contribution": r(h.get("target_risk_contribution"), 6),
        })
    total_return = nav1 / nav0 - 1
    gap = sum((float(mv[t].iloc[-1]) - float(mv[t].iloc[0])) / nav0 for t in tickers) - total_return
    if abs(gap) > 1e-12:
        raise SystemExit(f"The contributions do not add up to the return: gap {gap:.3e}")

    classes = {}
    for p in positions:
        c = classes.setdefault(p["asset_class"], {"name": p["asset_class"], "weight_start": 0.0, "weight_now": 0.0,
                                                  "contribution": 0.0, "risk_contribution": 0.0})
        for k in ("weight_start", "weight_now", "contribution", "risk_contribution"):
            c[k] += p[k] or 0.0

    out = {
        "about": "Round 1 performance from its start to as_of, written by scripts/round1_performance.py "
                 "with the website's calculations (scripts/update_portfolio.py).",
        "round": "Round 1", "start_date": r1["start"].date().isoformat(), "as_of": last.date().isoformat(),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "currency": "USD",
        "prices": "Yahoo Finance closes; dividends reinvested at the close before the ex-date (Bloomberg PRTU reinvest cash dividends)",
        "nav_start": r(nav0, 2), "nav_end": r(nav1, 2), "cash": r(cash.iloc[-1], 2), "trading_days": n,
        "vol_target": VOL_TARGET, "vol_band": list(VOL_BAND),
        "metrics": {"total_return": r(total_return), "realised_vol": r(vol), "sharpe": r(sharpe),
                    "max_drawdown": r(float(drawdown.min())), "max_drawdown_from": peak.date().isoformat(),
                    "max_drawdown_to": trough.date().isoformat(), "ex_ante_vol": r(sigma), "var_1m_95_pct": r(var),
                    "var_1m_95_usd": r(var * nav1, 2), "min_days_for_stats": up.MIN_STATS_DAYS, "rf_source": rf_source,
                    "risk_model_months": n_months, "risk_model_window": [m_from.date().isoformat(), m_to.date().isoformat()]},
        "positions": positions,
        "asset_classes": [{k: (r(v) if isinstance(v, float) else v) for k, v in c.items()} for c in classes.values()],
        "nav_series": [{"date": d.date().isoformat(), "nav": r(v, 2), "index": r(100 * v / nav0, 6)} for d, v in nav.items()],
    }
    out["checks"] = {"contributions_add_up": True, "site": compare_with_site(out)}

    path = Path(args.out) if args.out else RUNS / out["as_of"] / "round1_performance.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    m = out["metrics"]
    print(f"Round 1, {out['start_date']} to {out['as_of']} ({n} daily returns): return {m['total_return']:+.2%}, "
          f"max drawdown {m['max_drawdown']:.2%}, ex-ante vol {m['ex_ante_vol']:.2%}, VaR {m['var_1m_95_pct']:.2%}")
    if vol is None:
        print(f"  realised vol and Sharpe: not computed, {n} daily returns (the website needs {up.MIN_STATS_DAYS})")
    print(f"  check: {out['checks']['site']}")
    print(f"  wrote {path.relative_to(REPO) if path.is_relative_to(REPO) else path}")


if __name__ == "__main__":
    main()
