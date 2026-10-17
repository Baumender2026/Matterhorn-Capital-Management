# Claude Code prompts: Round 1 corrections

These prompts apply the corrections in `06_Report_draft_corrections.docx` to the notebook and the report. Paste them into Claude Code one at a time, in order. The code prompts come first, because the report takes its numbers from the code. The report prompts follow, then structure, then a final check. Section 01 (the market outlook) is deferred and has no prompt.

> **Status, 17 October:**
> - Prompt 1 is done. §9 has a third step: the USD 144.20 left after the equity step buys 2 more shares of VEA, which leaves USD 5.22 in cash.
> - The portfolio description in the report (item 1 of Prompt 4) is already filled from §9.
> - Continue with Prompt 2.

## How to use

1. Open Claude Code at the repo root (`Matterhorn-Capital-Management`) and paste one prompt at a time, in order. Each prompt can run in a fresh session, because each one starts by reading the shared context below.
2. **Prompt 1 is blocking.** Run it today: it produces the share counts to enter in Bloomberg PRTU on Saturday 17 or Sunday 18 October.
3. Fill in the blanks in Prompts 3 and 5 before running them (Bloomberg liquidity data, the VTI top-10 weight, the source for AI circular financing). Empty fields are allowed: no number is invented, but the report then contains `[TO FILL]` markers that the team must resolve.
4. After each prompt, read the summary, review the diff (`git diff`) and commit. No prompt commits by itself.

| # | Prompt | What it changes | Corrections covered |
|---|---|---|---|
| 1 | Data paths and §9: from the weights to the Bloomberg portfolio | notebook, `code/portfolio_for_PRTU.csv` | TO-DO 1, 2 |
| 2 | Backtests, allocation groups, checkpoint cells | notebook | TO-DO 3, 4 · A3 · B1, B2 |
| 3 | §10 "Figures of the report" and number audit | notebook, `code/report_figures.json` | TO-DO 5, 6, 7, 8 |
| 4 | Portfolio description, code section, cash leg | report | TO-DO 2 · A2 · 3.4 |
| 5 | Checkpoint 1: investment policy | report | A2–A5 · TO-DO 5 |
| 6 | Method and alternatives (section 05) | report | A3 · B1 · B2 (Table 5) |
| 7 | Backtest, Checkpoint 2, Checkpoint 3 | report | B1, B2, B3 · TO-DO 3, 4 |
| 8 | Universe, ETFs and inputs (sections 02–04) | report | A4 · TO-DO 6, 7 · 3.1–3.4 |
| 9 | Structure: checkpoints and page order | report | General (structure) |
| 10 | Final check and PDF | notebook run, report, PDF | TO-DO 8 |

---

## Shared context

Every prompt asks Claude Code to read this section first.

**Files**

- **Notebook:** `code/SAA_R1_our_version.ipynb`. It uses relative paths, so run it from `code/`.
- **Adjusted prices:** `code data/AMC_adjusted_prices_final.csv`.
  - Bloomberg daily adjusted prices, January 2012 to 15 October 2026.
  - Row 1 is the asset class and row 2 the ticker.
  - `BCOMTR INDEX` is the return proxy of BCI, which only listed in 2017.
- **Closes for the shares:** `code data/AMC_closing_raw.csv`.
  - Raw closes of Friday 16 October 2026 for the nine tickers, `BCI US EQUITY` included.
  - One row, a UTF-8 BOM, and the date written `16.10.2026`.
- **Report:** `reports/round-1/Round 1 Report.dc.html`. This is the only report file to edit; do not touch `reports/templates/`. Read `reports/README.md` first: inline styles only, the brand tokens, and fixed A4 pages that clip any overflow.
- **Corrections:** `reports/round-1/06_Report_draft_corrections.docx`. Read it with `pandoc -t markdown`.
- **Rules:**
  - `slides/AMC 2026 - Round 1 guidelines.pdf`. Its §7 lists what the report must contain.
  - The last slides of the Class 3 Part I, Class 3 Part II and Class 4 decks in `slides/`. These are the three checkpoint assignments.

**Decisions already taken by the team (do not reopen)**

1. **The notebook is the source of every number in the report.** Never type a number from memory or compute it by hand. Run the notebook and copy its output; from Prompt 3 on, copy from `code/report_figures.json`.
2. **The walk-forward test stays in the notebook.** It is moved, unchanged, to a final appendix marked "not used in the report". Never delete it. The report never mentions it.
3. **BIL = 0 applies only to the final positions (§9).**
   - The analysis tables (Checkpoint 1, Tables 5–7, Checkpoint 2) keep the optimiser weights of `Basket 50/25/25`, which leave 0.01% in BIL.
   - The report explains the difference.
   - §9 buys in three steps: bonds and commodities first, then equity with everything left over, then the last USD 144.20 buys 2 more shares of VEA (the cheapest equity ETF). USD 5.22 stays in cash.
4. **Section 01, the market outlook, is frozen.** Do not edit it. It covers:
   - page "03 Market outlook";
   - page "04 Monetary policy";
   - the "1.3 · Rates, inflation pricing, credit and the dollar" part of page "05 Indicators and universe".
5. **Out of scope:** `data/`, `scripts/`, `index.html`, `.github/`, `reports/templates/`, and anything outside the repo. In particular, never use the old `portfolio_for_PRTU.csv` in the former Group 3 folder: it holds MVO weights and the `BCOMTR INDEX` ticker.

**Run the notebook**

```bash
cd code && /opt/anaconda3/bin/jupyter nbconvert --to notebook --execute --inplace SAA_R1_our_version.ipynb
```

The notebook downloads FRED DGS1MO, so it needs internet. After Prompt 1, it falls back to a cached copy if the download fails. It must finish without errors. Never leave the notebook with errors or stale outputs.

**Notebook style**

Use the same idioms as the existing cells:

- short end-of-line comments;
- `show()` for every table;
- reuse `perf` and `perf_table`;
- `## N. Title` sections and `### Na. Title` sub-sections;
- markdown that says what a cell computes and why;
- American spelling, as in the notebook.

**Report style**

Follow `reports/README.md`:

- copy an existing block to make a new one;
- Geist and Geist Mono fonts, with every number in Geist Mono;
- U+2212 (−) for negative numbers;
- British spelling, as in the draft (optimiser, annualised, realised);
- tables and figures numbered in reading order.

**Checkpoint labels** (used by Prompts 5, 7 and 9)

- The top bar of a checkpoint page reads `Checkpoint N of 3 — <title>`.
- Sub-points read `CPN.k · <title>`, for example `CP1.3 · Constraints, with reasons`. They then cannot be confused with the three checkpoints, or with section sub-headings such as `1.1 · Growth and inflation`.

**Page-overflow check** (after every report edit)

Serve the repo with `python3 -m http.server 8765` from the repo root, running in the background. Open `http://localhost:8765/reports/round-1/Round%201%20Report.dc.html` with Playwright, wait for the fonts to load, then evaluate:

```js
[...document.querySelectorAll('section.page')]
  .map(s => [s.dataset.screenLabel, s.firstElementChild.scrollHeight - s.firstElementChild.clientHeight])
  .filter(([, d]) => d > 1)
```

