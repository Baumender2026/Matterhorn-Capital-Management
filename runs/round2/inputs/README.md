# Round 2 inputs

The files you fill in for Round 2. Everything else (downloads, numbers, pages) is written by the scripts.

| File | What it is |
|---|---|
| `_TEMPLATE.yaml` | The blank for one stock: peers, growth inputs, case, catalysts, issues, sources |
| `<TICKER>.yaml` | One per stock, copied from the blank |
| `portfolio.yaml` | The 20% sleeve, how it is raised (`funding`), and the six stocks in report order |

## Add a stock

From the repo root:

1. **Copy** `_TEMPLATE.yaml` to `<TICKER>.yaml` in this folder, for example `KO.yaml`.
2. **Fill it in.** The comments in the blank explain every field. Leave numbers to the script: write `{tokens}` such as `{V0}` or `{mos}` in the text instead.
3. **Build:** `python3 scripts/build_stock_report.py <TICKER> --as-of 2026-11-06`. It downloads the data and writes, in `runs/round2/2026-11-06/`, a copy of your YAML, the download (`<TICKER>_data.json`), the numbers (`<TICKER>_figures.json`) and the two pages (`<TICKER>.dc.html`, `<TICKER>.pdf`). Read the `FLAG` lines it prints.
4. **Add it to the report:** list the ticker under `stocks` in `portfolio.yaml`, then promote the pages and rebuild the report, as in `runs/round2/README.md` (*The Round 2 report*).

The page layout is `report/templates/stock-report.dc.html`. A slot of the report without a stock shows that layout with `[TO FILL]` and dashes.
