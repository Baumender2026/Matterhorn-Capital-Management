#!/usr/bin/env python3
"""Build data/portfolio.json from data/holdings.json.

Downloads daily closes (yfinance) and the 1-month T-bill rate (FRED DGS1MO),
then computes NAV, realised performance, current vs target weights and the
ex-ante risk model. Run daily by .github/workflows/update-portfolio.yml.

    python scripts/update_portfolio.py [--config data/holdings.json] [--out data/portfolio.json]

Rules (AMC):
  * NAV = cash + sum(shares * raw close). Dividends are reinvested in the ETF that
    pays them at the ex-date close, as in the Bloomberg portfolio (PRTU "reinvest
    cash dividends"); cash earns 0%.
  * Each round restarts at its own starting NAV (USD 100M). Daily returns are
    chain-linked across rounds into an index (base 100) for the inception figures.
  * Realised volatility and the Sharpe ratio are left empty until there are
    MIN_STATS_DAYS daily returns.
  * The data runs to the latest close every holding has. Before CLOSE_CUTOFF
    (New York time) today's bar is an intraday price and is ignored.

If today's close is not out yet, the JSON stays at the previous close. If Yahoo
returns no prices for any ticker, or its latest common close is older than the one
already published, the previous JSON is left untouched and the script exits 0 with
a warning (the next run retries). It exits 1, also leaving the JSON
untouched, if only some tickers come back, if the latest close is more than
MAX_STALE_DAYS trading days old (weekdays; holidays are not excluded), or on any
other data error.
The risk-free rate is only needed for the Sharpe ratio: if every source fails, the
Sharpe ratio is left empty instead.
"""

import argparse
import io
import json
import math
import os
import sys
import time
import urllib.request
from datetime import datetime, time as dtime, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS1MO"
TREASURY_URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                "daily-treasury-rates.csv/{y}/all?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv")
RF_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code data", "DGS1MO.csv")
PLACEHOLDER_TICKERS = {"", "COMMODITY"}
RISK_MONTHS = 60
RISK_YEARS = 6          # history downloaded for the monthly risk model
Z_95 = 1.645
TRADING_DAYS = 252
MIN_STATS_DAYS = 20     # daily returns needed before realised vol and Sharpe are reported
CLOSE_CUTOFF = dtime(16, 15)  # New York time after which today's daily bar is the close
MAX_STALE_DAYS = 3      # trading days the latest close may lag before the run fails


class DataError(Exception):
    pass


class PricesUnavailable(DataError):
    """Yahoo returned no prices for any ticker: keep the previous JSON and let the next run retry."""


# ---------------------------------------------------------------- config

def load_config(path):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    rounds = []
    for r in cfg.get("rounds", []):
        if not r.get("start_date"):
            continue
        rounds.append({**r, "start": pd.Timestamp(r["start_date"])})
    rounds.sort(key=lambda r: r["start"])
    for i, r in enumerate(rounds):
        r["next_start"] = rounds[i + 1]["start"] if i + 1 < len(rounds) else None
    return cfg, rounds


def placeholder_problems(r):
    """Reasons a round's holdings are not filled in yet (empty list = ready)."""
    out = []
    if not r.get("holdings"):
        out.append(f"{r['id']}: no holdings")
    for h in r.get("holdings", []):
        t = str(h.get("ticker", "")).strip()
        if t.upper() in PLACEHOLDER_TICKERS:
            out.append(f"{r['id']}: placeholder ticker '{t}'")
        if not h.get("shares") and float(h.get("target_weight") or 0) > 0:
            out.append(f"{r['id']}: {t or '?'} has 0 shares")
    return out


# ---------------------------------------------------------------- downloads

