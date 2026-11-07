# Round 2: stock report

A two-page A4 report for each stock we add, in the Round 1 style. Page 1 has the investment case (fair value, price, margin of safety and alpha, catalyst, decision) and the DDM. Page 2 has the comparables as a double check, the value-trap check, the alpha and the specific issues. It covers the stock part of the report and Checkpoint 2 (the valuation dossier). The Round 2 inputs and runs live in this folder; the code is `scripts/build_stock_report.py` and the page layout `report/templates/stock-report.dc.html`.

## Add a stock

Run these from the repo root.

1. **Copy the blank:** `runs/round2/inputs/_TEMPLATE.yaml` to `runs/round2/inputs/<TICKER>.yaml`.
2. **Fill it in:** the text only: the sources of g1, T and g2, the case, 1–2 catalysts, a short comment on the sensitivity matrix and 2 specific issues. The comments explain each field. The numbers (P0, D0, β, rf, ERP, g1, T, g2, method, payout) and the peers come from the stock's sheet in `DDM_valuation.xlsx`, so the stock must be in the workbook, with its assumptions set, before its report is built (see *Screen candidates*).
3. **Build it:** `python3 scripts/build_stock_report.py <TICKER>`
4. **Read the output:** open `runs/round2/<as-of>/<TICKER>.pdf` and go through the `FLAG` lines the script prints.

If the text is too long, the build stops and says which page and by how many pixels. Shorten the text rather than shrinking the type.

**Final numbers:** on 7–8 November, re-run with `--as-of 2026-11-06`, as the challenge uses the close of Friday 6 November. Text written with `{tokens}` updates by itself, but typed facts do not, so re-read them. Then promote the final pages into the report: `python3 scripts/promote.py runs/round2/2026-11-06/<TICKER>.dc.html` (see *The Round 2 report* below).

## Screen candidates

Before writing a YAML, value the candidates from the Bloomberg screen (`EQS`) in `runs/round2/inputs/DDM_valuation.xlsx`. It has one sheet per stock, with the Gordon Growth Model and the two-stage DDM as Excel formulas, and a Summary with fair value, margin of safety (V0 / P0 − 1) and signal. From row 101, each sheet has the comparables of the stock report as Excel formulas (same multiples, n/m rule, peer median and implied prices, from the same code), and Summary shows the comps value, its margin of safety and the TA's DDM vs comps check from column Y. Column X is the team's.

1. **Add the stocks:** `python3 scripts/build_ddm_workbook.py KO PEP` (with the workbook closed in Excel). It downloads the price, D0, β on SPY, the 10-year yield and Yahoo's growth estimates, and adds one sheet and one Summary row per ticker.
2. **Check the yellow cells** in each sheet. A new sheet starts with g1 = Yahoo's average earnings growth estimate (the current and next fiscal year, *Analysis > Growth Estimates*; the next year alone for NVO, PFE, VZ, PEP and NSRGY, added on 7 Nov: `G1_NEXT_YEAR` in the script), g2 = 3%, T = 5, the two-stage method, *Dividends + buybacks* and P/FCF in the comps value (the team's rule for every stock since 7 Nov). Set T for the stock by hand, and the β override if you use Bloomberg `BETA`. ERP and the buy threshold are on `Inputs`: the stock reports read the ERP from there too.
   **Non-US companies:** the tickers are US lines (ADRs, or AZN on the NYSE), so price and dividends are in USD and rf stays the US 10-year. Only the ERP changes: the script types the country's ERP in the sheet (Damodaran, 5 Jan 2026: mature market 4.23% + country risk premium), and the report takes it from there. A foreign company's buybacks are converted to USD per ADR. Yahoo's estimates come from the home listing when the US line has few analysts (AZN.L for AZN, 0700.HK for TCEHY, GOOGL for GOOG, NOVO-B.CO for NVO, NESN.SW for NSRGY).
   The payout is *Dividends* or *Dividends + buybacks* (cheat sheet p. 2): the second adds the last fiscal year's buybacks per share to D0, and the stock report uses the sheet's choice. **Limitation:** Yahoo's growth is per share, so with buybacks in they count twice (in the payout and in the falling share count) and V0 is too high. The note next to g1 says so and gives the total growth without that effect; a flag repeats it in Summary.