It must return `[]`. Take a screenshot of every page you changed and look at it. Fix overflow by tightening the text, never by shrinking fonts below the README sizes.

**Dependency sweep** (at the end of every prompt)

For every value, term or structure you changed, grep the notebook (code and markdown) and the report for the old value or term, and update every occurrence. Old values hide in places like these:

- a number quoted in a paragraph as well as in a table;
- references to sections;
- the description of the notebook in section 08.

**End every prompt with**

- a short summary of what changed, by file and by cell or page;
- the list of `[TO FILL: …]` markers and anything the team must check;
- no commit.

---

## Prompt 1: Code, data paths and §9 (blocking) · done 17 Oct

Produces the share counts for Bloomberg PRTU. Only the notebook changes. Already run, including the VEA top-up (step f); kept here for reference.

```text
Read the "Shared context" section of reports/round-1/07_Claude_Code_prompts.md first and follow it.

Task: corrections TO-DO 1 and 2. Make the notebook run in this repo, and turn our SAA into the number of shares we enter in Bloomberg PRTU this weekend, at the closes of Friday 16 October 2026. Only the notebook changes in this prompt; Prompt 4 updates the report.

1. Setup cell
   - Set DATA_FILE = Path("../code data/AMC_adjusted_prices_final.csv"). It currently points to ../Data Round 1/, which does not exist in this repo.
   - Add CLOSE_FILE = Path("../code data/AMC_closing_raw.csv"). It holds the raw closes (Bloomberg PX_LAST) of Friday 16 October 2026 for the nine tickers, BCI US EQUITY included. File details: one row; a UTF-8 BOM, so read it with encoding="utf-8-sig"; the date "16.10.2026" (format "%d.%m.%Y"); full Bloomberg tickers as column names.
   - FRED cache: after a successful download of DGS1MO, save the series to "../code data/DGS1MO.csv". If the download fails, read that file and print that the cached copy was used. Keep the same series and the same processing as now.

2. Section 1 markdown and the prices cell
   - The share count no longer relies on "last adjusted price = raw close", because the adjusted file ends on 15 October.
   - Say that §9 uses the raw closes of 16 October from AMC_closing_raw.csv, BCI included, and that the BCOMTR index remains the return proxy for BCI in §2–8.
   - Remove `close = prices.ffill()` if nothing uses it any more.

3. Rewrite the code of §9, "From weights to the Bloomberg portfolio"
   a. Prices.
      - Read CLOSE_FILE and set PRICE_DATE to its date. Assert that it is 2026-10-16 and a Friday.
      - Rename the columns to the notebook's short tickers, mapping BCI US EQUITY to BCOMTR, our internal name. BBG_TRADE already maps BCOMTR to "BCI US EQUITY".
      - Keep an explicit BCI_CLOSE taken from the file, with a comment saying that BCI is the ETF we hold and BCOMTR is its return proxy. Assert that it is a positive number.
   b. Target weights.
      - w = W[SAA], the eight risky ETFs.
      - Keep the 2% rule: an ETF below 2% gets no shares, and its weight joins the leftover of step e.
      - Print the smallest weight. It is 10.23% today, so the rule does not bind.
   c. BIL gets no shares. Our ex-ante volatility (8.13%) is inside the 7–9% band, so the 9% cap does not bind. The 0.01% the optimizer leaves unallocated is a numerical residual, not a cash leg.
   d. Bonds and commodities first (BASKETS["Bonds"] + BASKETS["Commodities"]): N_i = floor(w_i × CAPITAL / P_i).
   e. Equity last (BASKETS["Equity"]).
      - remaining = CAPITAL − the value bought in step d. This includes the 0.01% the optimizer left in BIL and the rounding leftovers of step d.
      - Split it among VTI, VEA and IEMG in proportion to their capital weights, rounding down: N_i = floor(remaining × w_i / Σ w_equity / P_i).
   f. Last leftover: what step e leaves (less than one share of each equity ETF) buys whole shares of the cheapest equity ETF. That is VEA, 2 more shares at the closes of 16 October. The final leftover cash, CAPITAL − total invested, is less than one share of VEA and earns 0.
   g. Print:
      - the total invested;
      - the leftover cash, in USD and in %;
      - the target and actual weight of each ETF, and the difference in pp;
      - the ex-ante volatility, the 1-month 5% VaR (% and USD) and the risk contributions of the actual weights, using V from §4 (the cash has no risk).
      Assert 7% ≤ ex-ante volatility ≤ 9%.
   h. Table, which becomes the portfolio description of the report: Name, Bloomberg ticker, Currency, Shares, Close price, Price date, Target weight, Actual weight, USD invested. One row for each of the 8 ETFs, then a cash row.
   i. Save portfolio_for_PRTU.csv next to the notebook, in code/.
      - The file contains the 8 ETFs only, with Bloomberg tickers written "XXX US Equity", including BCI US Equity.
      - There is no BIL row and no ticker containing "INDEX".
      - Columns: Name, Bloomberg ticker, Currency, Shares, Close price, Price date, Weight (actual).
      Assert all of these conditions, and that the total invested ≤ CAPITAL.

4. Markdown
   - Rewrite the §9 description: the three steps with their formulas, why bonds and commodities come first, why BIL is 0, and where the leftover goes.
   - Rewrite the "In Bloomberg" cell: enter the 8 ETFs of portfolio_for_PRTU.csv with their number of shares; no BIL.

5. Run the whole notebook (see the shared context). It must finish without errors.

6. Check the result against this dry run, made on 17 October with the same files:
   VTI 29,149 · VEA 147,369 · IEMG 133,320 · BND 188,225 · BNDX 349,731 · TIP 144,602 · GLD 29,177 · BCI 469,258
   Leftover after step e ≈ USD 144.20, which buys 2 VEA · final cash ≈ USD 5.22 · equity 31.38% of the capital (target 31.37%) · ex-ante volatility 8.13% · VaR ≈ USD 3,861,174.
   If a number differs, show the difference and explain it. Do not force the numbers.

7. In your answer, paste the §9 table and the contents of portfolio_for_PRTU.csv. The team types these share counts into PRTU.

Do not edit the report in this prompt.
```

---

## Prompt 2: Code, backtests, allocation groups and checkpoint cells

Explains why each test is used, groups the eleven allocations, and moves the walk-forward to an appendix without deleting it. Only the notebook changes.

