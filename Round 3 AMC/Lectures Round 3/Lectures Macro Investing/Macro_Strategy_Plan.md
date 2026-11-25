# AMC Round 3 – Macro Strategy Plan

Nov 25, 2026 · @Elena

A minimal plan for the macro part of Round 3, built on the TA's macro notebook: six steps, each with a short task list, the tool to use and an Owner column.

## What we must deliver

- **A macro strategy** (yield curve, currencies, commodities, country value and momentum, or a global theme), long-only, inside the 7% tracking-error budget together with the quant sleeve and the Round 2 stocks we keep.
- **In the report:** why it should pay in the coming weeks, whether as a compensation for risk or a behavioural bias, and its risks.
- **The macro page (Checkpoint 2):** the view, the instruments, what happens if the regime changes, the event that would make us exit.
- **The trades:** portfolio description, TE, volatility and VaR against the SAA, entry in PRTU on 28–29 November.

## How the TA code works

The TA macro folder (`Round 3 - Macro`) is a three-stage pipeline, and the quant folder of TA session 6 has the same shape:

1. **Bloomberg Excel file** (`Bloomberg template/r7_bloomberg.xlsx`). It contains only formulas (`BDH` for monthly histories, `BDP` for today's values), one sheet per type of data:
   - Macro: PMI, CPI, T-bill, Fed funds;
   - Assets: long-history indices of the SAA asset classes;
   - Countries and Value: 18 country ETFs and their P/B;
   - Live: today's prices;
   - Rates: policy rates.

   On the terminal you refresh it and save a values-only copy as `Data/r7_bloomberg_values.xlsx`, which then works on any computer.
2. **Notebook 01** (`01_bloomberg_macro_data.ipynb`) only handles data. It reads that file and the carry data (`Data/DataPython.xlsx`), aligns every series on month-ends, prints checks (missing months, suspicious returns, P/B range) and writes the clean `r7_*.csv` files.
3. **Notebook 02** (`02_round3_macro_lecture.ipynb`) reads only the CSVs and does the analysis:
   - §2 classifies each month into four regimes (PMI above 50 = growth up; CPI y/y above a year earlier = inflation rising) and measures how each asset class did in the following month;
   - §3 ranks the 18 countries on value and momentum and backtests buying the top 4, with a validation period and the Sharpe discount;
   - §4 measures the currency carry trade on 1980–2014 data and today's rate gaps;
   - §5 sizes the macro sleeve so that the total tracking error stays within the budget;
   - §6 turns the weights into shares and trades (`r7_portfolio.csv`).

Notebook 02 also needs the output of the quant pipeline (`Data/r3_*.csv`: prices, T-bill, portfolio with the quant sleeve), because §5 sizes the macro sleeve on top of it. All the CSV files are already in the folder, with data to October 2026, so Notebook 02 runs without a terminal.

## Deadlines

Everything has to be finished by Sunday night, and the presentation follows two days later. After that the portfolio is frozen for a month, which is why the macro view must be one that can hold without adjustments until 27 December.

| Date | What happens | What it means for the macro sleeve |
| --- | --- | --- |
| Nov 27, 2026 (Fri) | Bloomberg prices the new positions at this day's close | Share counts use these closes; the signal can only use data published by then |
| Nov 28, 2026 – Sun 29 Nov | Enter the new positions with `PRTU`, updating the existing portfolio (not a new one) | Macro and quant trades go in together |
| Nov 29, 2026, 23:59 | Report, code and portfolio description by e-mail to the TA (riccardo.croci@usi.ch), and on our website. Same deadline for all groups | The macro page and the strategy analysis must be final |
| Dec 1, 2026, 11:00, room 253 | Presentations of groups 1–5, so ours (group 3): about 10 minutes, all members | Performance of Round 2 first, then the two strategies |
| Dec 3, 2026, 13:30, SI-008 | Presentations of the other groups | We are expected to ask questions and challenge them |
| Until Dec 27, 2026 | The portfolio cannot change | The exit condition on the macro page is stated, but we cannot trade on it before the end |

Source: *AMC 2026 – Round 3 guidelines*, sections 1, 5, 6 and 7.

## The plan

First we decide what makes sense to test, then we download all the data in one go, then we test everything with the same code.

### Step 1 – Decide what to test (tasks in parallel)

This comes first because some variations need data the TA's file does not have.

| Task | How | Owner |
| --- | --- | --- |
| Read the TA results | Already saved in Notebook 02, nothing to run: §2 regime today and the best asset in it; §3 top 4 countries and backtest against all countries; §4 carry: past Sharpe and skewness, currencies paying more than USD |  |
| December check | Regime: consensus for the November PMI (1 Dec) and CPI (mid-Dec) against the two thresholds (`ECO`), Cleveland Fed nowcast. Carry: next move of the high-rate central bank (`WIRP`), `VIX Index`. Countries: events in the month, `DXY Curncy`, overlap with NVDA. Fed: `WIRP`. Calendar of dated events 27 Nov – 27 Dec |  |
| Regime models | Deep research with the prompt below; plus the Class 7 alternative (CFNAI for growth, change in inflation, each against the median of past months only) |  |
| Country variations | Universe: the `COUNTRIES` dictionary of Notebook 01 (the TA picked 18 markets with data from 2001; e.g. add INDA, MCHI, with shorter history). Signal: 12-1 momentum, another valuation measure of the MSCI index (e.g. dividend yield). Number of countries bought |  |
| Correct the TA code | On the TA's CSVs already in the folder, no terminal needed. Notebook 02: W\_SAA = our weights; in §5, A\_TICK = the Round 2 stocks we keep; replace the §2 table with the code below (each month uses only earlier months); add the 2002–2013 / 2014–2026 split to the regime, as §3 does; keep the timing (shift(1) on macro data, shift(-1) on returns). The same code will run on our data in step 3 |  |
| Decide the list | Decide which strategies and which variations each, with the reason, written in the trials log before running anything; list the data they need |  |

**Notes for this step**

- **Publication lag (correcting the code).** Bloomberg dates October CPI 31 October, but it comes out in mid-November. A backtest that used it on 31 October would trade on news nobody had yet. The TA avoids this by lagging the macro data one month (`shift(1)`) and applying the signal to the following month's return (`shift(-1)`): keep both in every version.
- **The regime table (correcting the code).** §2 picks the best asset in each regime using all months up to 2026, including months that were still in the future at the time, so it cannot be used as evidence; the code below replaces it. The TA's fixed thresholds (PMI 50, CPI against a year earlier) are fine; a median over the whole sample, as in the Class 7 exercise, would use the future, so any median must come from past months only.
- **Count the trials (deciding the list).** Every strategy or variation we run goes in the trials log, and the report gives the count, as Class 4 asks: with 20 variations and no real effect, about one looks significant by luck. That is why the list is fixed, with reasons, before anything runs.

Code that replaces the §2 regime table. It assumes `Re` has one column per SAA ETF ticker (skip the TA's renaming to plain names) and uses `regime` from §2, whose row t is the regime known at the end of month t:

```python
nxt = Re.shift(-1).loc[regime.index]      # row t = excess return of month t+1, as in TA §2
MIN_N = 24                                # months needed in a regime before trusting its Sharpe
pick = {}
for i, t in enumerate(regime.index):
    past = nxt.iloc[:i]                   # rows before t: their next-month return is known at t
    same = past[regime.iloc[:i].values == regime.iloc[i]]
    if len(same) >= MIN_N:
        pick[t] = (same.mean() / same.std()).idxmax()
pick = pd.Series(pick)
ret = pd.Series({t: nxt.loc[t, a] for t, a in pick.items()})
saa = (nxt[list(W_SAA.index)] @ W_SAA).loc[ret.index]
ret.index = saa.index = ret.index + pd.offsets.MonthEnd(1)   # date each return by the month it is earned
ok = saa.notna()                          # the SAA needs all its indices (TIP starts in 1997)
print(stats(ret[ok], 0 * ret[ok], saa[ok]))   # returns are already in excess of the T-bill
```

Deep-research prompt for the regime models:

```text
We classify each month into four macro regimes (growth up/down x inflation rising/falling) using the US ISM manufacturing PMI above 50 and CPI y/y above its level 12 months earlier, lagged one month for publication, and tilt a long-only multi-asset portfolio toward the asset class with the best historical Sharpe ratio in the current regime, rebalanced monthly. Review the academic and practitioner literature on better ways to classify growth/inflation regimes for monthly asset allocation: indicators (PMI, Chicago Fed National Activity Index, nowcasts, core vs headline CPI, inflation surprises), levels vs changes, thresholds, probabilistic or Markov-switching models, and the effect of real-time data (publication lags, revisions). For each method: out-of-sample evidence at a 1-month horizon and whether it can be implemented with monthly data in pandas. Cite papers and practitioner research with links. End with the two or three simplest improvements worth testing.
```

### Step 2 – Download all the data at once (terminal)

| Task | How | Owner |
| --- | --- | --- |
| Bloomberg | `r7_bloomberg.xlsx`: Assets sheet with the indices of our SAA (benchmark from `DES` of VTI, VEA, IEMG, BND, BNDX; TIP, GLD and BCI are already there); one column pair (BDH, `Per=M`) for each extra series on the list of step 1. Refresh, save as values in `Data/r7_bloomberg_values.xlsx` |  |
| Clean | Notebook 01 (`pip install openpyxl` first): add the new tickers to its dictionaries (`COUNTRIES`, `ASSETS`, `MACRO`), run all, check that "holes" are 0 |  |

**Notes for this step**

- **Indices as proxies.** The SAA ETFs start in the 2000s, too late to see many months in each regime, so the Assets sheet uses the indices behind them, which go back to 1990. They have no fees and sometimes a different currency hedge: name each one in the report.
- **Revised data.** Bloomberg history shows today's revised figures, not those known at the time. It hardly matters for CPI and little for PMI, but GDP is revised heavily: if a variation uses GDP (e.g. a Taylor-rule signal), take first-release data from ALFRED, or use the unemployment gap, which is barely revised.

### Step 3 – Test everything with correct methods

| Task | How | Owner |
| --- | --- | --- |
| Run the TA's versions | The code corrected in step 1, on the data of step 2 |  |
| Run the variations | Regime: each rule of step 1 as a small function that returns the monthly regime, through the same code. Countries: §3 code with each universe or signal of step 1 |  |
| Validation and discount | Tuning 2002–2013, test 2014–2026; Sharpe ÷ 2; every run in the trials log |  |

**Notes for this step**

- **Look at the test period once.** Going back and forth between tuning and test turns the test period into a second tuning period, and the result stops meaning anything.
- **The discount.** Report the backtest Sharpe and half of it as the realistic figure, with a larger cut if the trials log is long.
- **A weak result reported honestly is fine**: the TA's own country strategy lost to its benchmark (Sharpe 0.37 against 0.46).

### Step 4 – Choose

| Task | How | Owner |
| --- | --- | --- |
| Strategy (one or more), instruments, split | What worked in the test period (step 3), whose signal holds in December (step 1), with little overlap with the quant and Round 2 stocks |  |
| Chain from view to position, and rationale | TA Notebook 02 §1 cards; Class 7 reading; Pedersen, *Efficiently Inefficient*, for carry |  |

### Step 5 – Size and trade

| Task | How | Owner |
| --- | --- | --- |
| Inputs from the quant strategy team | TE target, Round 2 stocks kept, files `r3_prices.csv`, `r3_rf.csv`, `r3_portfolio.csv` |  |
| Size | Notebook 02 §5 with `PICKS` = our instruments and `A_TICK` = the Round 2 stocks kept: it gives the macro weight within the TE target (TA: 6.5%) and the table of volatility, VaR and TE |  |
| Trades and portfolio description | §6 with the NAV from `PORT`; add ISIN (`ID_ISIN`) and price date; one table with the quant trades |  |
| Enter the trades | `PRTU`, Sat 28 or Sun 29 Nov, updating the existing portfolio |  |

### Step 6 – Write

| Task | How | Owner |
| --- | --- | --- |
| Strategy analysis | Why it should pay in the coming weeks (December check, step 1), risk or behavioural (step 4), the risks |  |
| Macro page | View, instruments, risk (state the skewness for carry), exit event from the calendar of step 1. The portfolio cannot change before 27 December, so the exit event is the one that would prove the view wrong |  |
| Slides | Market outlook = our view; 2–3 slides on the strategy |  |