def download_prices(tickers, start, end):
    """Raw close, adjusted close and dividends per ticker, indexed by date."""
    close, adj, div, missing = {}, {}, {}, []
    for t in tickers:
        df, err = None, "empty response"
        for attempt in range(3):
            try:
                df = yf.Ticker(t).history(start=start.strftime("%Y-%m-%d"),
                                          end=end.strftime("%Y-%m-%d"),
                                          auto_adjust=False, actions=True)
                if not df.empty:
                    break
            except Exception as e:  # network / Yahoo hiccup: retry, then fail
                err = e
            time.sleep(2 * (attempt + 1))
        if df is None or df.empty:
            missing.append(f"{t} ({err})")
            continue
        idx = df.index.tz_localize(None).normalize() if df.index.tz is not None else df.index.normalize()
        df.index = idx
        df = df[~df.index.duplicated(keep="last")]
        close[t] = df["Close"].round(4)  # Yahoo sends float32 noise (374.0700073 for 374.07)
        adj[t] = df["Adj Close"] if "Adj Close" in df else df["Close"]
        div[t] = df["Dividends"] if "Dividends" in df else pd.Series(0.0, index=df.index)
    if len(missing) == len(tickers):
        raise PricesUnavailable("Yahoo returned no prices for any ticker: " + ", ".join(missing))
    if missing:
        raise DataError("Yahoo returned no prices for " + ", ".join(missing) + " while the other tickers downloaded")
    return pd.DataFrame(close), pd.DataFrame(adj), pd.DataFrame(div).fillna(0.0)