```text
Read the "Shared context" section of reports/round-1/07_Claude_Code_prompts.md first and follow it.

Task: corrections B1, B2, A3 and TO-DO 3–4, in the notebook only. When you are done, the notebook must:
- say why each backtest is used;
- group the eleven allocations;
- show the ex-post volatility next to the Sharpe Ratio;
- keep the walk-forward test, moved to an appendix and not deleted;
- compute every number of the three checkpoints.

1. Groups of allocations (B1)
   - Define this before the 7a table:
     GROUPS = {"Candidates": ["Basket 1/3", "Basket 50/25/25", "Basket 60/20/20", "Basket 70/15/15"],
               "Benchmarks (CP2)": ["EW", "RP 1/vol"],
               "Diagnostics": ["Min var", "Max Sharpe", "RP (ERC)", "MVO @ 8%", "MDP"]}
   - Assert that every column of W belongs to exactly one group.
   - Order the columns of W by group, and show the group in the tables of 7a, §8, 8b, 8c and 8e. Use a Group column or a two-level index, whichever works better with show().
   - Only the order and the labels change, never the numbers.
   Markdown of §6, §7 and 7a:
   - Only the four baskets were candidates for our SAA.
   - EW and RP 1/vol are the benchmarks required by Checkpoint 2, not candidates. They are asset-class agnostic: they allocate by ETF, so the number of ETFs in each asset class decides the allocation. For example, three bond ETFs out of eight take 3/8 of the capital or of the risk. The basket method fixes this.
   - The diagnostics were never candidates:
     - Max Sharpe and MVO @ 8% show the estimation-error problem: they load on the winners of the last five years.
     - Min var stops at the 7% floor, with a solution that is not unique.
     - ERC on the 8 ETFs and MDP are asset-class agnostic, like the benchmarks.

2. §7b "Our SAA" markdown (A3)
   Use the A3 paragraph in Part 1 of the corrections doc as the model. The text must make these points:
   - We allocate risk, not capital.
   - Equity is the growth engine: the equity premium rests on economic growth and corporate earnings.
   - Bonds and commodities are the brakes: nominal bonds when growth and inflation fall, commodities (and TIPS) when inflation rises.
   - The rules came before the choice. Equity gets the largest share of the risk, but at most 70%. Bonds + commodities get at least 30%, split equally.
   - We tested four budgets within these rules and chose 50/25/25 because it is the closest to the 8% volatility target. The effect of a risk budget on the volatility is hard to anticipate ex ante.
   - The backtests only confirmed that the four budgets have practically the same hold-out Sharpe Ratio. Take the range from 8b.
   - For reference, a 60/40 portfolio has about 90% of its risk in equity (Class 3). Even the 70% budget is more balanced.
   Code under SAA:
   - Compute the risk contribution of each basket (the sum of its ETF contributions) for the four candidates, and show the table.
   - Assert equity ≤ 70% and bonds + commodities ≥ 30%, with a 0.1 pp tolerance for the optimizer.

3. Why each backtest is used (B2, TO-DO 3)
   Rewrite the markdown of §8, 8b and 8c. In a few lines, each test states what it tests and its limit:
   - Full sample (§8): our weights on all 159 months. Reference only, because the last 60 months are the estimation window (in-sample).
   - Hold-out (8b): our actual weights on the 99 months before the estimation window, which the optimizer never saw.
     - No in-sample fitting, but there is look-ahead: weights estimated on 2021–2026 are applied to 2013–2021, which no investor could have done.
     - It is the test we rely on, because it tests the mix we hold until Round 2: not the method, and not what re-optimizing would give.
   - Split (8c): the rule estimated once on the first 60 months, then held fixed for the following 99, just as our SAA is held fixed.
     - No look-ahead, but it tests the method: its weights are not ours.
   Remove the 8c bullet that compares the split with the walk-forward test, and every other mention of 8d outside the appendix.

4. Walk-forward moves to an appendix
   - Move the markdown and code cells of "8d. Walk-forward test", unchanged in their logic, to a new last section: "## Appendix — Walk-forward test (not used in the report)".
   - Put it at the very end of the notebook, after "In Bloomberg". Prompt 3 inserts §10 before it.
   - Its markdown says why the report does not use it: it re-estimates the weights every month, which is a dynamic strategy we do not follow, since our SAA stays fixed until Round 2.
   - It may show its own Sharpe and volatility table.
   - Do NOT delete any of its code.

5. 8e becomes "Backtest summary" (TO-DO 4)
   It holds two tables, both used by the report.
   a. Our SAA in the three tests, the source of report Table 8.
      - Columns: Full sample, Hold-out (8b), Split (8c, the SAA column of W_first).
      - Rows: period, Ann. return, Cum. return, Ann. vol, Sharpe, t-stat (= Sharpe × √(months / 12)), Sortino, Max drawdown, 1-month 5% VaR (= var_normal(Ann. vol)).
   b. The eleven allocations by group, the source of report Table 10: Sharpe and Ann. vol (ex post), in the full sample and in the hold-out.
   Say in the markdown that the Sharpe Ratios of the eleven allocations in the split test remain in 8c.

6. CP1 cell
   - Set MAX_DD = -0.15, the maximum acceptable drawdown stated in the report. Print it next to the worst drawdown of our weights in the full sample.
   - Print the capital and the risk by basket (Equity, Bonds, Commodities, BIL).
   - Print the regional split of the equity capital: VTI, VEA and IEMG as shares of equity.

7. CP2 cell
   Add the capital by basket and the risk by basket for the three portfolios. They are the source of the Equity / Bonds / Real assets rows in the report's Checkpoint 2 table.

8. CP3 cell
   a. Design: the three tests of §8 (full sample, hold-out, split).
   b. Variations, with the arithmetic printed.
      - N_ALLOCATIONS = len(W.columns): 11, each allocation counted once, however many tests it goes through.
      - N_EX_ANTE = 23: variants compared ex ante on earlier universes, the team's count.
      - N_CHANGES = 3: STIP → TIP; VT → VTI + VEA + IEMG; 1/σ → ERC inside the bond basket.
      - The total is 37.
      Put the constants at the top of the cell with a comment, so the team can change the count.
   c. Print which allocations were candidates, CP2 benchmarks and diagnostics, taken from GROUPS.
   d. A risk table with three columns: Tuning sample (the estimation window, with our fixed weights), Held out, and Full sample.
      - Rows used by the report's Checkpoint 3 table: mean excess return, annualised, with its t-stat; Ann. vol; Max drawdown; 1-month 5% VaR in % and in USD; Sharpe.
      - Additional rows: months, Ann. return, Cum. return, Sortino, t-stat and discounted Sharpe.
      - Also print the standard error of the hold-out Sharpe (≈ Sharpe / t-stat).

9. Run the whole notebook.
   - Confirm that every number already shown in 7a, §8, 8b, 8c, CP1–CP3 and §9 is unchanged, apart from order and labels.
   - List any number that changed, and explain why.
```

---

## Prompt 3: Code, §10 "Figures of the report" and number audit

Makes the code the source of every number in the report and exports them to one JSON file. Fill in the blanks at the bottom of the prompt before running it.

