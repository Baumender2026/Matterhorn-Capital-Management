# AMC Round 3 – Macro Strategy Plan

Nov 25, 2026 · @Elena

A minimal plan for the macro part of Round 3, built on the TA's macro notebook: six steps, each with a short task list, the tool to use and an Owner field.

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

- **Forward-looking macro analysis (27 Nov – 27 Dec)** — Owner:
  - Regime: consensus for the November PMI (1 Dec) and CPI (mid-Dec) against the two thresholds (`ECO`); Cleveland Fed nowcast.
  - Carry: next move of the high-rate central bank (`WIRP`); `VIX Index`.
  - Countries: events in the month; `DXY Curncy`; overlap with NVDA.
  - Fed: `WIRP`.
  - Calendar of dated events 27 Nov – 27 Dec.
- **Regime strategy** — Owner:
  - Our indicators: CPI for inflation; for growth, PMI or an alternative from the literature (e.g. CFNAI, used in the Class 7 slides, whose sources we can reuse).
  - Method for which assets perform in which regime: deep research with the prompt below, plus the sources of the Class 7 slides.
  - The regime-change signal: the threshold each indicator must cross, checked against the consensus and nowcasts for the next prints (forward-looking macro analysis).
- **Country value and momentum** — Owner:
  - The TA ranks all 18 markets (the `COUNTRIES` dictionary of Notebook 01, data from 2001) and buys the top 4, already long-only.
  - Our universe: MSCI classification (Developed + Emerging), keeping the countries with a liquid iShares country ETF and enough history. Not the OECD list, which leaves out China, India and Taiwan (more than half of MSCI EM), plus Brazil, South Africa, Saudi Arabia and Indonesia.
  - Start from the TA's 18 (which already include Brazil and Taiwan) and add the main missing EM: China (MCHI), India (INDA), South Africa (EZA). Check each ETF's start date on the terminal: MCHI and INDA start only in 2011–2012, so their backtest is shorter.
  - Their ETF data are downloaded in step 2.
  - Use the TA's signals (12-month momentum, P/B).
  - Decide how to handle a missing P/B (the TA falls back on momentum only).
  - Decide how to correct the sector bias of P/B (see notes).
- **Carry** — Owner:
  - Low priority. Long-only, we do not earn the rate gap: we hold a high-rate currency (e.g. AUD through FXA) and earn its rate plus its move against the dollar.
  - On the TA's data only AUD pays more than USD, by 0.85% a year (0.07% a month), so the position is in practice a bet on the AUD.
  - Currencies to watch: the TA's G10 (US, Eurozone, Japan, UK, Canada, Australia, New Zealand, Sweden, Switzerland) plus the high-rate EM in our country universe (Brazil, Mexico, South Africa, India). Japan matters also as a risk: the yen funds carry trades, so a BoJ hike can trigger an unwind.
  - For each: rates (policy rate today and the next expected move, `WIRP`), which give what carry earns; FX (trend against the dollar over 1 and 3 months), which is the risk of losing it.
  - Instruments: G10 currency ETFs (FXA, FXE, FXY, …); for EM only basket currency ETFs or local-currency bond ETFs, or indirectly through the country ETFs, which already carry the currency.
- **Rates and inflation (if we want them)** — Owner:
  - The TA has only the cards of §1b, no code: decide the rule and how to test it.
  - Rates, e.g.: when the Taylor-rule rate is above Fed funds, underweight duration (SHY instead of IEF, or an inverse Treasury ETF).
  - Inflation, e.g.: when CPI y/y is above a year earlier, overweight commodities, TIPS and gold against nominal bonds (close to the regime strategy).
  - List the data they need.
- **Thematic strategies (any model allowed, per the tutor)** — Owner:
  - Order: market outlook → 2–3 candidate themes → literature for each → one rule per theme → backtest in step 3.
  - From the outlook workbook (Bloomberg), list the themes that the data support for 27 Nov – 27 Dec (e.g. a sector or region driven by rates, the dollar, commodities or AI capex), each with the data point behind it.
  - For each theme, deep research with the prompt below: which signal has out-of-sample evidence at a 1-month horizon.
  - Write the rule as for the other strategies: signal, threshold, instrument, when it is in or out. E.g. hold the theme ETF when its 12-month momentum against SPY is positive and the macro driver points the same way, otherwise hold the SAA.
  - Instrument: a liquid theme or sector ETF (Live sheet). Check its start date: many theme ETFs begin after 2015, so use the sector index behind it for the backtest, and name the proxy.
  - Check the overlap with the stocks we already hold (e.g. NVDA in an AI or semiconductor theme): the same bet twice adds risk, not diversification.
  - List the data they need (step 2, Extra sheet).
- **Correct the TA code** — Owner:
  - On the TA's CSVs already in the folder, no terminal needed.
  - Notebook 02: `W_SAA` = our weights; in §5, `A_TICK` = the Round 2 stocks we keep.
  - Replace the §2 table with the code below (each month uses only earlier months).
  - Add the 2002–2013 / 2014–2026 split to the regime, as §3 does.
  - Keep the timing (`shift(1)` on macro data, `shift(-1)` on returns).
  - The same code will run on our data in step 3.
