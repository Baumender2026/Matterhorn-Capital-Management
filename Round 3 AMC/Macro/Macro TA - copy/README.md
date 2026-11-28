# AMC 2026 – Round 3: the macro strategy

Financial Modeling (USI) · TA session 7 · continues TA session 6 (the quant strategy)

> **Matterhorn Capital Management (Group 3): our copy of the TA's folder.** Our macro position is Strategy A, the regime rule of `03b_strategy_A_backtest.ipynb` (pick: BNDX), set in `02_round3_macro_lecture.ipynb` §5 (`PICKS`). Run order: `01_bloomberg_macro_data.ipynb` → `03b_strategy_A_backtest.ipynb` and `04_strategy_B_countries.ipynb` (Strategy B, country value and momentum, not traded) → `02_round3_macro_lecture.ipynb`. `03_strategy_A_regimes.ipynb` is superseded by 03b. Decisions, owners and the Saturday runbook: `../../README.md`. The TA's original folder is in `course/ta-code/round3-macro/`.

## What we do
1. **Menu (§1).** Examples of macro strategies you can run long-only: regime tilt, rate cycle, yield curve, commodities, country value & momentum, carry, thematic.
2. **Regimes (§2).** Classify each month by growth (ISM PMI) and inflation (CPI), and see which SAA asset class wins in each environment.
3. **Country value & momentum (§3).** Our TA example: buy the 4 iShares MSCI country ETFs with the best value + momentum score. Backtest with the Class 4 protocol.
4. **Carry (§4).** The *Efficiently Inefficient* exercise: Sharpe, skewness and drawdowns of the currency carry trade, long-short and long-only.
5. **Sizing and trades (§5–6).** Add the macro sleeve to the Round 3 portfolio of TA session 6, inside the TE budget (≤ 7%): TE² with the three bets (Round 2 stock, quant, macro) and their correlations.

## Files
| File | What it is |
|---|---|
| `Bloomberg template/r7_bloomberg.xlsx` | BDH/BDP formulas to refresh on the terminal |
| `01_bloomberg_macro_data.ipynb` | Reads the Bloomberg file, checks it, writes the `r7_*.csv` files |
| `02_round3_macro_lecture.ipynb` | The lecture: §1–§6 |
| `Data/r3_*.csv` | The output of TA session 6 (Round 3 portfolio with the quant sleeve) |
| `Data/DataPython.xlsx` | Carry data (9 currencies, 1980–2014) |
| `Data/r7_bloomberg_values.xlsx` | The Bloomberg template refreshed and saved as values (our data) |
| `r7_*.csv` | Clean data written by Notebook 01: Notebook 02 runs from these, without Bloomberg |

## How to run it
1. On the terminal, open `Bloomberg template/r7_bloomberg.xlsx`, check the dates in **Settings**, refresh, wait until no cell shows "Requesting Data".
2. Save a copy **as values** in `Data/r7_bloomberg_values.xlsx`.
3. Run Notebook 01, then Notebook 02.

No Bloomberg access? Skip steps 1–3 and run Notebook 02 directly: the `r7_*.csv` files are included.

Python 3 with `pandas`, `numpy`, `matplotlib` and `openpyxl`.