```text
Read the "Shared context" section of reports/round-1/07_Claude_Code_prompts.md first and follow it.

Task: correction TO-DO 8, plus the code side of TO-DO 5, 6 and 7. The code must be the origin of every number in the report. Today several numbers are computed nowhere in the notebook; Table 9 (calendar-year returns) is one example. Add them in a new section, then export every number of the report to one file that the report prompts copy from. Only the notebook, and the JSON it writes, change here.

1. Audit
   Read every page of the report except the frozen section 01, and list every number with:
   - where it appears (page label, table or paragraph);
   - its value;
   - its source: the notebook section and variable, or "external [n]" for a cited source such as a fact sheet, or "missing".
   Show the audit table in your answer.
   These numbers are missing from the notebook today, at least:
   - Table 9: calendar-year returns of our SAA, EW and RP 1/vol, for 2014–2025 and for January–September 2026.
   - Figure 2:
     - the monthly growth of USD 1 of our SAA, EW and RP 1/vol over the full sample;
     - the end values (2.11, 2.27 and 1.86 in the draft);
     - the start and end of the estimation window (the light band).
   - 7.2 text:
     - the worst month: −9.4%, March 2020;
     - the maximum drawdown, with its peak, trough and recovery month: October 2021 → September 2022, recovered by March 2024;
     - March 2020: the month's return, the drawdown from the peak, and the recovery month;
     - each ETF's return in 2022 and in March 2020. In 2022: US equity −20%, US bonds −12.5%, commodities +15.7%, gold +0.8%. In March 2020: equities about −20%, commodities −17%;
     - the losing calendar years, and the worst of them;
     - the realised volatility of the SAA in the hold-out and in the estimation window: 6.9% vs 8.1%;
     - the range of the t-statistics in Table 8.
   - Section 04 text:
     - the correlation ranges: equity 0.72–0.82; bonds 0.85–0.90; stocks–bonds 0.47–0.64; gold and commodities at most 0.47 with the other ETFs; commodities–bonds −0.13 to 0.12;
     - the standard error of the mean of a 15%-volatility ETF over five years: 15% / √5 ≈ 6.7 pp.
   - Section 06 text: equity volatility relative to bond volatility, "about 2.5 times".
   - Table 7, the Checkpoint 1 paragraph and the Checkpoint 2 rows:
     - capital and risk by basket. The draft prints real assets at 23.55% (and 23.5%) of the capital; the code gives 23.54%;
     - the regional split of the equity capital, 35/33/33.
   - Table 8: the t-statistic and the VaR of the split column.
   - Checkpoint 3: the tuning-sample column, the mean excess returns with their t-statistics, and the standard error of the Sharpe Ratio (≈ 0.35).
   Prompt 2 already added some of these to the CP cells and to 8e. Reuse those values; do not compute anything twice.

2. New section "## 10. Figures of the report"
   - Place it after §9 ("In Bloomberg") and before the walk-forward appendix.
   - Add one short cell per missing item. Title each cell with the report element it feeds, e.g. "Table 9 · Calendar-year returns".
   - Reuse the variables of §1–9 (R, rf, bt, bt_out, bt_first, W, V, vol, corr, mu, cp1, the §9 table, …). Never re-read the data.
   Also add these three cells:
   a. Gold look-through (TO-DO 6).
      - GOLD_IN_BCOM = 0.149, the 2026 target weight of gold in the Bloomberg Commodity Index. For reference: precious metals are 18.8% and energy 29.4%, as announced by Bloomberg on 30 October 2025.
      - Look-through gold = w_GLD + GOLD_IN_BCOM × w_BCI, using the target weights of W[SAA]. This gives ≈ 11.15% + 0.149 × 12.40% ≈ 13.0% of the capital, with an overlap through BCI of ≈ 1.8 pp.
   b. Liquidity check (TO-DO 5, A5).
      - Build a dict LIQUIDITY holding each ETF's fund assets (USD) and average daily volume (shares), as read on Bloomberg. Fill it from the block at the bottom of this prompt.
      - Compute each ETF's average daily value traded (volume × close of 16 October) and each §9 position as a % of one day's value traded.
      - Check that the fund assets exceed USD 1 billion and that each position is at most one day's volume.
      - Print an ETF without data as "to verify on Bloomberg". Never assume its values.
   c. Table 4 colours (TO-DO 7).
      - For every cell of the correlation matrix, compute the background colour of the §4 heatmap as a hex code. Use matplotlib "RdBu_r" with vmin −1 and vmax 1, exactly as background_gradient does.
      - Also compute the text colour pandas puts on that cell: light on dark cells, following pandas' rule with text_color_threshold = 0.408.
   Update the notebook's intro cell so that it lists §10 and the appendix.

3. Export
   The last cell of §10 writes code/report_figures.json.
   - It holds every number of the report, formatted exactly as the report prints it: same decimals, % sign, thousands separators, and U+2212 for negatives.
   - Group the numbers by report element:
     - cp1, cp2, cp3;
     - table3 to table10;
     - figure2, with the raw series for the chart;
     - portfolio: the §9 table and the leftover cash;
     - text: numbers quoted in paragraphs, keyed by page and topic;
     - liquidity, gold, heatmap.
   - Write it with json.dump, indent=1 and ensure_ascii=False.

4. Run the whole notebook. Then compare the report with report_figures.json and list every mismatch (the value in the report vs the value in the JSON). Do not edit the report.

Bloomberg liquidity data. The team fills this in before running; leave blank anything not yet checked.
| ETF  | Fund assets (USD bn) | Avg daily volume (shares) | Bloomberg field and date |
|------|----------------------|---------------------------|--------------------------|
| VTI  |                      |                           |                          |
| VEA  |                      |                           |                          |
| IEMG |                      |                           |                          |
| BND  |                      |                           |                          |
| BNDX |                      |                           |                          |
| TIP  |                      |                           |                          |
| GLD  |                      |                           |                          |
| BCI  | 3.5                  | 1.5–1.7 million; store 1.5 million (the conservative end) | team check on Bloomberg (corrections doc, TO-DO 5) |
```

---

## Prompt 4: Report, portfolio description, code section and cash leg

Checks the §9 share counts in the report (already filled on 17 Oct), updates the code section, and fixes every "scale to 8%" statement outside Checkpoint 1.

```text
Read the "Shared context" section of reports/round-1/07_Claude_Code_prompts.md first and follow it. This prompt needs Prompts 1–3 to have run: take every number from code/report_figures.json and from the output of §9.

Task: correction TO-DO 2 (report side) and A2, plus the code section. Specifically:
- report the portfolio we enter in Bloomberg exactly as §9 computes it;
- describe the code as it is now;
- fix the description of the cash leg. BIL is used only to bring the volatility down to the 9% cap; it is never "scaled to the 8% target".

1. Portfolio description (page "16 Code and portfolio", heading "Portfolio description")
   This was already filled on 17 October from §9. It contains:
   - the three-step text: bonds and commodities first; equity with everything left over; the last USD 144.20 buying 2 more VEA shares;
   - the table of the 8 ETFs (no BIL row), with the cash row (USD 5.22) and the total row;
   - the note with the largest weight difference (0.004 pp) and the volatility and VaR of the portfolio held.
   Check every number against the latest §9 output and portfolio_for_PRTU.csv, and fix any difference. Keep the three steps.

2. Section 08 "The code" (same page)
   Make the description match the repo.
   - SAA_R1_our_version.ipynb: describe §1–10 as they are now:
     - §8 runs three backtests: full sample, hold-out, split;
     - the checkpoint cells;
     - §9 computes the numbers of shares;
     - §10 computes the remaining figures of the report.
     Do not mention the walk-forward appendix.
   - Data and output files:
     - AMC_adjusted_prices_final.csv: January 2012 – 15 October 2026;
     - AMC_closing_raw.csv: raw closes of 16 October 2026, BCI included, used by §9;
     - FRED DGS1MO: downloaded at every run and cached in DGS1MO.csv;
     - portfolio_for_PRTU.csv: the output of §9, the 8 positions entered in PRTU;
     - report_figures.json: every number of this report, written by §10.
   - The sentence "Running it from top to bottom reproduces every table" must stay true.

3. Cash leg outside Checkpoint 1 (A2; Prompt 5 handles Checkpoint 1)
   - 3.4 BIL, "Role". Replace "we scale the risky portfolio down to the 8% target and invest the remainder in BIL" with the 9% cap. The new text says:
     - BIL is used only if the risk budgets give an ex-ante volatility above 9%;
     - in that case, the risky weights are scaled down until the volatility is 9% and the rest goes to BIL, as in the 70/15/15 budget (Table 5);
     - inside the 7–9% band, BIL is not held;
     - our SAA (8.13%) does not hold BIL. The 0.01% the optimiser leaves unallocated is a numerical residual, and it goes to equity in the final portfolio (section 09).
   - 5.1, Step 3: change "whatever is not invested goes to BIL" to say that BIL takes the rest only when the 9% cap binds.
   - Table 5 note. Keep "At 70/15/15 the 9% cap binds and the rest goes to BIL". Add that the 0.01–0.06% of the other budgets is a numerical residual, because risk budgets fix the shares of risk, not the scale. For our SAA it goes to equity in section 09.
   - Section 06.
     - The KPI "Positions · 8 + BIL" becomes 8 ETFs (BIL not held).
     - The BIL row of Table 7 (0.01%, "Cash leg") stays, with a short pointer to section 09.
   - Section 07 says "whatever is not invested earns the BIL return", and Checkpoint 3 says "rest in BIL". Both are correct, because the backtest uses the target weights; keep them.

4. Sources
   Extend [13] with the raw closes of 16 October 2026 (AMC_closing_raw.csv) and the end date of the adjusted prices (15 October 2026).

5. Checks
   - Run the overflow check on pages 09, 11, 13 and 16.
   - Do the dependency sweep. Grep for "8% target", "scale", "8 + BIL", "[—]", "BIL US Equity" and "§8 runs".
```