- **Decide the list** — Owner:
  - Decide which strategies and which variations each, with the reason, written in the trials log before running anything.
  - List the data they need.

**Notes for this step**

- **Publication lag (correcting the code).** Bloomberg dates October CPI 31 October, but it comes out in mid-November. A backtest that used it on 31 October would trade on news nobody had yet. The TA avoids this by lagging the macro data one month (`shift(1)`) and applying the signal to the following month's return (`shift(-1)`): keep both in every version. Revisions are a separate problem: if an indicator is revised after release (e.g. CFNAI, unlike PMI and CPI), take the values known at the time from ALFRED, which has vintages for the series used in the Class 7 slides.
- **The regime table (correcting the code).** §2 picks the best asset in each regime using all months up to 2026, including months that were still in the future at the time, so it cannot be used as evidence; the code below replaces it. The TA's fixed thresholds (PMI 50, CPI against a year earlier) are fine; a median over the whole sample, as in the Class 7 exercise, would use the future, so any median must come from past months only.
- **Count the trials (deciding the list).** Every strategy or variation we run goes in the trials log, and the report gives the count, as Class 4 asks: with 20 variations and no real effect, about one looks significant by luck. That is why the list is fixed, with reasons, before anything runs.
- **Momentum in USD, value in local currency: not a problem.** P/B is a ratio in one currency (price and book both local), which is what makes it comparable across countries; the currency risk is in the return we earn, in USD, which the backtest already includes. The iShares ETFs track the same MSCI indices, so the two sources are consistent.
- **Any model is allowed, so the trials count matters more (thematic strategies).** A theme picked because it did well this year, then tested on the same years, will look good by construction. Choose the theme and its rule from the outlook and the literature before looking at its backtest, test it on 2014–2026 only after fixing it on earlier years (or on the sector index where the ETF is young), and log every theme tried.
- **The real caveat: P/B depends on sector mix (decision needed).** A market full of banks has a low P/B by construction, one full of tech a high one, so ranking raw P/B across countries partly ranks sectors, not cheapness. Options: compare each country's P/B with its own past (using only earlier months); use a sector-neutral valuation if Bloomberg provides one for the MSCI country indices; or accept it and state it in the report.

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

Deep-research prompt for a thematic strategy (replace the parts in brackets):

```text
We run a long-only macro sleeve rebalanced monthly and want a rule-based thematic position in [THEME, e.g. US semiconductors] through [ETF or index], held for one month from 27 November 2026. Our view comes from [DATA POINT FROM THE OUTLOOK, e.g. rising AI capex and falling real yields]. Review the academic and practitioner literature on predicting the returns of this theme or sector at a 1-month horizon: momentum (absolute and relative to the market), valuation, macro drivers (rates, dollar, commodities, earnings revisions), and their interaction. For each signal: out-of-sample evidence, typical Sharpe ratio, drawdowns, and whether it can be built with monthly Bloomberg data in pandas. Warn about crowding and about theme ETFs with short histories. Cite papers and practitioner research with links. End with the one or two simplest rules worth backtesting.
```

### Step 2 – Download all the data at once (terminal)

We work on a copy of the TA folder, `Round 3 AMC/Macro/`; the TA original stays untouched. The copy of the template is already filled with our tickers, so on the terminal you only refresh it. What it downloads (also listed in its README sheet; tickers in yellow may need checking):

