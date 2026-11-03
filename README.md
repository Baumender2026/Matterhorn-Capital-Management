# Matterhorn Capital Management

Group 3, Asset Management Challenge 2026 (USI). The repo root is also the website (GitHub Pages, `index.html`).

## Where things live

```
report/        THE report: one folder for every round, no per-round folders (see report/README.md)
  round<N>-<topic>.dc.html   report and deck sources
  figures/                   run outputs the report uses, promoted from runs/ (recorded in manifest.json)
  pdf/                       exported deliverables, linked from the website
  templates/  runtime/       blank templates and the page runtime
runs/          analysis runs, one folder per round and as-of date
  round1/inputs/  round1/2026-10-16/
  round2/inputs/  round2/<as-of>/          (see runs/round2/README.md)
scripts/       all code: update_portfolio.py (daily site data), SAA_R1.ipynb (Round 1),
               build_stock_report.py (Round 2), promote.py
data/          what the website reads: holdings.json, portfolio.json (updated daily by a GitHub Action), DGS1MO.csv
course/        course material: guidelines/, slides/, ta-code/
notes/         working notes, by round
```

## Runs and the report

- **A run is a folder `runs/round<N>/<as-of>/`**, named after the price date it uses (Round 1: `2026-10-16`; Round 2 final: `2026-11-06`). It holds a copy of the inputs it used, the data snapshot and every output. The editable inputs stay in `runs/round<N>/inputs/`. Re-running the same date overwrites that run, and git keeps the history.
- **The report never reads from `runs/`.** Copy the outputs it uses into `report/figures/` with
  `python scripts/promote.py runs/round<N>/<as-of>/<file> …`. This writes `report/figures/round<N>-<file>` and records the source run and its hash in `report/manifest.json`, so it is always clear which run produced which number.
- **Before exporting a report**, run `python scripts/promote.py --check`. It fails if a promoted file no longer matches its run, or if a file in `figures/` was never promoted.
- Code lives only in `scripts/`. Don't copy it per round.