---

## Prompt 5: Report, Checkpoint 1 (investment policy)

Rewrites the constraints and the risk paragraph on page 02. The page must stay one page. Fill in the blanks at the bottom of the prompt before running it.

```text
Read the "Shared context" section of reports/round-1/07_Claude_Code_prompts.md first and follow it. This prompt needs Prompts 2–3 to have run: it uses MAX_DD, the basket sums, the liquidity table and the gold look-through from code/report_figures.json.

Task: corrections A2–A5 and TO-DO 5, on page "02 Investment policy". Every number comes from the notebook.

The page must stay ONE page. The assignment slide (Class 3 Part I) asks for "One page per group, the first page of your round-1 report". It must keep the four required items:
- the universe;
- the objective and risk budget: volatility target, ex-ante volatility, VaR, and maximum acceptable drawdown;
- the constraints, each with its reason in terms of today's model errors: concentration, regions and liquidity;
- the capital weight and risk contribution of each position, stating whether a position above half of the risk is intended.

1. Labels
   Apply the checkpoint labels from the shared context:
   - top bar: "Checkpoint 1 of 3 — Investment policy";
   - sub-points: CP1.1 Universe; CP1.2 Objective and risk budget; CP1.3 Constraints, with reasons; CP1.4 Risk contributions.

2. CP1.3 table
   One row per constraint: the rule on the left, and the reason (model error or estimation error) on the right.
   - Concentration: risk budgets by asset class (A3).
     Rule:
     - We allocate risk, not capital. The rules were fixed before choosing the weights.
     - Equity at most 70% of the portfolio risk.
     - Bonds + commodities (the brakes) at least 30%, split equally.
     - Equal risk per ETF inside each basket.
     - No ETF above 20% of the capital or of the risk.
     - We tried four budgets within these rules (33, 50, 60 and 70% equity) and chose 50/25/25 (section 05).
     Reason:
     - Estimation error. Five years of returns give a standard error of about 7 pp on the mean of a 15%-volatility ETF, so expected returns cannot set the weights. An optimiser that used them would hold a third of the capital in gold.
     - Allocating by ETF (equal weight, ERC) lets the number of ETFs per asset class decide the allocation.
     - The 70% bound keeps equity well below the ~90% of the risk that it carries in a 60/40 portfolio.
   - Regions (A4).
     Rule:
     - Each equity region (US, developed ex-US, emerging) holds at least 5% of the capital, for full geographic coverage.
     - Equity is weighted by risk, not by market cap: 35/33/33 of the equity capital, against 64% US in the MSCI ACWI [6].
     - Non-US bonds are hedged to USD.
     Reason (model error), stated as a risk-concentration argument:
     - Market-cap weights would put 64% of world equity in the US, and a large share of that in a handful of AI-linked mega caps. The top 10 holdings are [VTI_TOP10]% of VTI [5].
     - Their earnings partly finance each other [CIRCULAR_SOURCE]: chipmakers invest in AI labs that buy their chips and cloud capacity. So many names carry one risk factor, which a 60-month covariance matrix does not show as concentration.
     - The 20% cap on every ETF already limits single positions.
     - Currency risk in bonds is not rewarded.
   - Liquidity (A5, TO-DO 5).
     Rule:
     - Only ETFs with fund assets above USD 1 billion.
     - Every position can be bought within one day of average trading volume.
     - Whole shares, rounded down.
     - No position below 2% of the capital.
     Reason (model error): the optimiser assumes every ETF trades at the closing price at no cost.
     Evidence (from §10):
     - BCI, the smallest fund, has about USD 3.5 billion of assets and trades 1.5–1.7 million shares a day, about USD 40–45 million.
     - Our BCI position, about USD 12.4 million, is about 30% of one day's volume. It is the most binding of the eight.
     - For the other seven ETFs, use the liquidity table of §10. If a fund is still "to verify on Bloomberg", write "[TO FILL: verify on Bloomberg DES]" and list it in your summary.
   - Cash leg (A2).
     Rule:
     - BIL is used only if the fully invested portfolio would exceed the 9% cap. The risky weights are then scaled down to 9%, and the rest goes to BIL.
     - Our SAA (8.13%) does not need it. The 0.01% left unallocated by the optimiser goes to equity in the final portfolio (section 09).
     Reason: cash earns 0 in the challenge, which is about −4% a year in excess of the 1-month T-bill (4.13%). BIL earns about the T-bill rate.

3. CP1.4 Risk contributions
   - Keep the table: the optimiser weights, BIL 0.01%, with the numbers from the CP1 cell.
   Rewrite the paragraph so that it says:
   - No position carries more than half of the risk. The largest is VEA, at 17.4%.
   - By basket, from §10: equity is 31.4% of the capital and 50.0% of the risk; bonds 45.1% and 25.0%; real assets 23.5% and 25.0%. This fixes the draft's 23.55%.
   - Why equity gets the largest share of risk: it is the growth engine, and the equity premium rests on economic growth and earnings. Bonds and commodities are the brakes, in falling and in rising inflation respectively.
   - The maximum acceptable bound is 70% of the risk, still below the ~90% of a 60/40 portfolio (Class 3).

4. CP1.1 and CP1.2
   - Take the numbers from the notebook: ex-ante volatility 8.13%; VaR 3.86% = USD 3.86 million; maximum acceptable drawdown −15%, against −13.0% in the backtest.
   - CP1.1 can say that BIL is the cash leg, held only when the 9% cap binds.

5. Keep it on one page
   - Shorten the wording before you reduce spacing. Never go below the README font sizes.
   - Run the overflow check and take a screenshot of page 02.

Fill in before running (team):
- VTI_TOP10 = the weight of the top 10 holdings in VTI: ___%, from the Vanguard fact sheet dated ___.
  - If this is empty, take the value from the latest Vanguard VTI fact sheet you can open, and cite it with its date.
  - If that date differs from source [5] (30 Jun 2026), either add a new source, or update [5] together with the 3.1 facts that cite it.
  - If you cannot find it, write [TO FILL: VTI top-10 weight].
- CIRCULAR_SOURCE = a citation for "chipmakers invest in AI labs that buy their chips and cloud capacity": publisher, title, date, URL: ___.
  - If this is empty, cite a reputable outlet that you can actually open (Bloomberg, Financial Times, Reuters, WSJ), and add it to Sources.
  - If you cannot, drop the clause.
```

