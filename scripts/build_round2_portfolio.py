#!/usr/bin/env python3
"""Round 2 portfolio: Treynor-Black with the Round 1 SAA as passive portfolio and benchmark, sized by the
tracking-error budget, as entered in Bloomberg (PRTU). The steps of the TA's notebook (02_round2_lecture.ipynb §6-§10).

    python scripts/build_round2_portfolio.py                  reads runs/round2/inputs/portfolio.yaml

Inputs, all from runs/round2/<as_of>/:
  round1_performance.json       NAV, shares and closes of the portfolio on as_of (scripts/round1_performance.py)
  <T>_figures.json, <T>_data.json for each stock (scripts/build_stock_report.py <T> --as-of <as_of>)
Writes runs/round2/<as_of>/portfolio.json and portfolio_for_PRTU.csv.

The steps, as in the TA's notebook:
  §6  Each stock's alpha, beta_S and sigma2(eps) come from its page: the regression on the SAA, last 60 complete months.
  §7  Weights inside the active portfolio A: w_i = (alpha_i / sigma2_eps_i) / sum_j (alpha_j / sigma2_eps_j).
      Then alpha_A, beta_A, sigma2(eps_A) and Treynor-Black's optimal size of A (Class 3 Part II, eqs. 11-12):
      w_A0 = (alpha_A / sigma2(eps_A)) / (E(R_S^e) / sigma_S^2),   w_A* = w_A0 / (1 + (1 - beta_A) w_A0).
  §8  The new portfolio is (1 - w_A) SAA + w_A A, so TE = w_A x sd(R_A - R_S) sqrt(12). The budget bounds w_A between
      2% / TE per unit and te_target / TE per unit (the TA: 4%, safely inside 5%). w_A = w_A* pushed inside the bounds.
  §10 Every ETF goes to (1 - w_A) x its SAA weight, so the SAA mix does not change; each stock to w_A x w_i.
      Whole shares, rounded down; what is left is cash. The weights of every position and the cash add up to 100%.
  A negative weight stops the run: it is reported, never dropped or rescaled. Only `negative_weights: zero` in the
  YAML applies the course rule (the TA's clip at 0: weight 0, the others rescaled), and the raw weight stays, flagged.
  The ex-ante TE of the portfolio as entered (after rounding) must lie in 2-5% (Round 2 guidelines).
Anything that does not reconcile stops the run and is listed. The output is written anyway, marked "stopped".
"""

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_stock_report as bsr                                  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
TE_BUDGET = (0.02, 0.05)          # Round 2 guidelines
Z_95 = 1.645
MAX_ROUNDING_PP = 0.1             # stocks' total weight may differ from w_A by rounding only
SAA_TOL = 1e-4                    # relative gap allowed between the stock pages' SAA statistics


class Stop(Exception):
    pass


def bloomberg(t):
    return f"{t} US Equity"       # every position is US-listed in USD, as in Round 1 (checked below for the stocks)


