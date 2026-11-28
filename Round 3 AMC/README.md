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
| Guidelines | `AMC 2026 - Round 3 guidelines.pdf` |
| Quant notebooks | `Quant/Strategy/01_bloomberg_data.ipynb` (data) · `Quant/Strategy/02_round3_lecture.ipynb` (strategy, sizing, trades) |
| Quant Bloomberg file | `Quant/Strategy/Bloomberg template/r3_bloomberg.xlsx`, saved as values to `Quant/Strategy/Data/r3_bloomberg_values.xlsx` |
| Quant trials | `Quant/Data/Tested Strategies.xlsx` · EQBT exports in `Quant/Data/Backtest/` |
| Macro notebooks | in `Macro/Macro TA - copy/`: `01_bloomberg_macro_data.ipynb` (data) · `03b_strategy_A_backtest.ipynb` (Strategy A, **traded**) · `04_strategy_B_countries.ipynb` (Strategy B, not traded) · `02_round3_macro_lecture.ipynb` (§5 sizing, §6 trades) |
| Macro Bloomberg file | `Macro/Macro TA - copy/Bloomberg template/r7_bloomberg.xlsx`, saved as values to `Macro/Macro TA - copy/Data/r7_bloomberg_values.xlsx` |
| Values-only copies (B4) | `save_bloomberg_values.py` |
| Market outlook | `Macro/Market_Outlook_27nov.xlsx` |
| Hand-off (B9) | `r3_prices.csv`, `r3_rf.csv`, `r3_portfolio.csv` from `Quant/Strategy/` to `Macro/Macro TA - copy/Data/` |
| Final trade list (PRTU) | `Macro/Macro TA - copy/r7_portfolio.csv` |
| Superseded | `Macro/Macro TA - copy/03_strategy_A_regimes.ipynb`: its table uses the whole sample; 03b replaces it |
| TA originals (lectures and code) | `Lectures Round 3/` |

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
