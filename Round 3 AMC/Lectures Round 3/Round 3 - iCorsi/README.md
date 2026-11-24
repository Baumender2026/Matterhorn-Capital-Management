# AMC 2026 – Round 3: Quant strategy in Bloomberg

Financial Modeling (USI) · TA session 6

This folder contains a **worked example** of the Round 3 quantitative strategy.
You can rerun it without a Bloomberg terminal, then repeat the same steps with your own screen.

## What we did

1. **Screen (EQS).** We built the screen "AMC R3 VMQ". Each stock gets a score on value, momentum and quality, and we keep the stocks with the highest scores.
2. **Backtest (EQBT).** We tested the screen over history, with monthly rebalancing, against the Russell 1000. We also tested each factor on its own.
3. **Data (Excel).** We used `r3_bloomberg.xlsx` on the terminal to download the stocks of the screen, their monthly prices, the SAA ETFs, the Round 2 stocks and the T-bill rate. After the refresh, we saved a copy as values.
4. **Notebook 01.** It reads the Bloomberg files, cleans and checks them, and saves the CSV files.
5. **Notebook 02.** It analyses the backtest, measures the tracking error, sizes the quant sleeve (total TE at most 7%, target around 5%) and builds the trade list.

## Files

| File | What it is |
|---|---|
| `AMC 2026 Round 3 - Quant strategy in Bloomberg.pdf` | Step-by-step guide. Start here. |
| `01_bloomberg_data.ipynb` | Reads the Bloomberg files and writes the CSVs. |
| `02_round3_lecture.ipynb` | Builds the Round 3 portfolio from the CSVs. |
| `r3_*.csv` | Clean data written by Notebook 01. Notebook 02 uses them. |
| `Data/` | Our Bloomberg exports: the EQBT backtests, the EQS holdings, and `r3_bloomberg_values.xlsx` (our Excel template after the refresh, saved as values). |
| `Bloomberg template/r3_bloomberg.xlsx` | Empty template to fill on the terminal with **your** screen. |

## How to use it

**To rerun our example:** open `02_round3_lecture.ipynb` and run all cells. The CSVs are already here, so you only need Python.

**To do it with your own strategy:**
1. Build and save your screen in EQS, then backtest it in EQBT and export the returns to Excel.
2. On the terminal, open `Bloomberg template/r3_bloomberg.xlsx`. Type your screen name in **Settings**, cell B4, and paste your EQBT returns in the **Backtest** sheet.
3. Refresh. Wait until no cell shows "Requesting Data", then save a copy as values.
4. Put your files in `Data/` with the same names, then run Notebook 01 and Notebook 02.

## Requirements

Python 3 with `pandas`, `numpy`, `matplotlib` and `openpyxl`.