---

## Prompt 6: Report, method and alternatives (section 05)

Covers 5.2, 5.3, Table 5 and Table 6: why risk-based, why 50/25/25, and the candidates, benchmarks and diagnostics.

```text
Read the "Shared context" section of reports/round-1/07_Claude_Code_prompts.md first and follow it. This prompt needs Prompt 2 (groups, the §7b text, 8e) and Prompt 3 (the JSON).

Task: corrections B1 and A3, plus B2 for Table 5, on pages "11 Method" and "12 Methods compared".

1. 5.2 "Why a risk-based method"
   - Start with the core reason, which is missing today. Equal weight, risk parity 1/σ and ERC on single ETFs are asset-class agnostic: they allocate by ETF. The result therefore depends on how many ETFs each asset class has, not on the asset class itself. For example, three bond ETFs out of eight take 3/8 of the risk under ERC. The basket method fixes this by budgeting risk by asset class.
   - Against mean–variance and maximum Sharpe, the reason remains estimation error. Keep the Class 3 horse race: 0.04 against 0.53.
   - Keep "Regimes" and "Capital is not risk", shortened if space requires.

2. 5.3 "Why 50 / 25 / 25"
   Rewrite it using the A3 paragraph of the corrections doc (Part 1, "Risk budget across asset classes"), adapted to the page. It must be clear that we did not pick 50/25/25 ex ante:
   - We wanted a mix driven by equity risk, so we set the rules first. Equity gets the largest share of risk, but at most 70%. The brakes, bonds and commodities, get at least 30%, split equally.
   - We tested four budgets within these rules. We chose 50/25/25 as the budget closest to the 8% volatility target, because the effect of a risk budget on the volatility is hard to anticipate ex ante.
   - The backtests only confirmed that the budgets have practically the same hold-out Sharpe Ratio: 0.65–0.66, from 8b.
   - For reference, a 60/40 portfolio has about 90% of its risk in equity. Even the 70% budget is considerably more balanced.
   Keep references [15] and [16] only if the text still uses them. If one drops out, tell me; do not renumber the sources here.

3. Table 5 "The four equity budgets" (B2)
   - Drop the "Sharpe, walk-forward" column, and the walk-forward sentence of the note.
   - Keep the ex-ante volatility, BIL and hold-out Sharpe, with numbers from 7a and 8b.
   - Keep the BIL sentence that Prompt 4 added to the note.

4. 5.4 "The methods we compared" (B1)
   Table 6:
   - Keep the same numbers (from 7a).
   - Group the rows into three blocks, each with a header row:
     - "Candidates — basket method": 33/33/33, 50/25/25 · SAA, 60/20/20, 70/15/15;
     - "Benchmarks of Checkpoint 2": equal weight, risk parity 1/σ;
     - "Diagnostics — never candidates": minimum variance, maximum Sharpe, mean–variance at 8%, ERC on 8 ETFs, maximum diversification.
   Intro:
   - We computed eleven allocations on the same inputs and under the same rules. Only the four baskets were candidates.
   - Equal weight and risk parity are the Checkpoint 2 benchmarks.
   - The other five are diagnostics, kept because they show the estimation-error problem.
   "Why we did not choose the others": regroup the text by block.
   - Benchmarks: asset-class agnostic. Equal weight ignores the risk of each ETF, 1/σ ignores the correlations, and both let the ETF count decide.
   - Diagnostics:
     - maximum Sharpe and mean–variance: estimation error, giving a third of the capital in gold, no bonds, no non-US equity, and 24–30% in BIL;
     - minimum variance: stops at the 7% floor, is not unique, and holds 16.7% in BIL;
     - maximum diversification: 41% in BNDX;
     - ERC on 8 ETFs: the ETF count becomes a hidden risk budget.
   Add this sentence: "In the hold-out test, risk parity 1/σ outperformed our allocation (Sharpe 0.78 against 0.66), and we did not adopt it: we chose among the candidates on economic grounds."

5. Checks
   - Run the overflow check on pages 11–12.
   - Do the dependency sweep: grep for "walk-forward", "eleven", "Table 5" and "Table 6".
```

---

## Prompt 7: Report, backtest, Checkpoint 2 and Checkpoint 3

Covers the three tests and their logic, Table 10 with ex-post volatility, the B3 sentences, and the variation count. After this prompt the report never mentions the walk-forward.