3. **Refresh:** run the same command again, with `--as-of 2026-11-06` for the final numbers. Only the data cells change: your assumptions stay. Add `--g1-yahoo` to also reset g1 to the latest Yahoo estimate (then update the YAMLs).
   A dividend missing from Yahoo's history goes in `MISSING_DIVIDENDS` in the script, with its source (now AZN's interim of Aug 2026).
4. **Check the peers** (yellow, row 122 on). A new sheet takes them from the stock's YAML if it lists `peers`, else `PEERS` in the script (proposed by Claude on 6 Nov, not from Bloomberg), else Yahoo's industry list. Check them on Bloomberg `RV`, type over them, and change *Peers: source* once checked; a refresh keeps typed peers, and the stock report uses these. The comps choices (*Comps statistic*, *In the comps value*) are yellow too. A peer or a stock that reports in another currency gets its FCF (and, for the stock, EBITDA, revenue and net debt) converted to USD; Yahoo's own ratios are used as they are, so check those peers on `RV`. Banks (GS, AXP) have no EV/EBITDA or P/FCF, so their comps value rests on forward P/E.

The `Example NKE` sheet reproduces the TA notebook's Nike case (GGM 23.24, two-stage 29.78). `--new` starts a blank workbook and loses your edits. The stocks you keep then go through *Add a stock* above.

## The Round 2 report

`report/round2-equity.dc.html`: the cover, the Round 1 results (2 pages), six stock slots (2 pages each), Treynor-Black and the
new portfolio, the team. Write its text by hand; the numbers come from the runs. On 7–8 November, from the repo root:

1. **Round 1 results:** `python3 scripts/round1_performance.py --end 2026-11-06`. It writes `runs/round2/2026-11-06/round1_performance.json`
   with the website's calculations, and stops if they do not match `data/portfolio.json` or if the contributions do not add up.
2. **The workbook first:** `python3 scripts/build_ddm_workbook.py <TICKERS> --as-of 2026-11-06` (workbook closed in Excel), then set
   the yellow cells, save and close. Choose the stocks from its Summary. The workbook is the one place for the assumptions:
   each stock report takes its numbers from the stock's sheet (P0, D0 as used, β: the override or the 60-month β, rf from
   `Inputs` C7, the ERP, g1, T, g2, method, payout, peers and comps choices), so the report gives the workbook's value. It stops
   if the stock has no sheet or the sheet has prices of another date, and notes any number left in the YAML (not used).
3. **The stocks:** for each, `python3 scripts/build_stock_report.py <TICKER> --as-of 2026-11-06` (see *Add a stock*).
4. **The portfolio:** fill in `runs/round2/inputs/portfolio.yaml` (`te_target`, the tracking error to aim for, 4% as in the TA's
   notebook, and the `stocks` in report order), then `python3 scripts/build_round2_portfolio.py`. It follows the TA's notebook
   §6–§10, with our Round 1 SAA as passive portfolio and benchmark:
   - **Weights inside the active portfolio A:** w<sub>i</sub> ∝ α<sub>i</sub> / σ²(ε<sub>i</sub>).
   - **Size of A:** Treynor-Black's w<sub>A</sub>* (eqs. 11–12). The tracking error is w<sub>A</sub> × sd(R<sub>A</sub> − R<sub>S</sub>)√12, so
     w<sub>A</sub> is w<sub>A</sub>* pushed between the 2% floor and `te_target`.
   - **Positions:** every ETF goes to (1 − w<sub>A</sub>) × its SAA weight, each stock to w<sub>A</sub> × w<sub>i</sub>. Whole shares, rounded
     down; the rest is cash.

   The run stops, and says why, on a negative weight (never dropped or rescaled, unless `negative_weights: zero` applies the
   course rule: weight 0, raw weight shown and flagged, the others rescaled), weights that do not add up to 100%, a tracking
   error outside 2–5% after rounding, or inputs from different dates. It writes `portfolio.json` and `portfolio_for_PRTU.csv`
   (the shares to enter in Bloomberg PRTU).