def fetch_csv(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "matterhorn-portfolio/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return pd.read_csv(io.StringIO(resp.read().decode("utf-8")))


def rate_series(dates, values):
    s = pd.Series(pd.to_numeric(values, errors="coerce").values, index=pd.to_datetime(dates)).dropna().sort_index()
    if s.empty:
        raise DataError("no observations")
    return s


def download_rf(years):
    """1-month T-bill, annualised %, indexed by date, and its source.

    FRED DGS1MO first. It often times out from GitHub-hosted runners, so fall back to
    the same rate published by the US Treasury, then to the copy kept in the repo.
    Returns (None, None) if every source fails.
    """
    errors = []
    for attempt in range(2):
        try:
            df = fetch_csv(FRED_URL, 20)
            return rate_series(df.iloc[:, 0], df.iloc[:, 1]), "FRED DGS1MO"
        except Exception as e:
            errors.append(f"FRED: {e}")
            time.sleep(2 * (attempt + 1))
    try:
        parts = []
        for y in years:
            df = fetch_csv(TREASURY_URL.format(y=y), 30)
            parts.append(rate_series(pd.to_datetime(df["Date"], format="%m/%d/%Y"), df["1 Mo"]))
        return pd.concat(parts).sort_index(), "US Treasury daily par yield curve, 1 Mo"
    except Exception as e:
        errors.append(f"Treasury: {e}")
    try:
        df = pd.read_csv(RF_CACHE)
        return rate_series(df.iloc[:, 0], df.iloc[:, 1]), "code data/DGS1MO.csv (cached FRED DGS1MO)"
    except Exception as e:
        errors.append(f"cache: {e}")
    print("WARNING: risk-free rate unavailable, Sharpe ratio left empty -- " + " | ".join(errors), file=sys.stderr)
    return None, None


# ---------------------------------------------------------------- calculations

def trading_days_old(as_of, ny_now):
    """Weekdays after the as_of close up to the latest close due by ny_now (holidays not excluded)."""
    due = pd.Timestamp(ny_now.date())
    if ny_now.time() < CLOSE_CUTOFF:
        due -= pd.Timedelta(days=1)
    return len(pd.bdate_range(as_of + pd.Timedelta(days=1), due))


def round_nav(r, close, div, as_of):
    """Daily NAV of one round from its start to its end (next round's start) or as_of."""
    tickers = [h["ticker"] for h in r["holdings"]]
    shares = pd.Series({h["ticker"]: float(h["shares"]) for h in r["holdings"]})
    end = r["next_start"] if r["next_start"] is not None else as_of
    px = close.loc[r["start"]:end, tickers]
    if px.empty or px.index[0] != r["start"]:
        raise DataError(f"{r['id']}: no closing prices on start date {r['start'].date()}")
    px = px.ffill()
    if px.isna().any().any():
        raise DataError(f"{r['id']}: missing prices for {list(px.columns[px.isna().any()])}")
    d = div.reindex(px.index).loc[:, tickers].fillna(0.0)
    d.iloc[0] = 0.0  # bought at the start-date close: not entitled to that day's ex-dividend
    # dividends buy more of the ETF that pays them at the ex-date close (Bloomberg PRTU "reinvest cash dividends")
    units = shares * (1 + d / px).cumprod()
    cash = pd.Series(float(r.get("cash", 0.0)), index=px.index)
    mv = px * units
    nav = cash + mv.sum(axis=1)
    return nav, cash, mv, px, units


def ex_ante(tickers, weights, adj, as_of, allow_short):
    """sigma = sqrt(w'Vw), V = 12 * cov of the last 60 complete monthly returns."""
    monthly = adj[tickers].resample("ME").last()
    monthly = monthly[monthly.index < as_of.to_period("M").start_time]  # drop partial month
    rets = monthly.pct_change().iloc[1:].dropna(how="any").tail(RISK_MONTHS)
    if len(rets) < RISK_MONTHS and not allow_short:
        raise DataError(f"only {len(rets)} complete monthly returns for the risk model (need {RISK_MONTHS})")
    if len(rets) < 12:
        raise DataError(f"only {len(rets)} monthly returns for the risk model")
    V = 12.0 * rets.cov().values
    w = np.asarray(weights, dtype=float)
    Vw = V @ w
    var = float(w @ Vw)
    sigma = math.sqrt(var)
    rc = (w * Vw) / var
    return sigma, rc, len(rets), rets.index[0], rets.index[-1]


def r6(x):
    return None if x is None else round(float(x), 6)


def build(cfg_path, allow_short):
    cfg, rounds = load_config(cfg_path)
    now = datetime.now(timezone.utc)
    ny_now = datetime.now(ZoneInfo("America/New_York"))
    today = pd.Timestamp(ny_now.date())
    after_close = ny_now.time() >= CLOSE_CUTOFF

    started = [r for r in rounds if r["start"] <= today]
    if not started:
        nxt = rounds[0]["start"].date().isoformat() if rounds else None
        return pending(now, f"Round 1 starts {nxt}" if nxt else "No round start date set")
    problems = [p for r in started for p in placeholder_problems(r)]
    if problems:
        return pending(now, "holdings.json not filled in: " + "; ".join(problems))

    tickers = sorted({h["ticker"] for r in started for h in r["holdings"]})
    dl_start = min(started[0]["start"], today - pd.DateOffset(years=RISK_YEARS)) - pd.Timedelta(days=10)
    close, adj, div = download_prices(tickers, dl_start, today + pd.Timedelta(days=1))
    if not after_close:
        # before the close Yahoo's bar for today holds an intraday price, not a close
        close, adj, div = (x[x.index < today] for x in (close, adj, div))

    # common trading calendar = dates where every ticker of the active round has a close
    active = close[[h["ticker"] for h in started[-1]["holdings"]]]
    as_of = active.dropna().index.max()
    if as_of < started[-1]["start"]:
        return pending(now, f"{started[-1]['id']}: waiting for the first close on {started[-1]['start'].date()}")
    latest = active.apply(lambda s: s.last_valid_index())
    behind = ", ".join(f"{t} (last close {latest[t].date()})" for t in active if latest[t] < latest.max())
    age = trading_days_old(as_of, ny_now)
    if age > MAX_STALE_DAYS:
        raise DataError(f"latest common close {as_of.date()} is {age} trading days old (limit {MAX_STALE_DAYS})"
                        + (f"; behind the others: {behind}" if behind else "; Yahoo has no newer close"))
    if age:
        print(f"NOTE: latest common close is {as_of.date()}, {age} trading day(s) old"
              + (f"; behind the others: {behind}" if behind else "; Yahoo has no newer close yet"))

    # ---- NAV per round, chain-linked index
    series, rets, round_rows = [], [], []
    level = 100.0
    for r in started:
        nav, cash, mv, px, units = round_nav(r, close, div, as_of)
        rr = nav.pct_change().iloc[1:]
        idx = level * nav / nav.iloc[0]
        for d in nav.index:
            series.append({"date": d.date().isoformat(), "round": r["id"],
                           "nav": round(float(nav[d]), 2), "index": round(float(idx[d]), 4)})
        rets.append(rr)
        level = float(idx.iloc[-1])
        round_rows.append({"id": r["id"], "start_date": r["start"].date().isoformat(),
                           "end_date": nav.index[-1].date().isoformat(),
                           "status": "closed" if r["next_start"] is not None else "active",
                           "start_nav": round(float(nav.iloc[0]), 2), "end_nav": round(float(nav.iloc[-1]), 2),
                           "return": r6(nav.iloc[-1] / nav.iloc[0] - 1)})
        last = (r, nav, cash, mv, px, units)
    for r in cfg.get("rounds", []):
        if r["id"] not in {x["id"] for x in round_rows}:
            round_rows.append({"id": r["id"], "start_date": r.get("start_date"), "status": "pending"})

    daily = pd.concat(rets)
    daily = daily[~daily.index.duplicated(keep="last")]
    index_level = pd.Series([p["index"] for p in series], index=[p["date"] for p in series])
    index_level = index_level[~index_level.index.duplicated(keep="last")]

    total_return = index_level.iloc[-1] / 100.0 - 1
    max_dd = float((index_level / index_level.cummax() - 1).min())
    n = len(daily)
    vol = sharpe = None
    rf, rf_source = None, None
    if n >= MIN_STATS_DAYS:
        vol = float(daily.std(ddof=1) * math.sqrt(TRADING_DAYS))
        rf, rf_source = download_rf(range(daily.index[0].year, today.year + 1))
        if rf is not None:
            rf_d = rf.reindex(rf.index.union(daily.index)).ffill().reindex(daily.index) / 100.0 / TRADING_DAYS
            if rf_d.isna().any():
                print("WARNING: risk-free rate missing for some return dates, Sharpe ratio left empty", file=sys.stderr)
            else:
                ex = daily - rf_d
                sd = ex.std(ddof=1)
                sharpe = float(ex.mean() / sd * math.sqrt(TRADING_DAYS)) if sd > 0 else None

    # ---- current holdings of the active round
    r, nav, cash, mv, px, units = last
    nav_now = float(nav.iloc[-1])
    cash_now = float(cash.iloc[-1])
    tick = [h["ticker"] for h in r["holdings"]]
    w_now = [float(mv[t].iloc[-1]) / nav_now for t in tick]
    sigma, rc, n_months, m_from, m_to = ex_ante(tick, w_now, adj, as_of, allow_short)
    var_pct = Z_95 * sigma / math.sqrt(12)

    holdings = []
    for i, h in enumerate(r["holdings"]):
        t = h["ticker"]
        tw = float(h.get("target_weight") or 0.0)
        holdings.append({
            "ticker": t, "name": h.get("name") or t, "asset_class": h.get("asset_class") or "",
            "shares": round(float(units[t].iloc[-1]), 4), "price": round(float(px[t].iloc[-1]), 4),
            "market_value": round(float(mv[t].iloc[-1]), 2),
            "weight": r6(w_now[i]), "target_weight": r6(tw),
            "drift_pp": round((w_now[i] - tw) * 100, 4),
            "risk_contribution": r6(rc[i]),
            "target_risk_contribution": r6(h.get("target_risk_contribution")),
        })
    cash_w = cash_now / nav_now
    classes = {}
    for h in holdings:
        classes[h["asset_class"] or "Other"] = classes.get(h["asset_class"] or "Other", 0.0) + h["weight"]
    classes["Cash"] = classes.get("Cash", 0.0) + cash_w

    payload = {
        "status": "ok",
        "as_of": as_of.date().isoformat(),
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "currency": "USD",
        "current_round": r["id"],
        "nav": round(nav_now, 2),
        "metrics": {
            "total_return": r6(total_return),
            "realised_vol": r6(vol),
            "sharpe": r6(sharpe),
            "max_drawdown": r6(max_dd),
            "ex_ante_vol": r6(sigma),
            "var_1m_95_pct": r6(var_pct),
            "var_1m_95_usd": round(var_pct * nav_now, 2),
            "daily_returns": n,
            "min_days_for_stats": MIN_STATS_DAYS,
            "rf_1m_latest": r6(rf.iloc[-1] / 100.0) if rf is not None else None,
            "rf_source": rf_source,
            "risk_model_months": n_months,
            "risk_model_window": [m_from.date().isoformat(), m_to.date().isoformat()],
        },
        "rounds": round_rows,
        "holdings": holdings,
        "cash": {"market_value": round(cash_now, 2), "weight": r6(cash_w)},
        "asset_classes": [{"name": k, "weight": r6(v)} for k, v in classes.items()],
        "nav_series": series,
    }
    check(payload)
    return payload


def pending(now, message):
    return {"status": "pending", "message": message,
            "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ")}


