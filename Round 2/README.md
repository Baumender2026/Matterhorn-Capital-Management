# Round 2: stock report

A two-page A4 report for each stock we add, in the Round 1 style. Page 1 has the investment case (fair value, price, margin of safety and alpha, catalyst, decision) and the DDM. Page 2 has the comparables as a double check, the value-trap check, the alpha and the specific issues. It covers the stock part of the report and Checkpoint 2 (the valuation dossier). All the Round 2 work lives in this folder.

## Add a stock

Run these from the repo root.

1. **Copy the blank:** `stock-inputs/_TEMPLATE.yaml` to `stock-inputs/<TICKER>.yaml`.
2. **Fill it in:** 5–6 peers (Bloomberg `RV`), the growth inputs, the case, 1–2 catalysts, a short comment on the sensitivity matrix and 2 specific issues. The comments explain each field.
3. **Build it:** `python3 "Round 2/build_stock_report.py" <TICKER>`
4. **Read the output:** open `reports/<TICKER>.pdf` and go through the `FLAG` lines the script prints.

If the text is too long, the build stops and says which page and by how many pixels. Shorten the text rather than shrinking the type.

**Final numbers:** on 7–8 November, re-run with `--as-of 2026-11-06`, as the challenge uses the close of Friday 6 November. Text written with `{tokens}` updates by itself, but typed facts do not, so re-read them.

## Replace by hand before submitting

Yahoo can't supply these, so they need Bloomberg:

| Input | Where | Bloomberg |
|---|---|---|
| Equity risk premium, now 6.114% from Class 5 | `valuation.erp` | `CRP` |
| First-stage growth g1 | `valuation.g1` | `EE` or `BDVD` |
| Peer set | `peers` | `RV` |
| Optional: beta, forward EPS | `valuation.overrides` | `BETA`, `EE` |

## What the script computes

| Part | Method |
|---|---|
| Cost of equity | k = 10-year yield + β × ERP, with β on SPY over the last 60 complete months |
| DDM | Gordon and two-stage, the TA's formulas |
| Comparables | A double check only. Forward P/E, P/FCF (market cap ÷ last fiscal year's FCF) and EV/EBITDA, with the peer median and implied price. The comps value averages `comps_primary`. Other multiples are in the figures file only |
| Fair value | The DDM value. A stock with no dividend has no DDM, so it falls back on the comps, with a flag |
| Value-trap check | The TA's 6 metrics plus ROA, against the peer median and the stock's own past. Red flags plus falling earnings is Fail; either one is Watch |
| Alpha | α = p · α closed + (1 − p) · α never. p = 1 is the TA's α closed; p = 0 is α never |
| Risk on our SAA | β and σ²(ε) from the regression on **our** Round 1 weights (`data/holdings.json`) |

`reports/<TICKER>_figures.json` has every number, including those the Checkpoint 1 page needs: α, σ²(ε), β on the SAA, IR.

## Files

| File | What it is |
|---|---|
| `build_stock_report.py` | The whole pipeline. `--selftest` checks it against the TA's numbers; `--refresh` downloads again |
| `Stock Report Template.dc.html` | The page layout. Change section order and page structure here |
| `stock-inputs/` | One YAML per stock, plus the blank |
| `data/` | The saved download for each stock and date, because Yahoo's ratios have no history |
| `reports/` | The generated HTML, PDF and figures |
| `TA code/`, `AMC 2026 - Round 2 guidelines.pdf` | Course material |

The pages use `support.js` and `doc-page.js` from `reports/templates/`, so keep the repo layout. Needs Python with `yfinance`, `pandas`, `numpy` and `pyyaml`, plus Google Chrome for the PDF.