```text
Read the "Shared context" section of reports/round-1/07_Claude_Code_prompts.md first and follow it. This prompt needs Prompts 2–3 to have run.

Task: corrections B1, B2, B3 and TO-DO 3–4, on pages "14 Backtest", "15 Backtest results", "17 Robust approaches" and "18 Backtest protocol". After this prompt the report must not mention the walk-forward test anywhere.

1. Section 07 intro (page 14): three tests instead of four
   - Replace "We therefore run four versions" and the four cards with three cards. Each card gives the test's logic and its limit (B2), with the same content as the notebook markdown of §8–8c:
     - Full sample: our weights on all 159 months. Reference only: the last 60 months are in-sample.
     - Hold-out: our weights on the 99 months before the estimation window, which the optimiser never saw.
       - No in-sample fitting, but there is look-ahead: weights from 2021–2026 are applied to 2013–2021.
       - It is the test we rely on, because it tests the mix we actually hold: not the method, and not what re-optimising would give.
     - Split: the rule estimated once on the first 60 months, then held fixed for the following 99, just as our SAA is held fixed.
       - No look-ahead, but it tests the method: its weights are not ours.
   - Remove the walk-forward card.

2. Table 8 (table a of 8e)
   - Drop the walk-forward column.
   - Take the numbers from the JSON.
   - Note: "Split tests the rule, with weights different from ours."

3. Figure 2
   - Rebuild the three polylines, the end labels and the estimation-window band from figure2 in the JSON.
   - Use the same coordinate mapping as the current SVG; read it from the gridlines.
     - y: 1.0 sits at y = 179.8 and 2.2 at y = 34.2.
     - x: from 40 to 530 over the 160 month-ends, starting with Jun 2013 at 1.0.
   - The lines should match the current ones. Report any visible difference.

4. Table 9 and the 7.2 text
   - Take the numbers from the JSON. They match the draft today: check them, do not retype them.
   - Replace "The t-statistics of the mean excess return are between 1.4 and 2.0" with the range of the three tests in Table 8.

5. Table 10 (TO-DO 4, B1)
   - New title: "Sharpe Ratio and ex-post volatility of the eleven allocations".
   - For each allocation: the Sharpe and the annualised volatility, in the full sample and in the hold-out (table b of 8e).
   - Group the rows as in Table 6 (candidates, benchmarks, diagnostics), with our SAA in bold.
   - No split column and no walk-forward column.
   Rewrite the paragraph under the table, using only numbers that are in the table. For example:
   - maximum Sharpe leads the full sample only because its weights were fitted on the last 60 months, and it falls to 0.64 in the hold-out;
   - in the hold-out, risk parity 1/σ has the highest Sharpe (0.78) with the lowest volatility;
   - our basket is in the middle;
   - the four candidates have practically the same hold-out Sharpe.
   Add the caveat (B1, B2): the hold-out has look-ahead bias, but it tests the mix we hold, not the method and not re-optimising.

6. Checkpoint 2 (page 17)
   - Labels: "Checkpoint 2 of 3 — Robust approaches"; sub-points CP2.1 (the table) and CP2.2 (the paragraph).
   - Table: numbers from the CP2 cell. The Equity / Bonds / Real assets rows come from the new basket rows.
   - Paragraph: replace the last sentences ("Out of sample, no rule dominates: … a fixed share of the risk.") with the B3 text. Keep it verbatim, except for numbers taken from the JSON: "In the hold-out test, risk parity 1/σ has a higher Sharpe Ratio than our allocation (0.78 against 0.66), and equal weight a similar one (0.64). Our weights are therefore justified on economic grounds, not by superior backtested performance."

7. Checkpoint 3 (page 18)
   Labels: "Checkpoint 3 of 3 — Backtest protocol"; sub-points CP3.1 Design, CP3.2 Validation, CP3.3 Risk, CP3.4 The discount.
   - CP3.2 Validation:
     - Change "Split and walk-forward tests use only past data" to "The split test uses only past data".
     - Variations, from the CP3 cell: "37: 11 allocations, each backtested in 3 designs (full sample, hold-out, split); 23 variants compared ex ante on earlier universes; 3 changes of universe or rule".
     - Add which alternatives were never candidates (B1):
       - only the four basket budgets were candidates;
       - equal weight and risk parity 1/σ were the benchmarks required by Checkpoint 2;
       - minimum variance, maximum Sharpe, mean–variance at 8%, ERC on 8 ETFs and maximum diversification were diagnostics.
     - Add: in the hold-out, risk parity 1/σ beat our allocation (0.78 against 0.66), and we did not adopt it.
     - In the contamination note, remove "with the walk-forward".
   - CP3.3 Risk:
     - The table comes from the CP3 cell (tuning / hold-out / full sample).
     - Remove the walk-forward sentence from the note.
   - CP3.4 The discount:
     - Remove "our walk-forward gave 0.48,".
     - Keep the rest of the evidence: Class 3 risk parity 0.53 out of sample, 60/40 at 0.36.
     - Check that the five reasons still hold.

8. Checks
   - Run the overflow check on pages 14, 15, 17 and 18.
   - Grep the report for "walk", "Walk", "four tests", "four versions" and "four designs". None may remain.
```

---

## Prompt 8: Report, universe, ETFs and inputs (sections 02–04)

Covers concision, the VTI concentration point, TIP, the gold overlap in BCI, and the Table 4 heatmap.

```text
Read the "Shared context" section of reports/round-1/07_Claude_Code_prompts.md first and follow it. This prompt needs Prompt 3 (gold look-through, heatmap colours) and Prompt 5 (the VTI top-10 weight, if it was found).

Task: the Part 2 corrections for sections 02–04, plus TO-DO 6 and 7. Section 01 stays as it is.

1. Concision
   Sections 02–03 currently take about four pages ("How we built the universe" on page 05, then pages 06–09). Make the reasons less verbose, with a target of about three pages.
   - For each ETF, keep the header line (name, index, listing, facts).
   - Keep "Why we chose it", "Why not …" and "Risks we accept", each in one or two sentences.
   - Cut repetitions of the outlook.
   - Keep every fact that another section or checkpoint refers to, and every citation still needed.
   - Remove a page only if the content fits on the others. Prompt 9 renumbers the pages.
   - Page "05 Indicators and universe" already overflows by 16 px in the draft (found on 17 October). Fix it by shortening the section 02 part of that page ("How we built the universe"). The section 01 part is frozen.

2. 3.1 Equity, VTI (A4)
   Say that holding three regional ETFs weighted by risk, not by market capitalisation, hedges out the concentration a market-cap allocation would have. That concentration is in the US (64% US in the MSCI ACWI [6]) and in a handful of AI-linked mega caps (the top-10 holdings are [VTI_TOP10]% of VTI [5], as in Checkpoint 1).

3. 3.2 Fixed income, TIP
   - TIP sits in the bond basket because its risk is mostly real-rate duration: its correlation with BND is 0.90 (Table 4). It also partially hedges the inflation regime.
   - Keep Checkpoint 1's "Bonds · disinflation" label consistent with this. A short "TIP also partly hedges inflation" there is enough, if it fits; otherwise leave Checkpoint 1 as it is.

4. 3.3 Real assets: the gold overlap (TO-DO 6)
   - Gold overlaps with BCI. The 2026 target weight of gold in the Bloomberg Commodity Index is 14.9%, with precious metals at 18.8% and energy at 29.4%, as announced on 30 October 2025.
   - Our look-through gold is therefore about 13.0% of the capital: 11.15% in GLD plus 1.8 pp through BCI, from §10.
   - Justification: investors broadly treat gold as a standing asset class in inflationary and stress periods, and the overlap adds less than 2 pp.
   - Add the source to Sources: Bloomberg, Bloomberg Commodity Index 2026 target weights, 30 Oct 2025. Add the URL only if you can open it; otherwise write "[TO FILL: URL]".

5. 3.4 BIL
   Keep the 9% cap text from Prompt 4, shortened if needed.

6. 04 Inputs, Table 4 (TO-DO 7)
   - Colour every cell with the notebook's heatmap colours, so that low and negative correlations are visibly different. The JSON's heatmap entry gives the background and text colour of each cell, on the same RdBu_r scale from −1 to +1 as §4, diagonal included.
   - Replace the note "Shading: dark ≥ 0.80, light 0.50–0.79." with the scale, as in the notebook: blue −1, white 0, red +1.
   - The team requested this table as the only multi-colour element of the report. It is an exception to the README's single-accent rule.

7. Check the numbers in 4.1 and 4.2 against the JSON.

8. Sources
   - Every [n] in the text must exist in Sources, and every source must be cited at least once.
   - If a source is no longer cited, remove it and renumber all citations consistently. Grep every [n] to check.

9. Checks
   - Run the overflow check on pages 05–10.
   - Do the dependency sweep.
```

---

## Prompt 9: Report, structure, checkpoints and page order

Applies the "General (structure)" corrections. Run it after Prompts 4–8.