5. **Promote** what the report uses: `python3 scripts/promote.py runs/round2/2026-11-06/round1_performance.json
   runs/round2/2026-11-06/portfolio.json runs/round2/2026-11-06/<TICKER>.dc.html …` (one page file per stock).
6. **Assemble and export:** `python3 scripts/build_round2_report.py --pdf`. It fills the marked blocks of the report, the stock
   slots (a slot without a stock shows the layout with placeholders) and the page numbers, writes
   `report/pdf/Matterhorn_Round2_Equity.pdf`, and stops if a page overflows.

## Replace by hand before submitting

Yahoo can't supply these, so they are typed by hand:

| Input | Where | Source |
|---|---|---|
| Equity risk premium, now 4.46% | `Inputs` C8 of `DDM_valuation.xlsx`: the reports read it | Damodaran, United States, 5 Jan 2026 (country risk premiums page) |
| ERP of a non-US company | The stock's sheet (typed by the script from `COUNTRY_ERP`) | Damodaran, same page: Switzerland 4.23%, UK, Taiwan and Hong Kong 5.01%, China 5.14% |
| First-stage growth g1 | The stock's sheet (the report reads it), source text in `valuation.g1_source` | Bloomberg LTG (long-term EPS growth), typed for the first 15 stocks on 6 Nov; Yahoo's next-year estimate for NVO, PFE, VZ, PEP, NSRGY |
| Peer set | The yellow peer cells of the stock's sheet (the report reads them) | Bloomberg `RV` |
| Optional: beta, forward EPS | β override of the stock's sheet (its source text in `valuation.beta_source`); forward EPS in `valuation.overrides` | Bloomberg `BETA`, `EE` |

## What the script computes

| Part | Method |
|---|---|
| Cost of equity | k = 10-year yield + β × ERP, with β on SPY over the last 60 complete months |
| DDM | Gordon and two-stage, the TA's formulas |
| Comparables | A double check only. Forward P/E, P/FCF (market cap ÷ last fiscal year's FCF) and EV/EBITDA, with the peer median and implied price. The comps value averages `comps_primary`. Other multiples are in the figures file only. The same code (`comps_from_snapshot`) fills the workbook's comps. A peer's FCF in another currency is converted at the price date (the rate is saved in `_data.json`) |
| Fair value | The DDM value. A stock with no dividend has no DDM, so it falls back on the comps, with a flag |
| Value-trap check | The TA's 6 metrics plus ROA, against the peer median and the stock's own past. Red flags plus falling earnings is Fail; either one is Watch |
| Alpha | α = p · α closed + (1 − p) · α never. p = 1 is the TA's α closed; p = 0 is α never |
| Risk on our SAA | β and σ²(ε) from the regression on **our** Round 1 weights (`data/holdings.json`) |

`runs/round2/<as-of>/<TICKER>_figures.json` has every number, including those the Checkpoint 1 page needs: α, σ²(ε), β on the SAA, IR.

## Files

| File | What it is |
|---|---|
| `scripts/build_stock_report.py` | The whole pipeline. `--selftest` checks it against the TA's numbers; `--refresh` downloads again |
| `scripts/build_ddm_workbook.py` | The screening workbook `runs/round2/inputs/DDM_valuation.xlsx`: builds it, adds stocks, refreshes their data |
| `report/templates/stock-report.dc.html` | The page layout. Change section order and page structure here |
| `runs/round2/inputs/` | One YAML per stock, plus the blank. Edit these |
| `runs/round2/<as-of>/` | One run: for each stock, a copy of the YAML it used, the saved download (`<TICKER>_data.json`, because Yahoo's ratios have no history) and the generated HTML, PDF and figures |
| `course/ta-code/`, `course/guidelines/AMC 2026 - Round 2 guidelines.pdf` | Course material |

The pages use `support.js` and `doc-page.js` from `report/runtime/`, so keep the repo layout. Needs Python with `yfinance`, `pandas`, `numpy` and `pyyaml`, plus Google Chrome for the PDF.