def build(cfg, runs):
    """The portfolio record. status is "ok", or "stopped" with the reasons in problems (and what was computed so far)."""
    out = {"status": "stopped", "problems": [], "notes": [], "as_of": str(cfg.get("as_of") or ""),
           "te_target": float(cfg.get("te_target") or 0), "stocks": [], "etfs": [],
           "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    try:
        compute(out, cfg, runs)
    except Stop:
        pass
    if not out["problems"]:
        out["status"] = "ok"
    return out


def compute(out, cfg, runs):
    problems, notes = out["problems"], out["notes"]
    as_of, te_target = out["as_of"], out["te_target"]
    run = runs / as_of
    stocks = [str(t).upper() for t in cfg.get("stocks") or []]

    old = [key for key in ("sleeve", "funding", "sell") if key in cfg]
    if old:
        problems.append(f"{', '.join(old)} in the YAML: the size of the stocks now comes from Treynor-Black and the TE budget "
                        "(te_target), and every ETF goes to (1 - w_A) x its SAA weight (the TA's notebook §8-§10). Remove them")
    if not TE_BUDGET[0] <= te_target <= TE_BUDGET[1]:
        problems.append(f"te_target is {te_target}: give the tracking error to aim for, between {TE_BUDGET[0]} and {TE_BUDGET[1]} "
                        "(the TA uses 0.04, safely inside the budget)")
    if not 1 <= len(stocks) <= 6:
        problems.append(f"{len(stocks)} stocks listed: give 1 to 6 tickers under `stocks`")
    elif len(stocks) != 6:
        notes.append(f"{len(stocks)} stocks: the report has 6 slots, the rest stay empty")
    perf_path = run / "round1_performance.json"
    if not perf_path.exists():
        problems.append(f"no {perf_path.relative_to(runs.parent.parent) if perf_path.is_relative_to(runs.parent.parent) else perf_path}: "
                        f"run scripts/round1_performance.py --end {as_of}")
    if problems:
        raise Stop
    perf = json.loads(perf_path.read_text(encoding="utf-8"))
    if perf["as_of"] != as_of:
        problems.append(f"round1_performance.json is for {perf['as_of']}, not {as_of}")
    nav = float(perf["nav_end"])
    out["nav"] = nav

    # --- §6: the stocks' alpha, beta_S and sigma2(eps), from their pages
    figs, snaps = {}, {}
    for t in stocks:
        f, d = run / f"{t}_figures.json", run / f"{t}_data.json"
        if not f.exists() or not d.exists():
            problems.append(f"{t}: no {t}_figures.json or {t}_data.json in runs/round2/{as_of}: run build_stock_report.py {t} --as-of {as_of}")
            continue
        figs[t], snaps[t] = json.loads(f.read_text(encoding="utf-8")), json.loads(d.read_text(encoding="utf-8"))
        if figs[t]["as_of"] != as_of:
            problems.append(f"{t}: figures are for {figs[t]['as_of']}, not {as_of}")
        if figs[t].get("currency") != "USD":
            problems.append(f"{t}: reports in {figs[t].get('currency')}; the Bloomberg ticker '<T> US Equity' assumes a US listing in USD")
    if problems:
        raise Stop
    first = figs[stocks[0]]
    for t in stocks[1:]:   # one SAA for all. Yahoo revises adjusted prices slightly between downloads: tiny gaps are a note
        f = figs[t]
        gap = max(abs(f["saa_excess"] / first["saa_excess"] - 1), abs(f["saa_vol"] / first["saa_vol"] - 1))
        if f["window"] != first["window"] or gap > SAA_TOL:
            problems.append(f"{t} and {stocks[0]} use a different SAA (window {f['window']} vs {first['window']}, statistics "
                            f"{gap:.2e} apart): rebuild both with the same as_of")
        elif gap > 1e-12:
            notes.append(f"{t} and {stocks[0]}: SAA statistics {gap:.1e} apart (relative), from Yahoo's adjusted prices at "
                         f"different download times; the SAA of {stocks[0]} is used for the risk figures")

    # Monthly excess returns of the stock pages (same window, same SAA) and the SAA, the passive portfolio
    est = None
    for t in stocks:
        e_t, _ = bsr.monthly_excess_returns(snaps[t], t)
        if est is None:
            est = e_t.drop(columns=[c for c in e_t.columns if c == t]).copy()
        elif not e_t.index.equals(est.index):
            problems.append(f"{t}: its monthly returns cover {e_t.index[0]:%Y-%m}–{e_t.index[-1]:%Y-%m}, not the same months as {stocks[0]}")
            continue
        est[t] = e_t[t]
    W = bsr.saa_weights()
    R_S = est[list(W.index)] @ W
    mu_S, sigma_S = first["saa_excess"], first["saa_vol"]
    if not (math.isclose(R_S.std() * math.sqrt(12), sigma_S, rel_tol=1e-9) and math.isclose(R_S.mean() * 12, mu_S, rel_tol=1e-9)):
        problems.append("the SAA statistics recomputed here differ from the stock pages': check data/holdings.json")
    if mu_S <= 0:
        problems.append(f"the SAA's expected excess return is {mu_S:.2%}: Treynor-Black needs it positive")

    # --- §7: weights inside A. Raw Treynor-Black weights first. A negative one stops the run, unless the YAML says
    # negative_weights: zero (the course rule, Checkpoint 1, the TA's .clip(lower=0)): then it is entered as 0, shown
    # next to its raw weight, and the positive weights are rescaled to fill A.
    rule = str(cfg.get("negative_weights") or "stop").strip()
    out["negative_weights"] = rule
    if rule not in ("stop", "zero"):
        problems.append(f"negative_weights is '{rule}': use stop (the default) or zero (the course rule)")
    score = {t: figs[t]["alpha"] / figs[t]["sigma2_eps"] for t in stocks}
    total_score = sum(score.values())
    positive = sum(v for v in score.values() if v > 0)
    for t in stocks:
        f = figs[t]
        raw = score[t] / total_score if total_score else float("nan")
        entered = raw if rule == "stop" else (max(score[t], 0) / positive if positive else float("nan"))
        out["stocks"].append({"ticker": t, "name": f["name"], "bloomberg": bloomberg(t), "currency": f["currency"],
                              "alpha": f["alpha"], "sigma2_eps": f["sigma2_eps"], "beta_S": f["beta_S"], "ir": f["ir"],
                              "score": score[t], "weight_sleeve_raw": raw, "weight_sleeve_tb": entered, "price": f["P0"],
                              "negative": score[t] < 0, "set_to_zero": rule == "zero" and score[t] < 0})
    neg = [s for s in out["stocks"] if s["negative"]]
    if rule == "stop":
        if total_score <= 0:
            problems.append(f"the sum of alpha / sigma2(eps) is {total_score:.3f}: Treynor-Black has no positive active portfolio")
        for s in neg:
            problems.append(f"{s['ticker']}: Treynor-Black weight {s['weight_sleeve_raw']:.2%} of the active portfolio (alpha {s['alpha']:+.2%}). "
                            "Negative weights are not dropped or rescaled: decide what to do with this stock "
                            "(negative_weights: zero applies the course rule)")
    else:
        if positive <= 0:
            problems.append("no stock has a positive alpha: Treynor-Black has nothing to put in the active portfolio")
        for s in neg:
            notes.append(f"{s['ticker']}: raw Treynor-Black weight {s['weight_sleeve_raw']:.2%} of the active portfolio (alpha {s['alpha']:+.2%}), "
                         "entered as 0 by the course rule (negative_weights: zero); the positive weights are rescaled to fill it")
    held = [s["ticker"] for s in out["stocks"] if s["weight_sleeve_tb"] > 0]
    if 0 < len(held) < 3:
        notes.append(f"{len(held)} stock(s) with a positive weight ({', '.join(held)}): Checkpoint 1 asks for 3 to 6")
    if problems:
        raise Stop
    w = pd.Series({s["ticker"]: s["weight_sleeve_tb"] for s in out["stocks"]})
    assert abs(w.sum() - 1) < 1e-12

    # Characteristics of A and Treynor-Black's optimal size (Class 3 Part II, eqs. 11-12, 15-16)
    alpha_A = sum(w[t] * figs[t]["alpha"] for t in stocks)
    beta_A = sum(w[t] * figs[t]["beta_S"] for t in stocks)
    s2_A = sum(w[t] ** 2 * figs[t]["sigma2_eps"] for t in stocks)
    w_A0 = (alpha_A / s2_A) / (mu_S / sigma_S ** 2)
    w_A_star = w_A0 / (1 + (1 - beta_A) * w_A0)
    ir_A, sr_S = alpha_A / math.sqrt(s2_A), mu_S / sigma_S
    if not 0 < w_A_star <= 1:
        notes.append(f"Treynor-Black w_A* is {w_A_star:.0%}, outside 0-100%: with alphas of this size the formula asks for a huge bet, "
                     "the TE budget decides (the TA's notebook §7)")

    # --- §8: TE = w_A x sd(R_A - R_S) sqrt(12), so the budget bounds w_A; w_A* is pushed inside the bounds
    R_A = est[stocks] @ w[stocks]
    te_unit = float((R_A - R_S).std() * math.sqrt(12))
    w_A_lo, w_A_hi = TE_BUDGET[0] / te_unit, te_target / te_unit
    w_A = min(max(w_A_star, w_A_lo), w_A_hi)
    bound = "treynor_black" if w_A == w_A_star else "te_target" if w_A == w_A_hi else "te_floor"
    if w_A > 1:
        problems.append(f"w_A is {w_A:.0%}: the stocks track the SAA so closely (TE {te_unit:.2%} per unit) that even 100% in them "
                        f"stays below the {TE_BUDGET[0]:.0%} floor or the {te_target:.0%} target")
    R_new = (1 - w_A) * R_S + w_A * R_A                  # the portfolio at its target weights, before rounding
    mu_N = mu_S + w_A * (alpha_A + (beta_A - 1) * mu_S)   # E(R_new^e) = (1 - w_A) E(R_S^e) + w_A E(R_A^e)
    out["sleeve"] = w_A                                   # the share of the portfolio in the stocks (key kept for the report)
    out["active"] = {"alpha_A": alpha_A, "beta_A": beta_A, "sigma_eps_A": math.sqrt(s2_A), "ir_A": ir_A,
                     "w_A0": w_A0, "w_A_star": w_A_star, "te_per_unit": te_unit, "w_A_lo": w_A_lo, "w_A_hi": w_A_hi,
                     "w_A": w_A, "bound": bound, "te_target_weights": float((R_new - R_S).std() * math.sqrt(12)),
                     "sharpe_saa": sr_S, "sharpe_with_active": math.sqrt(sr_S ** 2 + ir_A ** 2),
                     "sharpe_at_w_A": mu_N / float(R_new.std() * math.sqrt(12)),
                     "saa_excess": mu_S, "saa_vol": sigma_S, "window": first["window"]}
    if problems:
        raise Stop

    # --- §10: every ETF to (1 - w_A) x its SAA weight, every stock to w_A x w_i, whole shares rounded down
    pos = {p["ticker"]: p for p in perf["positions"]}
    missing = sorted(set(W.index) - set(pos))
    if missing:
        problems.append(f"the SAA has {', '.join(missing)}, not in round1_performance.json")
        raise Stop
    for p in perf["positions"]:
        t, held_now, price = p["ticker"], float(p["shares_now"]), float(p["price_now"])
        w_saa = float(W.get(t, 0))
        if abs(float(p["target_weight"] or 0) - w_saa) > 1e-9:
            problems.append(f"{t}: target weight {p['target_weight']} in round1_performance.json, {w_saa} in data/holdings.json")
        target = (1 - w_A) * w_saa
        after = math.floor(target * nav / price)
        out["etfs"].append({"ticker": t, "name": p["name"], "bloomberg": bloomberg(t), "currency": "USD",
                            "asset_class": p["asset_class"], "weight_saa": w_saa, "weight_target": target,
                            "shares_before": held_now, "shares_after": after, "trade": after - held_now,
                            "price": price, "value": after * price})
    for s in out["stocks"]:
        s["weight_target"] = w_A * s["weight_sleeve_tb"]
        s["shares"] = math.floor(s["weight_target"] * nav / s["price"])
        s["value"] = s["shares"] * s["price"]
    cash = nav - sum(e["value"] for e in out["etfs"]) - sum(s["value"] for s in out["stocks"])
    raised = sum(e["shares_before"] * e["price"] for e in out["etfs"]) - sum(e["value"] for e in out["etfs"])
    out["raised"] = {"usd": raised, "weight": raised / nav}
    if cash < 0:
        problems.append(f"cash would be USD {cash:,.2f}: the sales raise {raised / nav:.2%} of the NAV, less than the stocks cost")
    for e in out["etfs"]:
        e["weight"] = e["value"] / nav
    for s in out["stocks"]:
        s["weight_total"] = s["value"] / nav
        s["weight_sleeve_actual"] = s["value"] / (w_A * nav)
    out["cash"] = {"usd": cash, "weight": cash / nav}
    total_w = sum(e["weight"] for e in out["etfs"]) + sum(s["weight_total"] for s in out["stocks"]) + out["cash"]["weight"]
    out["total"] = {"usd": nav, "weight": total_w}
    if abs(total_w - 1) > 1e-9:
        problems.append(f"the weights add up to {total_w:.6%}, not 100%")
    stock_w = sum(s["weight_total"] for s in out["stocks"])
    if abs(stock_w - w_A) * 100 > MAX_ROUNDING_PP:
        problems.append(f"the stocks weigh {stock_w:.2%} of the portfolio, not w_A = {w_A:.2%}: more than rounding")

    # --- risk against the SAA, of the portfolio as entered (after rounding; cash earns the T-bill: zero excess return)
    w_new = {e["ticker"]: e["weight"] for e in out["etfs"] if e["weight"]} | {s["ticker"]: s["weight_total"] for s in out["stocks"]}
    missing = [t for t in w_new if t not in est.columns]
    if missing:
        problems.append(f"no monthly returns for {', '.join(missing)}")
        raise Stop
    R_N = est[list(w_new)] @ pd.Series(w_new)
    te, vol_N = (R_N - R_S).std() * math.sqrt(12), R_N.std() * math.sqrt(12)
    out["risk"] = {"te": te, "vol_new": vol_N, "vol_saa": sigma_S, "var_new": Z_95 * vol_N / math.sqrt(12),
                   "var_saa": Z_95 * sigma_S / math.sqrt(12), "months": len(est),
                   "window": [est.index[0].strftime("%Y-%m"), est.index[-1].strftime("%Y-%m")]}
    if not TE_BUDGET[0] <= te <= TE_BUDGET[1]:
        problems.append(f"ex-ante tracking error {te:.2%} is outside the {TE_BUDGET[0]:.0%}–{TE_BUDGET[1]:.0%} budget")


def write(out, run):
    run.mkdir(parents=True, exist_ok=True)
    (run / "portfolio.json").write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8", newline="\n")
    if out["status"] != "ok":
        return
    with open(run / "portfolio_for_PRTU.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["Name", "Bloomberg ticker", "Currency", "Shares", "Close price", "Price date", "Weight"])
        for x in [e for e in out["etfs"] if e["shares_after"]] + [x for x in out["stocks"] if x["shares"]]:   # PRTU: positions held
            shares = x["shares_after"] if "shares_after" in x else x["shares"]
            wr.writerow([x["name"], x["bloomberg"], x["currency"], f"{shares:.0f}", f"{x['price']:.4f}", out["as_of"],
                         f"{x.get('weight', x.get('weight_total')):.6f}"])


BOUND = {"treynor_black": "Treynor-Black's own size", "te_target": "capped by the TE target", "te_floor": "raised to the 2% TE floor"}


def report(out):
    """The run on screen: Treynor-Black inside A, the size of A, the portfolio, then what stopped it."""
    if out["stocks"]:
        print(f"Treynor-Black inside the active portfolio A, prices of {out['as_of']}:")
        print(f"  {'':6}{'alpha':>8}{'s2(eps)':>9}{'a/s2':>8}{'% of A: raw, entered':>24}")
        for x in out["stocks"]:
            flag = ("   NEGATIVE: entered as 0 (course rule)" if x["set_to_zero"] else "   NEGATIVE: not dropped, not rescaled") if x["negative"] else ""
            print(f"  {x['ticker']:6}{x['alpha']:+8.2%}{x['sigma2_eps']:9.4f}{x['score']:8.2f}{x['weight_sleeve_raw']:12.2%}"
                  f"{x['weight_sleeve_tb']:10.2%}{flag}")
    a = out.get("active")
    if a:
        print(f"  A: alpha {a['alpha_A']:+.2%}, beta {a['beta_A']:.2f}, sigma(eps) {a['sigma_eps_A']:.2%}, IR {a['ir_A']:.2f}")
        print(f"Size of A: Treynor-Black w_A* {a['w_A_star']:.2%}; TE per unit of A {a['te_per_unit']:.2%}, so the budget allows "
              f"{a['w_A_lo']:.2%} (TE {TE_BUDGET[0]:.0%}) to {a['w_A_hi']:.2%} (TE {out['te_target']:.0%})")
        print(f"  w_A = {a['w_A']:.2%}, {BOUND[a['bound']]}; every ETF x {1 - a['w_A']:.4f}")
    if out["status"] == "ok":
        k = out["risk"]
        print(f"Portfolio, NAV USD {out['nav']:,.2f} (ETF sales raise {out['raised']['weight']:.2%}):")
        print(f"  {'':6}{'shares now':>14}    {'to enter':>10}  {'price':>9}  {'target':>7}  {'weight':>7}")
        for e in out["etfs"]:
            print(f"  {e['ticker']:6}{e['shares_before']:>14,.4f} -> {e['shares_after']:>10,.0f}  {e['price']:>9.2f}  "
                  f"{e['weight_target']:7.2%}  {e['weight']:7.2%}")
        for x in out["stocks"]:
            print(f"  {x['ticker']:6}{0:>14,.4f} -> {x['shares']:>10,.0f}  {x['price']:>9.2f}  {x['weight_target']:7.2%}  {x['weight_total']:7.2%}")
        print(f"  cash USD {out['cash']['usd']:,.2f} ({out['cash']['weight']:.4%})   total {out['total']['weight']:.4%}")
        print(f"  ex-ante TE vs SAA {k['te']:.2%} (target weights {a['te_target_weights']:.2%}), vol {k['vol_new']:.2%} "
              f"(SAA {k['vol_saa']:.2%}), VaR {k['var_new']:.2%} (SAA {k['var_saa']:.2%})")
        print(f"  Sharpe: SAA {a['sharpe_saa']:.2f}, at w_A {a['sharpe_at_w_A']:.2f} (at w_A*, eq. 16: {a['sharpe_with_active']:.2f})")
    for n in out["notes"]:
        print(f"NOTE: {n}")
    for p in out["problems"]:
        print(f"STOP: {p}")


def main():
    ap = argparse.ArgumentParser(description="Treynor-Black on the SAA, sized by the TE budget: the Round 2 portfolio for PRTU.")
    ap.add_argument("--inputs", default=str(REPO / "runs" / "round2" / "inputs" / "portfolio.yaml"))
    ap.add_argument("--runs", default=str(REPO / "runs" / "round2"), help="Folder with one sub-folder per as-of date")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.inputs).read_text(encoding="utf-8")) or {}
    runs = Path(args.runs).resolve()
    out = build(cfg, runs)
    report(out)
    if out["as_of"] and (runs / out["as_of"]).exists():
        write(out, runs / out["as_of"])
        print(f"wrote {runs / out['as_of'] / 'portfolio.json'}" + ("" if out["status"] == "ok" else " (stopped: do not promote)"))
    sys.exit(0 if out["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
