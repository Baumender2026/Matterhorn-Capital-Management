# Sector-composition bias in cross-country valuation (P/B) for a monthly MSCI country rotation

Scope: making country P/B comparable across ~21 MSCI country indices; own-history vs cross-sectional signals; evidence that the adjustment helps; what is doable in 2 days with Bloomberg.
Core sources (6): Keimling/StarCapital 2016; Keimling/StarCapital 2015 (sector-adjusted, original PDF now offline); Novy-Marx 2013; Asness-Porter-Stevens 2000; Zaremba-Szczygielski (country valuation horse race); MSCI Enhanced Value methodology. Secondary/blog sources are marked as such.

## Q1. Methods for sector-neutral / sector-adjusted country valuation

### Takeaway
Practitioners use three methods. (a) Reweighting: apply one region's sector weights to the other region's sector multiples, or compute a "fair" benchmark multiple for each country using its own sector mix and global sector multiples. (b) Sector-relative z-scores: score each holding against its own sector. (c) Sector-by-sector comparison, e.g. banks vs banks. StarCapital (Keimling) has the only dedicated country-level paper I found. Its method could not be retrieved, but its motivation (sector shifts break country CAPE/PB comparability) is documented in the 2016 paper.

### Cited Findings
- StarCapital published "Sector Adjusted Country Valuation" (Keimling, April 2015). The original link `starcapital.de/docs/2015-04_Sector_Adjusted_Country_Valuation_Keimling.pdf` now redirects to Bellevue (StarCapital's acquirer), and I could not retrieve the paper (Wayback not reachable from this environment). The link is cited in [Fortune Financial Advisors, Jan 2017](https://fortunefinancialadvisors.com/?p=227).
- Reweighting example (blog, forward P/E, not P/B): multiply MSCI World ex-USA sector weights by sector-ETF forward P/Es and re-normalise, then reverse the exercise. Results: ex-US at S&P 500 sector weights ≈ 17.44x forward P/E; S&P 500 at ex-US weights ≈ 17.58x. The author concludes regional valuations "aren't all that different" once sector mix is equalised — [Fortune Financial Advisors, 2017](https://fortunefinancialadvisors.com/?p=227). (The page's text calls 17.58 "slightly lower", so its wording is internally inconsistent.)
- A 2017 Nasdaq article, "Country Valuation Differences Often Caused By Sector Structure", is summarised in search results as saying Denmark's P/B would be 2.5 (vs actual 2.1) if the global market had Denmark's sector mix, i.e. roughly half of Denmark's apparent premium is sector structure. **Not verified**: the page timed out twice, and I saw only the search-engine summary — [Nasdaq, 2017-12-20](https://www.nasdaq.com/articles/country-valuation-differences-often-caused-sector-structure-2017-12-20).
- MSCI's value indices use a sector-relative score: z-scores of P/B, forward P/E and EV/CFO computed **relative to the sector** and winsorised at ±3, then combined. This is a direct template for a "sector-relative" valuation score — [MSCI Enhanced Value Index Methodology](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Enhanced_Value_Index_Meth_Aug14.pdf) (as summarised in search results; PDF not opened).
- Stock-level analogue: Asness, Porter & Stevens (2000) split each characteristic (B/M, CF/P, size, momentum) into a within-industry deviation and an industry average. Each is "reliably priced within-industry", and the within-industry measure gives "more precise estimates" than the raw form. Later work cites them as showing most of B/M's predictive power is within-industry — [AQR working paper page](https://www.aqr.com/Insights/Research/Working-Paper/Predicting-Stock-Returns-Using-IndustryRelative-Firm-Characteristics).
- Sector-by-sector comparison (practitioner): Columbia Management notes financials were ~25% of the European index vs 18% in the US. Comparing "banks to banks, insurance to insurance" shrinks the Europe–US valuation gap considerably — [Advisor Perspectives, 2014](https://www.advisorperspectives.com/commentaries/2014/12/03/digging-deeper-for-market-valuations) (search-result summary).
- Counterpoint: Cambridge Associates (2019) argues the US profitability premium (higher ROE/ROIC) is "not merely a reflection of sector composition differences". So part of a raw P/B gap is justified by profitability even after sector adjustment — [Cambridge Associates VantagePoint Q3 2019](https://publishedresearch.cambridgeassociates.com/wp-content/uploads/2019/07/VantagePoint-Q3-2019.pdf) (search-result summary).

### Inferences
- The simplest country-level formula follows from the reweighting idea. Let w_{c,s} be the weight of sector s in country c and PB_s^{World} the World sector P/B. Then **implied PB_c = Σ_s w_{c,s} · PB_s^{World}** (better done as harmonic or aggregate-book weighting, i.e. 1/Σ w/PB), and the **sector-adjusted signal = log(PB_c / implied PB_c)**. A negative value means the country is cheap relative to what its sector mix would justify.
- A second route is a cross-sectional regression each month: log PB_c on the country's sector weights (or just on Financials+Energy+Materials weight vs Tech+Health Care weight). The residual is the signal. With only 21 countries, use at most 1–2 sector regressors to avoid overfitting.
- P/B is particularly sector-sensitive. Banks, energy and materials trade at structurally low P/B, while tech and health care trade at high P/B with intangible-heavy books. So country rankings on raw P/B tend to become "overweight financial/commodity markets" (e.g. Italy, Spain, Austria, Norway, Brazil-type markets) vs "underweight US/Denmark/Switzerland".

### Gaps
- Could not read Keimling (2015) itself, so its exact formula and any backtest are unknown.
- I found no MSCI research note that publishes sector-adjusted country P/B with a return test.

## Q2. Valuation vs own history (z-score / percentile) vs raw cross-section

### Takeaway
Long-horizon evidence (StarCapital) shows country P/B levels are fairly comparable across developed markets: the cross-country dispersion of average P/B is ~13% vs ~25% for CAPE. P/B also predicts 10–15y returns within most countries. Structural change (sector shifts, shrinking constituent lists) degrades both own-history and cross-country comparability. Practitioner opinion favours own-history comparison. I found no rigorous horse race of own-history z-score vs raw cross-section at a monthly horizon.

### Cited Findings
- Keimling (StarCapital, Jan 2016), 17 MSCI countries, 12/1979–05/2015. Mean country P/B ranges from 1.6 (Belgium, France, Hong Kong) to 2.5 (USA). The relative standard deviation of mean P/B across countries is **12.8%** (medians 12.6%), vs **24.7%/26.9%** for payout-adjusted CAPE. So P/B "normal levels" differ less across countries than CAPE — [Keimling 2016, Fig. 10–11](https://gallery.mailchimp.com/6750faf5c6091bc898da154ff/files/Research_2016_01_Predicting_Stock_Market_Returns_Shiller_CAPE_Keimling_1_.pdf).
- Same paper, P/B vs subsequent 10–15y real returns, per-country R² (read from Fig. 12; the extracted text is garbled, so treat these as approximate): Australia 0.86, Belgium 0.85, Canada 0.10, Denmark 0.35, France 0.72, Germany 0.76, Hong Kong 0.90, Italy 0.95, Japan 0.34, Netherlands 0.93, Norway 0.54, Singapore 0.62, Spain 0.88. The pooled CAPE/PB relationship is R² ≈ 0.5 with correlation just under −0.7. CAPE and PB beat P/E, P/CF and dividend yield — [Keimling 2016](https://gallery.mailchimp.com/6750faf5c6091bc898da154ff/files/Research_2016_01_Predicting_Stock_Market_Returns_Shiller_CAPE_Keimling_1_.pdf).
- Structural change in Keimling (2016):
  - MSCI Denmark's health-care weight rose from ~10% to ~60% while constituents fell from >20 (1994) to 11 (2011).
  - Removing markets with >10% sector-weight changes over two decades (Australia, Belgium, Canada, Denmark, Italy, Netherlands, Norway, Sweden) lifts the pooled CAPE R² from **0.49 to 0.58**.
  - Conclusion: "the comparability with a country's own history and among countries seems to decrease with structural changes."
  - Book values fluctuate less than earnings, which avoids the 10-year smoothing and its "constant market structure" assumption.
  - [Keimling 2016](https://gallery.mailchimp.com/6750faf5c6091bc898da154ff/files/Research_2016_01_Predicting_Stock_Market_Returns_Shiller_CAPE_Keimling_1_.pdf)
- Practitioner opinion: compare a country's CAPE "only with its own historical average"; inter-market comparisons are "problematic" — [Monevator](https://monevator.com/cape-ratio-by-country/); similar view in [Siblis Research](https://siblisresearch.com/data/cape-ratios-by-country/) (opinion, not tested).
- Short-horizon signal decay: valuation-based country timing worked strongly 1995–2006 but shows "a marked flattening" after 2006 — [Alpha Architect, valuation horse race](https://alphaarchitect.com/timing-country-exposure-value-valuation-measure-horserace/) (search-result summary; page returned 403).

### Inferences
- Pros of own-history z-score:
  - It removes persistent country fixed effects, i.e. the part of the level driven by a stable sector mix, accounting or ROE.
  - It is trivial to compute.
- Cons of own-history z-score:
  1. It fails exactly when the sector mix *changes* (Denmark/Novo, Netherlands/ASML, Taiwan/TSMC), because the "own history" belongs to a different index.
  2. It throws away the cross-sectional level information that the long-horizon evidence says is predictive.
  3. It needs a long window (5–10y) and therefore a data start ≥ 5y before the backtest.
  4. It has look-ahead bias if a full-sample mean/sd is used. Use rolling (e.g. 60–120m) or expanding windows only, with stats computed through t−1.
- A pragmatic compromise is a **blend**: 50% cross-sectional rank of log P/B + 50% own-history rolling z-score. Alternatively, z-score the *sector-adjusted* ratio (Q1) vs its own history, which handles both level and mix drift.
- Monthly rotation horizon vs evidence horizon: the cited P/B evidence is about 10–15y returns. Monthly predictive power of value at the country level is weak and should be combined with momentum (cf. the Novy-Marx and AQR value+momentum logic below).

### Gaps
- I found no paper quantifying own-history z-score vs raw cross-section for monthly/annual country selection. The CERGE-EI working paper (Gupta & Novotný 2016) turned out to be a DCC model of CAPE comovement, not a horse race.

## Q3. Does sector adjustment improve (out-of-sample) performance?

### Takeaway
Strong evidence at the **stock level**: industry-adjusted/industry-hedged value roughly doubles HML's Sharpe ratio. At the **country-index level**, no quantified backtest of sector-adjusted P/B was found. The supportive evidence is indirect: R² rises when structurally shifting markets are dropped, and raw B/M is the weakest valuation ratio for country selection.

### Cited Findings
- Novy-Marx (2013, JFE; NBER w15940), US 7/1963–12/2010:
  - Conventional HML earns 0.40%/month (t = 3.25), annual Sharpe **0.47**.
  - Industry-hedged HML earns 0.36%/month, Sharpe **0.88**. UMD goes from 0.57 to 0.79 and PMU from 0.35 to 0.52.
  - "Hedging the strategies decreases the average returns … but increases all three strategies' Sharpe ratios", and conventional HML has significantly negative alpha relative to the hedged version.
  - With industry-adjusted sorts, 80–90% of the industry hedges net out between the long and short sides.
  - [Novy-Marx, The Other Side of Value (PDF)](https://www.johnhcochrane.com/s/Novy_marx_OSoV.pdf); [NBER w15940](https://www.nber.org/papers/w15940)
- Novy-Marx cites Cohen & Polk (1998), Asness-Porter-Stevens (2000) and Novy-Marx (2009, 2011) as finding that industry-adjusted B/M strategies "significantly outperform their conventional counterparts" — [Novy-Marx 2013](https://www.johnhcochrane.com/s/Novy_marx_OSoV.pdf).
- Country level, raw ratios: Zaremba & Szczygielski compared 14 valuation ratios across 73 country indices (1996–2017). EBITDA/EV performed best, and "the traditional and commonly applied ratio (book to market) performs poorly when applied to country selection" — [Alpha Architect summary](https://alphaarchitect.com/ebitda-to-ev-wins-again/); [Northumbria research portal](https://researchportal.northumbria.ac.uk/en/publications/and-the-winner-is-a-comparison-of-valuation-measures-for-equity-c/) (search-result summaries; full text not read).
- Country level, structural change: dropping markets with large sector shifts raises the pooled CAPE→return R² from 0.49 to 0.58 — [Keimling 2016](https://gallery.mailchimp.com/6750faf5c6091bc898da154ff/files/Research_2016_01_Predicting_Stock_Market_Returns_Shiller_CAPE_Keimling_1_.pdf). This is in-sample and long-horizon, not an out-of-sample test of an adjusted signal.
- Asness & Frazzini, "The Devil in HML's Details" (JPM 2013), is about **timely prices** (current price vs 6–18-month-lagged price in B/P), not industry adjustment. The timely version is weaker stand-alone but better combined with momentum — [AQR](https://www.aqr.com/insights/research/journal-article/the-devil-in-hmls-details). It is relevant only as an implementation detail: use the current month's P/B.

### Inferences
- The stock-level result (sector exposure is mostly unrewarded noise in value sorts) transfers by analogy. A raw country P/B signal is partly a bet on Financials/Energy vs Tech/Health Care, which adds volatility without obvious premium. Expect sector adjustment to raise the **Sharpe/IR more than the mean return**, consistent with Novy-Marx.
- With 21 countries and a long-only top-N portfolio, any improvement will be noisy. Report the IC (rank correlation of signal vs next-month return) for raw vs adjusted signals rather than relying on a single backtest path.

### Gaps
- No out-of-sample, quantified country-index result for sector-adjusted P/B was found (Keimling 2015 might contain one but was unreachable).
- No result for own-history-z-scored P/B in a monthly rotation.

## Q4. What is implementable in a 2-day student project with monthly Bloomberg data

### Takeaway
Tier 1 (hours): own-history rolling z-score and cross-sectional rank of `PX_TO_BOOK_RATIO`. Tier 2 (about half a day): a cross-sectional regression residual using one or two sector-share regressors, or a P/B-to-ROE adjustment. Tier 3 (likely too costly): a full sector-reweighted implied P/B, which needs country×sector weights and P/B histories.

### Cited Findings
- P/B is preferable to CAPE for cross-country use, because its cross-country level dispersion is ~half that of CAPE and it needs no 10-year smoothing — [Keimling 2016](https://gallery.mailchimp.com/6750faf5c6091bc898da154ff/files/Research_2016_01_Predicting_Stock_Market_Returns_Shiller_CAPE_Keimling_1_.pdf).
- MSCI's own approach (sector-relative z-scores winsorised at ±3) provides the scoring convention to copy — [MSCI Enhanced Value methodology](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Enhanced_Value_Index_Meth_Aug14.pdf).

### Inferences (implementation recipe; not sourced, based on the above)
1. **Baseline:** S1 = −cross-sectional z-score of log(PX_TO_BOOK_RATIO) each month.
2. **Own-history:** S2 = −[log PB_t − mean(log PB_{t−60..t−1})] / sd(same window). Use a rolling 60m window (expanding if history is short), with no full-sample statistics, and require ≥36 months.
3. **Profitability-adjusted (cheap proxy for sector/quality bias):** regress log P/B on ROE across the 21 countries each month (Bloomberg `RETURN_COM_EQY` or the implied ROE = P/B ÷ P/E). Use the residual as the value signal, since "justified P/B" rises with ROE. This partly absorbs sector mix, because high-P/B sectors are high-ROE sectors.
4. **Sector regressor (if data permit):** pull the MSCI country × GICS sector index market caps (MSCI publishes country-sector indices; Bloomberg tickers exist but must be looked up per country). Compute the Financials+Energy+Materials share and regress log P/B on it cross-sectionally; use the residual. If sector-weight history is unavailable, use a static current-weight snapshot only as a robustness check, and flag the look-ahead.
5. **Evaluate:** monthly rank IC and top-tercile vs bottom-tercile spread for S1, S2, S3 and the S1+S2 blend. Combine with 12-1 momentum, since value alone is weak at monthly horizons and value+momentum is the standard pairing (Asness-Frazzini; Novy-Marx).

### Gaps
- I did not confirm Bloomberg field availability or history depth for MSCI country-sector weights. Verify on the terminal (e.g. MSCI country-sector index tickers and `CUR_MKT_CAP`/`INDX_MWEIGHT`).
