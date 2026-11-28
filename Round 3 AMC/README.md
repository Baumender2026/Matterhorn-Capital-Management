# Round 3 · Quant and macro

The working folder for Round 3 of the AMC 2026: the quant sleeve (BABQM) and the macro sleeve (Strategy A, BNDX).

- **Deadline:** the report, the code and the portfolio description go to the TA by **Sun 29 Nov 2026, 23:59**.
- **Prices:** the trades are priced at the closes of **Fri 27 Nov 2026**.
- **Plan:** step numbers (A1, B7, …) refer to `Round 3 - Step-by-step plan (quant + macro).pdf` in this folder, which replaces the five-page quant plan.

## 1. Where things are

Paths are relative to this folder.

| What | Where |
|---|---|
| Plan (9 pages) | `Round 3 - Step-by-step plan (quant + macro).pdf` |
| Guidelines | `../course/guidelines/AMC 2026 - Round 3 guidelines.pdf` |
| Quant notebooks | `Quant/Strategy/01_bloomberg_data.ipynb` (data) · `Quant/Strategy/02_round3_lecture.ipynb` (strategy, sizing, trades) |
| Quant Bloomberg file | `Quant/Strategy/Bloomberg template/r3_bloomberg.xlsx`, saved as values to `Quant/Strategy/Data/r3_bloomberg_values.xlsx` |
| Quant trials | `Quant/Data/Tested Strategies.xlsx` · EQBT exports in `Quant/Data/Backtest/` |
| Macro notebooks | in `Macro/Macro TA - copy/`: `01_bloomberg_macro_data.ipynb` (data) · `03b_strategy_A_backtest.ipynb` (Strategy A, **traded**) · `04_strategy_B_countries.ipynb` (Strategy B, not traded) · `02_round3_macro_lecture.ipynb` (§5 sizing, §6 trades) |
| Macro Bloomberg file | `Macro/Macro TA - copy/Bloomberg template/r7_bloomberg.xlsx`, saved as values to `Macro/Macro TA - copy/Data/r7_bloomberg_values.xlsx` |
| Values-only copies (B4) | `save_bloomberg_values.py` |
| Market outlook | `Macro/Market_Outlook_27nov.xlsx` |
| Hand-off (B9) | `r3_prices.csv`, `r3_rf.csv`, `r3_portfolio.csv` from `Quant/Strategy/` to `Macro/Macro TA - copy/Data/` |
| Final trade list (PRTU) | `Macro/Macro TA - copy/r7_portfolio.csv` |
| Report (A7) | `report/round3-strategies.dc.html` (at the repo root): check and print with `scripts/check_report.py` |
| Superseded | `Macro/Macro TA - copy/03_strategy_A_regimes.ipynb`: its table uses the whole sample; 03b replaces it |
| TA originals (lectures and code) | class 6 and 7 slides, readings and exercises in `../course/slides/`; TA notebooks in `../course/ta-code/round3-quant/` and `../course/ta-code/round3-macro/` |

## 2. Decisions (28 Nov 2026)

### A1 · The macro strategy: Strategy A, all in BNDX

The macro sleeve holds one position: **BNDX** (Vanguard Total International Bond ETF, USD hedged).

- **Where the pick comes from:** the regime rule of `03b_strategy_A_backtest.ipynb`, main trial T2. Growth is "up" if the CFNAI 3-month average is above 0; inflation is "rising" if CPI y/y is above its level 12 months earlier. In each regime the rule holds the SAA asset class with the best past Sharpe, using only earlier months.
- **Today's reading:** Stagflation → BNDX (Sharpe 0.75, t = 2.0, 86 months).
- **Strategy B** (country value and momentum, `04_strategy_B_countries.ipynb`) is not traded.
- **In the code:** `PICKS = ["BNDX"]` at the top of macro 02 §5 (A3).

Sentences for the report (macro part):

> We implement Strategy A because it turns an observable macro view into a single liquid position with dated exit events. The view is stagflation: growth below trend (CFNAI 3-month average −0.05) and inflation rising (CPI 3.7 % y/y against 3.0 % a year earlier). The position is hedged global bonds, which lower the portfolio's risk in a month in which our outlook shows elevated stress (VIX 27.5 on 26 November, up 9.1 points in a month).
>
> We leave Strategy B out: country value and momentum did not beat an equal-weighted basket of the same 21 countries (Sharpe 0.44 against 0.45; mean information coefficient −0.004), and its top pick, Korea, would add a second semiconductor bet next to NVDA.
>
> The whole macro sleeve is in BNDX, the rule's single pick; splitting it with Strategy B would add the equity risk our regime view tells us to avoid.
>
> Neither candidate beat its benchmark in the backtest: Strategy A earned a Sharpe ratio of 0.51 against 0.59 for our SAA (0.25 after the ×0.5 discount), and the TA's own country strategy did not beat its benchmark either (0.37 against 0.46).

### A2 · The tracking-error split

