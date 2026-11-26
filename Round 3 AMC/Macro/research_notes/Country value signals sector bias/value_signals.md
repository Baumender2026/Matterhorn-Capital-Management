# Country-level equity value signals for a monthly rotation among ~21 MSCI country indices

## Q1. Which value ratio works best at the country level, with what effect size, sample and horizon?

### Takeaway
Book-to-market (B/M) is the most validated monthly cross-country value signal in the primary literature. In AMP (2013), a monthly-rebalanced B/M strategy across 18 developed-market indices earned about 6% a year at a Sharpe ratio of about 0.6 (t ≈ 3.4, 1978–2011). For long horizons (10–15 years), CAPE and P/B forecast about equally well (Keimling 2016), and both beat trailing P/E and dividend yield. Broader and more recent samples (73 countries, 1996–2017) favour EBITDA/EV over B/M. Country value premia have also faded in the last decade and are concentrated in EM and frontier markets.

### Cited Findings
- **Asness, Liew & Stevens (1997, JPM 23(3)).** Country versions of B/M, market equity and 1-year past return (momentum) "help explain the cross-section of expected country returns". Portfolios sorted by country show the same profitability patterns as stock-level sorts. The authors argue that the stock/country parallel "bolsters the case" that the premiums are not data mining, but say investors "should interpret the evidence with caution". Only the abstract is available on AQR; I could not retrieve coefficients or t-stats. — [AQR abstract](https://www.aqr.com/Insights/Research/Journal-Article/Parallels-Between-the-Cross-Sectional-Predictability-of-Stock-and-Country-Returns?aqrPDF=1)
- **AMP (2013, JF) universe.** 18 developed equity index futures (AU, AT, BE, CA, DK, FR, DE, HK, IT, JP, NL, NO, PT, ES, SE, CH, UK, US) from Jan 1978 to Jul 2011. Price and book data come from MSCI and Bloomberg. The minimum cross-section is 8 indices, and all 18 are present after 1980. No EM markets are included. — [Asness, Moskowitz & Pedersen 2013, pp. 934–935](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)
- **AMP value signal for country indices.** "the previous month's BE/ME ratio for the MSCI index of the country." Rebalancing is monthly. — [AMP 2013, p. 937](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)
- **AMP Table I, Panel B, country indices, Jan 1978–Jul 2011:**
  - **Value.** Tercile returns P1/P2/P3 are 3.1% / 6.6% / 9.1% a year. P3–P1 earns 6.0% a year (t = 3.45, σ 9.8%, Sharpe 0.61, alpha 5.9%, t = 3.45). The signal-weighted factor earns 5.7% a year (t = 3.40, Sharpe 0.60).
  - **Momentum.** P3–P1 earns 8.7% (t = 4.14, Sharpe 0.73). The factor earns 7.4% (Sharpe 0.63).
  - **50/50 value plus momentum.** P3–P1 earns 7.3% (t = 6.62, σ 6.3%, Sharpe 1.16). The factor earns 10.6% (Sharpe 1.00).
  — [AMP 2013, Table I](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)
- **Long-only reading of the same table.** The cheapest tercile (P3) earned 9.1% a year (Sharpe 0.56) against 3.1% (Sharpe 0.19) for the most expensive tercile. These are excess returns on futures. — [AMP 2013, Table I](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)
- **Keimling (2016, StarCapital/SSRN 2736423).** The sample is the US (Shiller data from 1871) plus 16 MSCI country indices (monthly from 1969 or 1979; secondary summaries disagree on the start date), through 2015. Forecasts are real returns over the following 10–15 years.
  - The lowest CAPE decile returned 13.3% a year real. The lowest P/B decile returned 13.6%, and the lowest payout-adjusted CAPE decile 12.5%.
  - Starting from CAPE < 10, average real growth was 11.7% a year. Starting from CAPE > 30, it was 0.5%.
  - P/E, P/CF and dividend yield were "generally inferior to CAPE".
  - CXO's caveats: the tests are in-sample, there are few independent 10-year windows, results are fragile to excluding countries, and index structure changes over time.
  — [CXO summary](https://cxoadvisory.com/fundamental-valuation/comparing-cape-to-other-stock-market-valuation-ratios); [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2736423)
- **Keimling R² figures (secondary, unverified against the paper).** CAPE explained about 48% of later 10–15-year returns in developed markets. By country: Japan 90%, UK 86%, US 82% (since 1970), US 46% (since 1881), Canada 1%. — [Monevator, citing Keimling](https://monevator.com/cape-ratio-by-country/)
- **Zaremba & Szczygielski (2019, JPM 45(5), "And the Winner Is…").** They compare 14 valuation ratios across 73 national indices, 1996–2017.
  - EBITDA/EV is the best predictor. An equal-weighted top-minus-bottom tertile earned 0.69% a month at a Sharpe of 0.81, "more than double" the Sharpe of traditional B/M and dividend yield.
  - Returns come mainly from EM and frontier markets, and profitability "has declined significantly over the last decade".
  — [Northumbria research portal abstract](https://researchportal.northumbria.ac.uk/en/publications/and-the-winner-is-a-comparison-of-valuation-measures-for-equity-c/)
- The same paper reportedly finds that traditional B/M performs poorly for country selection, while EBITDA- and sales-based ratios survive controls for momentum, size, long-run reversal, seasonality and beta. This is from a search-engine summary only (the full text returned 403). — [Alpha Architect summary (not fetched)](https://alphaarchitect.com/ebitda-to-ev-wins-again/)

### Inferences
- For a 21-country universe (DM plus EM), B/M has the strongest primary monthly-frequency evidence (AMP), and AMP built its B/M from MSCI and Bloomberg data, the same source we would use. CAPE and P/B are the strongest long-horizon level signals. A composite (for example the average z-score of P/B, CAPE and forward or trailing E/P) reduces dependence on any single ratio, which matters because Zaremba & Szczygielski find large differences between ratios.
- Expect a smaller premium than the 1978–2011 backtests. Post-2010 decay is documented (Zaremba & Szczygielski), and the AMP spread is long-short. A long-only top-N tilt captures only part of it: the P3 minus equal-weight difference is roughly 3 percentage points a year before costs.
- Use sector-neutral or relative-to-own-history valuation where possible. Country P/B levels differ structurally (for example, high-tech vs bank-heavy indices), which matches the "sector bias" in this folder's name. I have not verified this point in a source.

### Gaps
- I could not retrieve ALS (1997) regression coefficients, t-stats or spreads; only the abstract is accessible.
- Keimling's primary PDF was not retrieved. The R² values are secondary and possibly in-sample.
- Head-to-head 1-month results for CAPE vs P/B vs P/E vs dividend yield on a comparable 21-country DM+EM universe were not found in a primary source. A secondary summary of Zaremba's 2014 working paper reports 0.40% a month for B/M and 0.74% for dividend yield (long-short quintiles), but I could not verify the source.

## Q2. Is country value a 1-month signal or a long-horizon signal, and how does it combine with 12-1 momentum?

### Takeaway
Value works when rebalanced monthly (AMP: Sharpe about 0.6 on monthly-updated B/M), but its information is slow-moving and it predicts best over multi-year horizons, where CAPE and P/B explain a large share of 10–15-year returns. It is negatively correlated with 12-1 momentum, so a 50/50 combination roughly doubles the Sharpe ratio of either signal alone (1.0–1.16 vs about 0.6–0.7).

### Cited Findings
- AMP use 12-month momentum skipping the most recent month for all asset classes. For index futures, momentum is "stronger when we don't skip the most recent month". — [AMP 2013, p. 937](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)
- Country indices, 50/50 value plus momentum: P3–P1 Sharpe 1.16 (t = 6.62), factor Sharpe 1.00 (t = 5.72). This compares with value alone at 0.61 and momentum alone at 0.73. — [AMP 2013, Table I](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)
- The value–momentum return correlation for country indices appears as −0.34 (P3–P1) and −0.37 (factor) in Table I. This is my reading of the extracted table layout, which was jumbled, so confirm it in the PDF. For global stocks the correlation is −0.52 / −0.60, and the stock-wide average is −0.53 (Table II). — [AMP 2013, Tables I–II](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)
- Some of the negative correlation comes from using the current price in BE/ME. Lagging ME by one year still leaves a correlation of −0.28 in stocks. Using −5-year return as the value signal gives −0.48. — [AMP 2013, pp. 950–951](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)
- Country value, momentum and global-stock value are correlated across asset classes. Country-index value correlates 0.27 with global stock value, and country-index momentum correlates −0.28 with global stock value. — [AMP 2013, Table II Panel B](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)
- Keimling's evidence is explicitly about 10–15-year horizons. CXO notes that CAPE "may not have been exploitable in real time". — [CXO](https://cxoadvisory.com/fundamental-valuation/comparing-cape-to-other-stock-market-valuation-ratios)

### Inferences
- For a monthly rotation, use value as a slow tilt combined with 12-1 momentum, for example by averaging z-scores. Value alone at a 1-month horizon gives a low-information-ratio signal with high turnover only when prices move. Combining the two exploits the negative correlation.
- Because value signals change slowly, a monthly rebalance driven only by value would generate little turnover. Most turnover will come from the momentum leg.

### Gaps
- No primary source found that gives a decay profile of country value predictability by horizon (1, 3, 12 or 36 months) on the same sample.

## Q3. Evidence on long-run (3–5 year) price reversal across countries

### Takeaway
National indices mean-revert relative to each other with a half-life of about 3–3.5 years (Balvers, Wu & Gilliland 2000). Past 3–5-year losers outperform past winners, and risk does not explain it (Richards 1997). In stocks, AMP show that −5-year return is a close proxy for B/M (factor correlation 0.83–0.86), which supports using it as a value fallback where book data are thin.

### Cited Findings
- **Balvers, Wu & Gilliland (2000, JF 55(2):745–772).** 18 countries, 1969–1996. "Strong evidence" of mean reversion in relative index prices, with a half-life of 3–3.5 years. Parametric contrarian strategies beat buy-and-hold and standard contrarian strategies. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v55y2000i2p745-772.html)
- **Richards (1997, JF 52(5):2129–2144).** Winner–loser reversals in 16 national indices. Loser countries are not riskier on standard deviation, beta to the world market, other factors, or performance in bad states. Smaller markets show larger reversals, but reversals are not confined to small markets. The anomaly is "unresolved". — [IMF WP/97/182](https://www.imf.org/en/Publications/WP/Issues/2016/12/30/Winner-Loser-Reversals-in-National-Stock-Market-Indices-Can-they-Be-Explained-2458); [RePEc](https://ideas.repec.org/a/bla/jfinan/v52y1997i5p2129-44.html)
- **AMP on −5-year return as value.** For commodities and currencies, AMP define value as −5-year return, using the average price 4.5–5.5 years ago to avoid noise. In stocks, the −5-year-return value factor correlates 0.83 with B/M sorts in the US and 0.86 globally. — [AMP 2013, pp. 937–938](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)
- **Zaremba, Kizys & Raza.** International equity returns back to 1830. The long-term reversal is "not subsumed" by other patterns, including the value effect. This is abstract-level only; the full text returned 403. — [Southampton ePrints](https://eprints.soton.ac.uk/436972/)

### Inferences
- A 60-month return skipping the most recent 12 months (or AMP's 4.5–5.5-year average-price version) is a useful second value leg. It needs only prices, which helps EM indices with short or noisy book and earnings histories, and it is partly independent of accounting-based value.
- Skip the latest 12 months so the reversal signal does not mechanically offset 12-1 momentum.

### Gaps
- Richards' exact reversal magnitudes (the % a year spread for 3-year losers minus winners) were not retrievable; the paper is paywalled.

## Q4. Bloomberg field availability for MSCI country indices, and building CAPE

### Takeaway
MSCI computes index-level P/E, forward P/E, P/BV and dividend yield as aggregate (cap-weighted, float-adjusted) ratios from trailing 12-month per-share data. DM EPS history starts in Dec 1969 and EM EPS history in Jan 1992. A CAPE can therefore be built from a monthly index trailing EPS history (implied EPS = price ÷ P/E), deflated by CPI. I did not find Bloomberg's own field documentation for the specific mnemonics, so check them in the terminal (FLDS).

### Cited Findings
- **MSCI index valuation ratios.** Computed as Σ(price × shares × 1/FX × inclusion factor) / Σ(trailing 12-month per-share figure × shares × 1/FX × inclusion factor). Securities with no trailing figure are excluded. This applies to P/E, P/E Fwd, P/E Bwd, P/CE and P/BV. Dividend yield uses the inverse. MSCI also publishes "12-month Index EPS". — [MSCI Fundamental Data Methodology, Mar 2021, §3.1–3.2](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Fundamental_Data_Methodology_Mar2021.pdf)
- **Historical coverage.**
  - EPS and P/E: since Dec 1969 (DM) and Jan 1992 (EM).
  - P/BV: since Jan 1992 for EM. The DM start date was not legible in the extract.
  - Dividends: DM since Jan 2001 in the table as extracted.
  - Forecast data are refreshed monthly.
  — [MSCI methodology, p. 18](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Fundamental_Data_Methodology_Mar2021.pdf)
- **MSCI earnings adjustments.** MSCI normalises EPS for unusual items (restructuring, impairments, disposals, etc.) and restates history for corporate events. — [MSCI methodology §1.2](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Fundamental_Data_Methodology_Mar2021.pdf)
- **CAPE convention for country indices.** Real index price divided by the 10-year average of real trailing earnings, deflated with the local CPI. — [Siblis Research methodology](https://siblisresearch.com/docs/Siblis-Research-Data-Methodology.pdf)
- AMP sourced country BE/ME from MSCI and Bloomberg. — [AMP 2013](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)

### Inferences
- **Practical CAPE build.** Pull PE_RATIO (or a trailing EPS field) and PX_LAST monthly with BDH on the MSCI country index tickers. Compute EPS_t = PX_LAST / PE_RATIO, convert to real terms with local CPI (or use USD price and EPS with US CPI, consistently), and average over 120 months.
  - EM series begin in 1992, so a full 10-year CAPE is only available from about 2002. Before that, use a 5-year version or P/B.
  - Watch for negative or near-zero aggregate EPS (Bloomberg often returns blank P/E), which breaks the price ÷ P/E inversion.
- BEST_PE_RATIO (consensus forward) history on indices usually starts later and covers fewer countries than trailing P/E. EQY_DVD_YLD_12M on indices may need the index-specific equivalent field. Verify each field on 2–3 tickers first (for example MXGB, MXBR, MXIN Index).

### Gaps
- I found no Bloomberg documentation (FLDS/DES) confirming that PX_TO_BOOK_RATIO, PE_RATIO, BEST_PE_RATIO, EQY_DVD_YLD_12M or TRAIL_12M_EPS populate for MSCI country index tickers, or their start dates. This needs an in-terminal check.
- Whether Bloomberg's index P/E for MSCI tickers comes from MSCI's own aggregation or from Bloomberg's constituent aggregation is not documented in the sources reviewed.