```text
Read the "Shared context" section of reports/round-1/07_Claude_Code_prompts.md first and follow it. Run this prompt after Prompts 4–8.

Task: the "General (structure)" corrections. The three checkpoints must stand out from their sub-points, and the checkpoints must come before the code.

1. Page order
   - The new order is:
     1. Cover
     2. Checkpoint 1
     3. Sections 01–07
     4. Checkpoint 2
     5. Checkpoint 3
     6. 08 Code and 09 Portfolio description
     7. Sources
     8. Team & disclosures
   - Move whole <section class="page"> blocks without changing their content.

2. Checkpoints vs sub-points
   - On the three checkpoint pages, the top bar reads "Checkpoint N of 3 — <title>".
   - Add a small black pill reading "CHECKPOINT N" above the headline.
     - Style: Geist Mono 10–11px, uppercase, white text on #111111, border-radius 999px, padding about 3px 10px.
     - Black is the single accent the README allows.
   - Every sub-point uses "CPN.k · <title>". Check that CP1, CP2 and CP3 follow this; Prompts 5 and 7 should already have applied it.
   - No analysis section may use the pill.

3. Cover
   - Update the description of the two parts and the page references: Checkpoint 1 on page 2, and Checkpoints 2–3 on pages x–y, before the code.
   - Change "Published 16.10.26" to "18.10.26", the delivery date. The team confirms this.

4. Numbering and references
   - Renumber every footer "NN / TT" and the data-screen-label prefixes to follow the new order.
   - Fix every cross-reference in the text: pages, "section 0N", "Table N", "Figure N", "Checkpoint N".
   - Tables and figures must be numbered in reading order.

5. Checks
   Run the overflow check on all pages and take a screenshot of each page. Fix anything that is cut off.
```

---

## Prompt 10: Final check and PDF

Runs everything once more, checks every number against the JSON, checks the guidelines, and exports the PDF.

```text
Read the "Shared context" section of reports/round-1/07_Claude_Code_prompts.md first and follow it. Run this prompt last.

1. Run the whole notebook. It must finish without errors, so that report_figures.json and portfolio_for_PRTU.csv are current. Also check the notebook itself: no MAX_DD = None, no BCI_CLOSE = None, and no TODO left.

2. Numbers
   - Compare every number in the report (except section 01) with report_figures.json. List every mismatch and fix it.
   - Check the portfolio description against portfolio_for_PRTU.csv, share by share.

3. Leftovers
   - Grep the report for: "walk", "Walk", "8% target", "scale the risky", "8 + BIL", "[—]", "[TO FILL", "x.x", "BCOMTR INDEX", "four tests", "four versions", "four designs", "23.55".
   - Report anything left. [TO FILL] items go to the team, each with what is missing.

4. Requirements
   Check the report against these requirements:
   - the Round 1 guidelines: §7, analysis items 1–7 and the three checkpoints;
   - the three assignment slides:
     - Class 3 Part I, "Assignment: your investment policy (AMC checkpoint 1)";
     - Class 3 Part II, "Assignment 1: your allocation vs. the robust approaches";
     - Class 4, "Assignment: the backtest protocol (round-1 report)".
   Make a table of each requirement and the page that meets it. Checkpoint 1 must be one page, and it must be the first page after the cover.

5. Layout
   - Run the overflow check on all pages and take screenshots.
   - Check the footer numbering.
   - Check that sources and citations match in both directions.

6. PDF
   - Export reports/round-1/round-1.pdf: A4, no margins, backgrounds on, as the README specifies.
   - If Playwright allows it, use page.pdf({ format: 'A4', printBackground: true, preferCSSPageSize: true }). Otherwise, tell the team to print from Chrome as the README explains.
   - Check the page count, and that no page is cut.

7. Hand-over
   List the files to deliver:
   - the report PDF;
   - the notebook;
   - the code data/ files;
   - portfolio_for_PRTU.csv;
   - report_figures.json.
   Also give the PRTU steps from the notebook's "In Bloomberg" cell, with the share counts.
```

---

## Deferred: section 01, market outlook (no prompt yet)

The team chose not to change the market outlook for now. These are the corrections from the doc to pick up later:

- The market outlook was written for the presentation, not for the report. It can be shortened.
- The draft says developed economies are overheated, but growth was higher by only 0.1%. Is that enough? It also looks only at quarters, while an SAA probably needs a longer horizon (one year at least).
- The draft may lack data and evidence on US mega-cap concentration to support our choice of 3 ETFs weighted by risk contribution (A4). Prompts 5 and 8 cover the A4 argument in Checkpoint 1 and in 3.1.
- The draft lacks a short geopolitical outlook for commodities, which has been relevant in recent months.

## Coverage map

Every item of `06_Report_draft_corrections.docx` and the prompt that handles it.

| Corrections doc item | Prompt |
|---|---|
| TO-DO 1: PRTU portfolio (16 Oct closes, BCI_CLOSE, 8 ETFs with BCI US Equity) | 1 |
| TO-DO 2: BIL 0.01% → 0; bonds and commodities first, then equity with the leftover (last USD 144.20 → 2 VEA) | 1 (code, done), 4 (portfolio table done; check) |
| TO-DO 3: why each backtest method is used | 2 (code), 7 (report) |
| TO-DO 4: ex-post volatility in Table 10 | 2 (8e), 7 |
| TO-DO 5: liquidity rule; BCI numbers; the other 7 ETFs on Bloomberg | 3 (fill-in), 5 |
| TO-DO 6: gold in BCOM 14.9%; look-through ≈ 13.0% | 3, 8 |
| TO-DO 7: correlation heatmap (RdBu_r) | 3 (colours), 8 |
| TO-DO 8: the code as origin of every number (Table 9, …) | 3, 10 |
| A2: BIL only to respect the 9% cap | 4, 5 |
| A3: risk budget rules, equity ≤ 70% of risk | 2 (§7b), 5, 6 |
| A4: regions ≥ 5%; mega-cap risk concentration | 5, 8 (outlook part deferred) |
| A5: liquidity, AUM > USD 1 billion | 3, 5 |
| B1: never-candidates; benchmarks vs diagnostics; economic grounds | 2, 6, 7 |
| B2: logic of each backtest; walk-forward out of the report | 2, 6, 7 |
| B3: Checkpoint 2 closing sentences | 7 |
| General: differentiate checkpoints from sub-points | 5, 7, 9 |
| General: checkpoints before the code | 9 |
| Checkpoint 1: % rules, RC reason and 70% bound, cash leg, mega caps, regions, liquidity | 5 |
| 01 Market outlook (4 bullets) | Deferred |
| 02–03: less verbose | 8 |
| 3.1 VTI: three ETFs not weighted by market cap hedge concentration | 8 |
| 3.2 TIP: partial inflation hedge | 8 |
| 3.3 Gold overlap with BCI | 8 |
| 3.4 BIL: 9% cap | 4 |
| 04: more nuance in the correlation colours | 3, 8 |
| 5.2: asset-class agnostic reason | 6 |
| 5.3: not picked ex ante; Table 5 without walk-forward | 6 |
| 5.4: diagnostics grouped; economic grounds | 2, 6 |
| 07: logic of each test; ex-post volatility; walk-forward dropped; look-ahead caveat | 7 |
| Checkpoint 2: B3 text; walk-forward figures removed | 7 |
| Checkpoint 3: variations without walk-forward; never-candidates statement | 2, 7 |