The 7 % budget covers the Round 2 stocks, the quant sleeve and the macro sleeve together. Ex ante TE is measured against the SAA, on monthly USD returns over the last 60 months.

| Setting | Where | Value | Meaning |
|---|---|---|---|
| `TE_MAX` | quant 02 §0, macro 02 §0 | 0.07 | the Round 3 budget |
| `TE_QUANT` | quant 02 §0 | 0.05 | Round 2 stocks + quant sleeve, before the macro sleeve |
| `TE_TARGET` | macro 02 §0 | 0.065 | total target, with a 0.5 % buffer for price moves |
| `W_M_MAX` | macro 02 §0 | 0.20 | cap on the macro sleeve |

- **BNDX and the cap:** BNDX moves little against the SAA, so the 20 % cap should bind and the total TE end below 6.5 % (5.5 % in the TA's example). That is accepted.
- **Raising the cap** is a team decision, not something to tune.
- **The Round 2 stocks** (settled 27 Nov): NVDA, PEP, ABBV and DRI are kept at 2 % of the NAV each (`W_R2`, quant 02 §0), so w_A = 8 %. The reason for each one (catalyst, valuation) goes in report part 2.

### Working rules

- One person runs the laptop chain (section 3).
- Commit small, and run `git pull --rebase` before every push. The repository is public, and every push to `main` redeploys matterhorncapitalmanagement.com.

## 3. Owners

| Part of the report | Owner | With |
|---|---|---|
| Quant strategy + Checkpoint 1 | Filippo Selmi | Aaron Arauz |
| Macro strategy + Checkpoint 2 | Tommaso Rotondò | Elena Rocco |
| Round 2 performance | Giulia Musi | |
| Portfolio description and trades | Luca Di Pietro | |
| **Saturday laptop chain** (A8: quant 01 → quant 02 → hand-off → macro 01 → 03b and 04 → macro 02) | **Luca Di Pietro** | one person, so no file is overwritten halfway |

## 4. Saturday runbook (A8, Part B)

**Status on Sat 28 Nov, 16:00**
- The terminal steps B1–B4 are done. Filippo refreshed both templates on 28 Nov (end date 27 Nov) and saved the values copies with `save_bloomberg_values.py` (commit `740b7a2`).
- B5 is not done: `Macro/Market_Outlook_27nov.xlsx` still holds the 26 Nov values and has no formulas (its "Today" cell reads 26 Nov since Filippo's commit `c948a57`).
  - Bring the formula version, set "Today" to 27 Nov, refresh, and save a values copy.
  - If not, the report quotes the 26 Nov values and says so.
- A3 and A4 (macro 02, 03b, 04) are on `main`.
- The whole chain below was rehearsed on a scratch copy with the 27 Nov exports. It runs end to end: w_Q 34.0 %, w_M 20.0 % (capped), TE 5.14 %. These numbers are indicative until PORT has been checked (B6).

### People
- **Laptop chain:** Luca Di Pietro runs the whole chain, alone, so no file is overwritten halfway. Nobody else commits to `Round 3 AMC/` while it runs.
- **Terminal (B6, B14):**
  - Book the Bloomberg Lab.
  - For EQS/BEQS, log in with the account that saved the screen `AMC R3 BABQM` (BEQS only sees that account's private screens).
  - PORT and PRTU are needed on the account that owns the shared portfolio.
- If a refresh has to be redone, refresh all three workbooks in the same session: `Quant/Strategy/Bloomberg template/r3_bloomberg.xlsx`, `Macro/Macro TA - copy/Bloomberg template/r7_bloomberg.xlsx` and `Macro/Market_Outlook_27nov.xlsx`.
  - B3 check: compare the last price of TIP or GLD in the two values files. Not SPY: the quant Live sheet has no SPY. `save_bloomberg_values.py` already prints this comparison.
  - The quant values file goes to `Quant/Strategy/Data/`. The script creates that folder.
- For the A6 caveat on the terminal: `LEGATRUH Index DES`. Is it the Global Aggregate including USD bonds? BNDX holds only non-USD bonds.

### B6 · PORT (terminal), before the laptop chain
Note:
- the shares of every position and the cash, to compare with `OLD_SHARES` and `CASH_R2` (quant 02 §0, now the Round 2 entry of 8 Nov);
- the NAV at the 27 Nov close (our website shows USD 96,827,577);
- the Round 2 performance from 6 to 27 Nov: return, volatility, Sharpe, the portfolio against the SAA alone, and the attribution. Export or screenshot them for Giulia (report pages 9–10).

### The laptop chain, in this order: quant 01 → quant 02 → hand-off → macro 01 → 03b and 04 → macro 02
`git pull` first. On each notebook: Restart & Run All, then save it with its outputs.

**1. Quant 01 (B7)** writes `r3_holdings.csv`, `r3_prices.csv` and `r3_rf.csv`.
- CHECK: "screen 'AMC R3 BABQM', prices to Fri 27 Nov 2026"; 29 stocks (rehearsal); no missing price; no unknown sector (a "?" goes in `SECTOR_BY_HAND`); score 98–100; T-bill loaded.

**2. Quant 02 (B8).** First set `OLD_SHARES` and `CASH_R2` from PORT (B6), and delete the two "⚠️ check … PORT" comments (§0 and §7). Check `W_R2` (2 % each) and `TE_QUANT` (0.05).
- CHECK §6: the sector warning (above 40 %: accept it and say so in the report, or cap the sector, which counts as one more trial) and any overlap with the Round 2 stocks.
- CHECK §7: NAV close to PORT; TE close to 5 % (rehearsal 4.94 %); volatility and VaR next to the SAA's.
- CHECK §8: `r3_portfolio.csv` written, TE below 7 %.

**3. Hand-off (B9).** From the repo root:
```
cp "Round 3 AMC/Quant/Strategy/"r3_{prices,rf,portfolio}.csv "Round 3 AMC/Macro/Macro TA - copy/Data/"
head -1 "Round 3 AMC/Macro/Macro TA - copy/Data/r3_prices.csv"
```
- CHECK: the first line lists VTI … BCI and NVDA, PEP, ABBV, DRI, not SPY … DBC and GIS.

**4. Macro 01 (B10)** rewrites the `r7_*.csv` from the new values file.
- CHECK: the data end in October (the 27 Nov export has no November row); country ETFs 21 series, P/B for all 21; "holes" 0; months with |return| > 40 %: 0; "Live prices: 36 of 36".

**5. 03b and 04 (B11).**
- CHECK 03b: "Regime for the trade month (November 2026), from the data of October 2026"; T2 → Stagflation; "Pick: BNDX (Sharpe 0.75, t = 2.0, 86 months)".
  - If the pick changes, follow the rule (it was fixed in advance): set `PICKS` in macro 02 §5 and tell Tommaso and Elena.
- CHECK 04: for the record only, since Strategy B is not traded: "decision row 30 Nov 2026"; EWA, EWJ, EWH, EWY.

**6. Macro 02 (B12)**, §5 sizing and §6 trades.
- CHECK §5:
  - "Months used: 60 (Nov 2021 - Oct 2026)": compare it yourself with the 60 months of quant 02 §7; they must be the same. With BNDX alone the notebook cannot check it.
  - w_A = 8.0 %; "TE before macro" close to `TE_QUANT`.
  - "we invest w_M = 20.0% of the NAV (BNDX 20.0%) … (capped by W_M_MAX)".
  - TE with macro at most 6.5 % (rehearsal 5.14 %).
  - The table of volatility, 1-month 5 % VaR and TE for the SAA, before macro and with macro.
- CHECK §6:
  - NAV equal to PORT's; `r7_portfolio.csv` written.
  - "Weight by sleeve": SAA, Round 2 (0.08), Quant (w_Q), and "SAA + Macro", the BNDX row, which holds BNDX's SAA weight plus w_M.
  - "Macro sleeve: w_M = 20.0% of the NAV in BNDX".

**7. Commit and push** the run in one commit, after `git pull --rebase`: the six notebooks with their outputs, `Quant/Strategy/r3_*.csv`, `Macro/Macro TA - copy/r7_*.csv`, `Macro/Macro TA - copy/Data/r3_*.csv` and `Macro/Macro TA - copy/r7_portfolio.csv`.

### B13 · Check the trade list (team) on `Macro/Macro TA - copy/r7_portfolio.csv`, before PRTU
- Shares × price + cash = NAV; the weights add up to 100 %; the cash is positive and small.
- Every SAA ETF sits at the same fraction of its SAA weight, **except BNDX**. BNDX = that fraction × 16.48 % + w_M, in one row labelled "SAA + Macro".
- The `sleeve` column reads "Round 2" for NVDA, PEP, ABBV and DRI ("Round 2 + Quant" if quant 02 §6 flagged an overlap) and "Quant" for the screen stocks.
- Closed positions have 0 shares; no share count is negative; tickers are in Bloomberg format; `price date` is 2026-11-27 on every position.

### B14 · PRTU (terminal, Saturday or Sunday)
- Update the existing portfolio. Do not create a new one, so the performance history is kept.
- Enter the new share counts of `r7_portfolio.csv`: the SAA, Round 2, quant and macro trades together, at the 27 Nov closes.
- CHECK in PORT: every holding equals the file, the cash is right, and the portfolio is still shared with the TA. After this the portfolio cannot change until 27 Dec.

### Before sending (Part C, Sunday)
- Report:
  - `grep -nE '<div data-draft|\[TO FILL' report/round3-strategies.dc.html` must print nothing.
  - Then `python3 scripts/check_report.py report/round3-strategies.dc.html --pdf report/pdf/Matterhorn_Round3_Strategies.pdf` must report no overflow.
- Notebooks (C4): all six re-run and saved with outputs, and no ⚠️ printed in any output. A printed ⚠️ is a problem to fix or explain.
- `03_strategy_A_regimes.ipynb` is superseded by 03b: leave it out of the delivery (C5).
