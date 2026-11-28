# AMC 2026 – Round 3: our quant strategy (BABQM)

Matterhorn Capital Management · Group 3 · built on the TA session 6 folder (`Round 3 - iCorsi`, kept in `course/ta-code/round3-quant/`)

**BABQM** buys the top 2% of the Russell 1000 on a score that averages three percentile ranks with equal weights: **low beta** (beta against the S&P 500), **quality** (return on assets, last 12 months) and **momentum** (12-1 month total return). The stocks are equal-weighted and rebalanced monthly. The full EQS formula (EXP1–EXP10) is in notebook 02, §2. In the challenge we buy them with the closes of Friday 27 November and hold them until 27 December. The EQS screen is `AMC R3 BABQM` and the EQBT model is `AMC R3 BABQM BT`.

## Steps

1. **Backtest (done).** Our EQBT exports are in `../Data/Backtest/`, and the list of every backtest we ran is `../Data/Tested Strategies.xlsx`. Notebook 01 reads both where they are.
2. **Bloomberg refresh (Saturday 28 November, on the terminal).** Open `Bloomberg template/r3_bloomberg.xlsx`. It already holds our screen name, SAA ETFs and Round 2 stocks. Log in with the account that saved the screen, since BEQS only sees that account's private screens. Refresh, wait until no cell shows "Requesting Data", and check that Settings!B3 is 27 Nov 2026. Then save a copy with values only as `Data/r3_bloomberg_values.xlsx`.
3. **Notebook 01** (`01_bloomberg_data.ipynb`) writes the CSVs. It stops at §2 if the Bloomberg file is missing or was not refreshed with `AMC R3 BABQM`.
4. **Notebook 02** (`02_round3_lecture.ipynb`) covers Checkpoint 1 (§1–§5), today's stocks (§6), the TE sizing (§7) and the trades (§8). §1–§5 already run, because they need only the backtest.
5. **Macro.** Copy `r3_prices.csv`, `r3_rf.csv` and `r3_portfolio.csv` into the macro notebook's `Data/` folder. The macro notebook adds its sleeve on top and writes the final trades for PRTU.

## Settled on 27 November

| Setting | Where | Decision |
|---|---|---|
| `W_R2` | §0 | all four Round 2 stocks kept, each at **2% of the NAV** (8% together); 0 would close one |
| `N_EXTRA` | §0 | 0: every backtest we ran is in the trials log (9) |
| formula lines | §1–§2 | adjusted beta vs S&P 500 (`EQY_BETA`), ROA (LTM), 12-1 month return, equal weights, score rank ≥ 98 |

## Before the final run (⚠️ in notebook 02)

| Setting | Where | What to do |
|---|---|---|
| `OLD_SHARES`, `CASH_R2` | §0 | check against PORT (now: the Round 2 entry of 8 Nov) |
| `TE_QUANT` | §0 | TE of Round 2 + quant before macro (5%, the TA's split of the 7% budget) |
| "why now" | §1d | our view for the month |

## Files

| File | What it is |
|---|---|
| `01_bloomberg_data.ipynb` | Reads the Bloomberg files and writes the CSVs |
| `02_round3_lecture.ipynb` | Checkpoint 1, sizing and trades, from the CSVs |
| `r3_backtest.csv`, `r3_trials.csv` | Written by notebook 01, §1 (ours) |
| `r3_holdings.csv`, `r3_prices.csv` | Written by notebook 01, §2–§3, after the Saturday refresh |
| `r3_rf.csv` | The 1-month T-bill, written by notebook 01, §3. Until Saturday it is the TA's download (the same market data for everyone), which notebook 02 §3–§5 needs |
| `r3_portfolio.csv` | Written by notebook 02, §8: weights, shares and trades, with a `sleeve` column (SAA, Round 2, Quant) |
| `Bloomberg template/r3_bloomberg.xlsx` | The template to refresh on the terminal |
| `Data/` | The terminal file `r3_bloomberg_values.xlsx` (empty until Saturday) |
| `AMC 2026 Round 3 - Quant strategy in Bloomberg.pdf` | The TA's step-by-step guide |

## Requirements

Python 3 with `pandas`, `numpy`, `matplotlib` and `openpyxl`.
