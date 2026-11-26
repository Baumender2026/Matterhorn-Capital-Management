# Follow-up: recent long-term reversal evidence and the Wilcox P/B-ROE model

Literature check, 26 Nov 2026. Primary sources preferred. "Read" = full text read; "abstract" = abstract/secondary only.

---

## Q1. Long-term reversal across country indices: does it survive post-2010 and after value?

### Summary verdict
Over very long samples, country-level long-term reversal exists and is not subsumed by value. In the last 20–25 years it has disappeared or flipped sign, especially in large and developed markets and in cap-weighted portfolios. Two independent papers by Zaremba and co-authors find this directly with country-level value controls. The best recent evidence says reversal adds nothing (or hurts) for a developed-heavy universe after ~2005.

### Sources

**1. Zaremba (2016), "Has the Long-Term Reversal Reversed? Evidence from Country Equity Indices", *Romanian Journal of Economic Forecasting* 19(1): 88–103.** [IDEAS](https://ideas.repec.org/a/rjr/romjef/vy2016i1p88-103.html). Full text read (publisher PDF via the IDEAS link).
- Sample: 74 countries (MSCI, Bloomberg, USD), Jan 1995 – Feb 2015. Returns from Jan 1999 (193 months). The average cross-section is 49 countries. Survivorship-free.
- Signal: cumulative excess return t−60 to t−13 (skip 12m, following Malin & Bornholt), quintiles, cap-weighted, monthly rebalance.
- Result (Table 1): Losers − Winners = **−1.22%/month (t = −2.36)**. The country 4-factor alpha (market, SMB, HML on **B/M**, WML) = **−1.09%/month (t = −2.42)**. Winners beat losers, and the result holds after value, size and momentum controls.
- Robustness (Tables 2–4):
  - 36m formation: −0.29% (t −0.44); 48m: −0.77% (t −1.69).
  - Equal-weighted: −0.37% (t −1.74), with alpha −0.37% (t −1.16).
  - Large markets: −1.93% (t −3.62). Small markets: 0.01%.
  - **Developed: −0.47% (t −1.58), alpha −0.55% (t −1.63)**. Emerging: −0.97% (t −1.97).
- Takeaway for us: in a developed-heavy, roughly 21-country universe, 1999–2015 shows no reversal premium. The point estimate has the wrong sign.

**2. Zaremba & Umutlu (2020), "Where Have the Profits Gone? Market Efficiency and the Disappearing Equity Anomalies in Country and Industry Returns", *Journal of Banking & Finance* 121, 105966.** (The published version adds Maydybura as co-author.) [IDEAS](https://ideas.repec.org/a/eee/jbfina/v121y2020ics0378426620302284.html); [EFMA 2020 working paper PDF](https://www.efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2020-Dublin/papers/EFMA%202020_stage-1301_question-Full%20Paper_id-125.pdf). Working-paper text read.
- Sample: 53 anomalies, 64 country markets (plus industries), 1973–2018. Subperiods: 1976–1990, 1991–2004, 2005–2018.
- The composite **country reversal** alpha (monthly) falls from **1.19% EW / 1.27% VW (1976–90) to −0.24% EW / −0.49% VW (2005–18)**. The authors describe long-run reversal profits as having "turned into massive losses during the last 10–20 years".
- The composite **country value** alpha falls to **0.02% EW / 0.03% VW** in 2005–18, no longer significant. Low-risk anomalies were the only robust category.
- The decline is strongest in large developed markets. The authors attribute it to market efficiency, not to publication or risk changes. The full-sample VW reversal composite is already insignificant for countries.
- Takeaway: this is the cleanest evidence on the decay question. **Decay dates from about 2005, for both reversal and value.**

**3. Zaremba, Kizys & Raza (2020), "The Long-Run Reversal in the Long Run: Insights from Two Centuries of International Equity Returns", *Journal of Empirical Finance* 55: 177–199.** [Southampton eprints 436972](https://eprints.soton.ac.uk/436972/); [IDEAS](https://ideas.repec.org/a/eee/empfin/v55y2020icp177-199.html). Abstract and search snippets only (PDF blocked, 401/403).
- Sample: 71 countries, 1830–2019.
- Abstract: past long-term return "negatively predicts future performance". The effect is "not subsumed" by value and other cross-sectional effects, "robust to many considerations but highly unstable through time". The authors read it as overreaction.
- Manuscript snippet (not verified against the published tables): a winners-minus-losers quintile strategy earns **−0.38%/month** (losers beat winners by ≈4.6%/yr), with a nine-factor alpha of **−0.47%/month**.
- Gap: subperiod tables not seen. The authors cite their own 2015/16 finding that the effect was "questionable" over the last 20 years. So the long-sample result does not contradict the recent decay: it is a 190-year average dominated by earlier history.

**4. Malin & Bornholt (2013), "Long-term return reversal: Evidence from international market indices", *J. Int. Financial Markets, Institutions & Money* 25: 1–17.** [IDEAS](https://ideas.repec.org/a/eee/intfin/v25y2013icp1-17.html). Abstract only.
- Reversal exists in developed and emerging indices, and is stronger with a "late-stage contrarian" filter that uses recent short-term returns.
- But **developed markets show no cross-sectional contrarian profits post-1989**. Only a time-series (own-history) variant still works there.
- The follow-up time-series study is Kobinger, Bornholt & Malin (MSCI developed). Above-normal returns after extreme lows appear for about half of the indices ([conference PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0008/56456/43093-S-Kobinger-Long-Term-Time-Series-Reversal-International-Evidence_Sonja-Kobinger,-Graham-Bornholt,-Mirela-Malin.pdf), not read, 403).

**5. Quantpedia, "Mean Reversion Effect in Country Equity Indexes"** (source: Richards 1997, 16 markets 1969–1995, ≈6.4%/yr for 36m holding). [Quantpedia](https://quantpedia.com/strategies/mean-reversion-effect-in-country-equity-indexes). Practitioner page.
- States that its OOS backtest "shows significantly negative performance" and rates confidence "Weak". No OOS period or figures are given.

**Not found / not checked:** AMP (2013) use B/M, not a −5y return, as value for country indices. So they give no country-level reversal result to cite beyond the stock-level 0.86 correlation already in the report. No AQR or Research Affiliates note specific to country reversal was found in this check.

### Implication for the notebook
- Treat −return(t−60, t−12) as at most a **robustness variant, not a core leg** of the value composite. Post-2005 evidence for developed, cap-weighted country universes points to zero or a negative premium.
- If kept, use it as a value proxy only where book data is missing, and report it separately.

---

## Q2. Wilcox P/B-ROE model

### Citations (confirmed)
- **Wilcox, J.W. (1984). "The P/B-ROE Valuation Model." *Financial Analysts Journal* 40(1): 58–66.** DOI 10.2469/faj.v40.n1.58. [CFA Institute](https://rpc.cfainstitute.org/en/research/financial-analysts-journal/1984/the-pb-roe-valuation-model)
- **Wilcox, J.W. & Philips, T.K. (2005). "The P/B-ROE Valuation Model Revisited." *Journal of Portfolio Management* 31(4): 56–66.** SSRN working version: "The P/B-ROE Model Revisited" (10 Mar 2004), [SSRN 534442](https://ssrn.com/abstract=534442). The JPM volume and pages come from the reference list of a UCT thesis ([Coultas, UCT](https://open.uct.ac.za/bitstreams/8805f64b-22ed-497e-b25b-bfc01b5f1464/download)). The SSRN id comes from [Bianconi & Yoshino 2017](https://mbiancon.pages.tufts.edu/SEF-04-2016-0095_01.pdf). Spelling: "Philips" (one l).

### What the model says
- Two-stage growth model: ln(P/B) ≈ (ROE − k)·T, where T is the "investment horizon" over which above-normal ROE persists. Empirically: regress **ln(P/B) on ROE** cross-sectionally. The slope estimates T, and the residual is "cheap/expensive given profitability".
- 1984 (abstract): historical ROE is a fair predictor of future ROE. On Value Line data the model beats P/E models on **mean squared error of price fit** for most companies. It can back out the market's consensus ROE, required return and horizon. It also argues higher-beta stocks do not earn the CAPM-implied premium. **This is in-sample fit, not a return-prediction test.**
- 2004/05 (from the slide version, [pdf4pro mirror of the conference slides](https://pdf4pro.com/view/the-p-b-roe-model-revisited-cb53.html)):
  - Value Line 1988–2002, December fiscal year-ends, ROE between −10% and +40%, >20,000 firm-years.
  - **Pooled R² = 26%**, approaching **50% for the most ROE-stable quartile**. T rises to about **9 years** for very stable firms.
  - Example: 15% → 20% ROE implies a **+38% price** for a stable firm.
  - Return prediction is shown only as a chart: the correlation of the December valuation residual with subsequent monthly returns, axis ticks 0 to 0.05. The figures are not in the text.
  - The authors themselves caution: "In an efficient market, even a very good explanatory model for prices may not forecast returns."
- **Evidence quality:** strong as a cross-sectional *description* of prices. **Weak or undocumented as a return predictor**: no published long-short backtest, no OOS spread, and US stocks only.

### Country / sector applications
- **No academic test of P/B-ROE residuals for country selection was found.**
- Closest academic relatives:
  - **Desrosiers, Lemaire & L'Her (2007), "Residual Income Approach to Equity Country Selection", *FAJ* 63(2): 76–89** ([CFA Institute](https://rpc.cfainstitute.org/en/research/financial-analysts-journal/2007/residual-income-approach-to-equity-country-selection)). The residual income model is the generalisation of P/B-ROE. Implied expected returns across 19 developed country indices (1988–2005) gave significant zero-investment returns over several holding periods. The returns survived world market/size/B-M/momentum factors and transaction costs. Abstract only; figures not seen. The sample ends before the post-2005 decay.
  - **Chattopadhyay, Lyle & Wang (HBS WP 15-092, 2015; later "Expected Stock Returns Worldwide: A Log-Linear Present-Value Approach")** ([HBS DASH](https://dash.harvard.edu/bitstream/handle/1/16198221/15-092.pdf?sequence=4)). Expected return ≈ linear in B/M and ROE. It predicts OOS returns *within* 26 of 29 markets, with an average slope of 1.05. **Firm-level within country, not country allocation.** Abstract/snippet only.
- Time-variation warning: **Bianconi & Yoshino (2017)**, 6,323 commodity-sector firms in 69 countries, 1999–2010. The ROE → market-to-book coefficient is **time-varying and declining**, and turns negative for growth (90th-pct M/B) firms ([PDF](https://mbiancon.pages.tufts.edu/SEF-04-2016-0095_01.pdf)). Relevant because energy- and materials-heavy countries are where sector bias bites.
- Practitioner use: country P/B-vs-ROE scatters are common. Examples: Bridgeway on MSCI EM small cap ([2021](https://bridgeway.com/perspectives/emerging-markets-small-cap-investment-landscape-may-2021)) and MoneyWeek on Asian markets ([link](https://moneyweek.com/6261/moneyweek-asia-the-best-way-to-value-asian-markets-01105)). These are descriptive, with no backtests. GMO or Research Affiliates material using this exact construction was not found.

### Implication for the notebook
- The ROE-residual P/B is **theoretically motivated (Wilcox; residual-income) and partly validated at country level only via the RIM paper (pre-2005)**.
- Present it as a sector/profitability adjustment to P/B, not as a proven alpha source. Use ln(P/B) on ROE (Wilcox form), cross-sectional each month, with t−1 data. Consider winsorising ROE (Wilcox used −10%…+40%), since index ROE is noisy around write-downs.

---

## Gaps
- ZKR (2020) subperiod tables are unread (PDF blocked). The −0.38%/−0.47% figures come from a manuscript snippet.
- Desrosiers et al. (2007) return magnitudes are unread.
- The Wilcox & Philips (2005) published return-prediction figures are unread. Only the slide version was seen, and its chart values are not extractable.
- No source covers country reversal or P/B-ROE specifically for 2019–2026.