| Sheet | What | Why |
|---|---|---|
| Macro | ISM PMI, US CPI y/y, 3-month T-bill, Fed funds, monthly from 1990 | regimes (TA) |
| Assets | TA indices + proxies of our SAA: Russell 3000 (VTI), MSCI World ex US (VEA), MSCI EM (IEMG), US Aggregate (BND), Global Aggregate hedged (BNDX); TIP, GLD, BCI already covered by TIPS, gold, BCOMTR | regime vs our SAA, sizing |
| Countries / Value | total return of the 18 TA country ETFs + China (MCHI), India (INDA), South Africa (EZA); P/B of their MSCI indices, from 2001 | country V&M |
| Live | today's price of the country ETFs and of candidate macro ETFs (TLT, IEF, SHY, TIP, GLD, DBC, USO, CPER, FXA, FXE, FXY, FXB, FXF, FXC, CEW) | trade prices |
| Rates | today's policy rate of the 9 G10 currencies + Brazil, Mexico, South Africa, India | carry today |
| CarryRates / CarryFX (new) | the same policy rates and FX vs USD, monthly from 2001 | carry backtest after 2014 (the TA's `DataPython.xlsx` stops in 2014) |
| Extra (new) | CFNAI, unemployment, core CPI, 2y and 10y yields, 10y breakeven, 10y real yield, Brent, WTI, copper | only for the variations chosen in step 1 |

- **Bloomberg** — Owner:
  - On the terminal PC, open OneDrive in the browser (onedrive.live.com, our account) and download `Desktop/Financial Modeling/Matterhorn-Capital-Management/Round 3 AMC/Macro/Bloomberg template/r7_bloomberg.xlsx`.
  - Open it in Excel. In Settings, check that the end date is the trade date (Friday 27 November 2026).
  - Bloomberg tab → Refresh Workbook. Wait until no cell shows "#N/A Requesting Data...".
  - Ask Claude in Excel: "Check every sheet: for each ticker that returns #N/A find the right Bloomberg ticker, replace it and tell me what you changed." Write the changes in the README sheet.
  - Ask Claude in Excel: "Replace all formulas with their values in every sheet." Then File → Save As `r7_bloomberg_values.xlsx`.
  - Upload it through the browser to `Round 3 AMC/Macro/Data/`, replacing the TA's file. OneDrive syncs it to our laptops.
  - Live prices must be from the trade day: if you download earlier, refresh only the Live sheet again on 27 November and upload again.
- **Clean** — Owner:
  - `Round 3 AMC/Macro/01_bloomberg_macro_data.ipynb` (`pip install openpyxl` first). Our tickers are already in its dictionaries (`COUNTRIES`, `ASSETS`), and the last cell also saves `r7_carry_rates_bbg.csv`, `r7_carry_fx_bbg.csv`, `r7_extra.csv`.
  - If a ticker was changed on the terminal, change it here too.
  - Run all, check that "holes" are 0 and the first date of each new series.

**Notes for this step**

- **Indices as proxies.** Our Round 1 data start only in 2012 (BNDX in 2013), too late to see many months in each regime, so the Assets sheet uses the benchmark indices behind the ETFs, which usually go back much further (the TA's start in 1990). Check the first date of each one on the terminal; if one starts late (most likely the hedged global aggregate behind BNDX), use a close index with a longer history or accept a shorter sample. They have no fees and sometimes a different currency hedge: name each proxy in the report.
- **Revised data.** Bloomberg history shows today's revised figures, not those known at the time. It hardly matters for CPI and little for PMI, but GDP is revised heavily: if a variation uses GDP (e.g. a Taylor-rule signal), take first-release data from ALFRED, or use the unemployment gap, which is barely revised.

### Step 3 – Test everything with correct methods

- **Run the TA's versions** — Owner:
  - The code corrected in step 1, on the data of step 2.
- **Run the variations** — Owner:
  - Regime: each rule of step 1 as a small function that returns the monthly regime, through the same code.
  - Countries: §3 code with each universe or signal of step 1.
- **Rates and inflation (if chosen)** — Owner:
  - Write the code on the pattern of §3: signal known at month-end (macro data lagged with `shift(1)`), position, return of the following month, e.g. SHY minus IEF when the rates signal is on.
  - Data: Treasury indices for a long history; BCOMTR, TIP, XAU are already in the TA's CSVs.
- **Validation and discount** — Owner:
  - Tuning 2002–2013, test 2014–2026.
  - Sharpe ÷ 2.
  - Every run in the trials log.

**Notes for this step**

- **Look at the test period once.** Going back and forth between tuning and test turns the test period into a second tuning period, and the result stops meaning anything.
- **The discount.** Report the backtest Sharpe and half of it as the realistic figure, with a larger cut if the trials log is long.
- **A weak result reported honestly is fine**: the TA's own country strategy lost to its benchmark (Sharpe 0.37 against 0.46).

### Step 4 – Choose

- **Strategy (one or more), instruments, split** — Owner:
  - What worked in the test period (step 3).
  - Whose signal holds in December (step 1).
  - With little overlap with the quant and Round 2 stocks.
- **Chain from view to position, and rationale** — Owner:
  - TA Notebook 02 §1 cards; Class 7 reading; Pedersen, *Efficiently Inefficient*, for carry.

### Step 5 – Size and trade

- **Inputs from the quant strategy team** — Owner:
  - TE target, Round 2 stocks kept.
  - Files `r3_prices.csv`, `r3_rf.csv`, `r3_portfolio.csv`.
- **Size** — Owner:
  - Notebook 02 §5 with `PICKS` = our instruments and `A_TICK` = the Round 2 stocks kept.
  - It gives the macro weight within the TE target (TA: 6.5%) and the table of volatility, VaR and TE.
- **Trades and portfolio description** — Owner:
  - §6 with the NAV from `PORT`.
  - Add ISIN (`ID_ISIN`) and price date.
  - One table with the quant trades.
- **Enter the trades** — Owner:
  - `PRTU`, Sat 28 or Sun 29 Nov, updating the existing portfolio.

### Step 6 – Write

- **Strategy analysis** — Owner:
  - Why it should pay in the coming weeks (forward-looking macro analysis, step 1).
  - Risk or behavioural (step 4).
  - The risks.
- **Macro page** — Owner:
  - View, instruments, risk (state the skewness for carry).
  - Exit event from the calendar of step 1.
  - The portfolio cannot change before 27 December, so the exit event is the one that would prove the view wrong.
- **Slides** — Owner:
  - Market outlook = our view.
  - 2–3 slides on the strategy.