def check(obj, path="$"):
    """Refuse to write NaN / inf anywhere, and sanity-check weights."""
    if isinstance(obj, float) and not math.isfinite(obj):
        raise DataError(f"non-finite value at {path}")
    if isinstance(obj, dict):
        for k, v in obj.items():
            check(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check(v, f"{path}[{i}]")
    if path == "$" and obj.get("status") == "ok":
        total = sum(h["weight"] for h in obj["holdings"]) + obj["cash"]["weight"]
        if abs(total - 1) > 1e-4:
            raise DataError(f"weights sum to {total:.6f}, not 1")
        rcs = sum(h["risk_contribution"] for h in obj["holdings"])
        if abs(rcs - 1) > 1e-4:
            raise DataError(f"risk contributions sum to {rcs:.6f}, not 1")


def published_as_of(out):
    """as_of of the JSON already at out (None if there is none)."""
    try:
        with open(out, encoding="utf-8") as f:
            as_of = json.load(f).get("as_of")
    except (ValueError, OSError):
        return None
    return pd.Timestamp(as_of) if as_of else None


def published_age(out):
    """Trading days since the as_of of the JSON already at out (None if there is none)."""
    as_of = published_as_of(out)
    return trading_days_old(as_of, datetime.now(ZoneInfo("America/New_York"))) if as_of is not None else None


def write_if_changed(payload, out):
    def strip(p):
        return {k: v for k, v in p.items() if k != "generated_at"}
    if os.path.exists(out):
        try:
            with open(out, encoding="utf-8") as f:
                if strip(json.load(f)) == strip(payload):
                    print(f"{out}: unchanged")
                    return False
        except (ValueError, OSError):
            pass
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, out)
    print(f"{out}: written")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="data/holdings.json")
    ap.add_argument("--out", default="data/portfolio.json")
    ap.add_argument("--allow-short-history", action="store_true",
                    help="accept fewer than 60 monthly returns (testing only)")
    args = ap.parse_args()
    try:
        payload = build(args.config, args.allow_short_history)
    except PricesUnavailable as e:
        age = published_age(args.out)
        if age is not None and age > MAX_STALE_DAYS:
            print(f"::error::{e} -- and {args.out} is {age} trading days old (limit {MAX_STALE_DAYS})")
            sys.exit(1)
        print(f"::warning::{e} -- {args.out} left unchanged")
        return
    except Exception as e:
        print(f"::error::{e} -- {args.out} left unchanged")
        sys.exit(1)
    if payload["status"] == "pending":
        print(f"pending: {payload['message']}")
    else:
        # Yahoo sometimes drops the newest bar of a ticker for a while: never step back a day
        prev = published_as_of(args.out)
        if prev is not None and pd.Timestamp(payload["as_of"]) < prev:
            print(f"::warning::latest common close is {payload['as_of']}, older than the published "
                  f"{prev.date()} -- {args.out} left unchanged")
            return
        m = payload["metrics"]
        print(f"as of {payload['as_of']}: NAV {payload['nav']:,.0f}  return {m['total_return']:+.2%}  "
              f"ex-ante vol {m['ex_ante_vol']:.2%}  VaR {m['var_1m_95_pct']:.2%}")
    write_if_changed(payload, args.out)


if __name__ == "__main__":
    main()
