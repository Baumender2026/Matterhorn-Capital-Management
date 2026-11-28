"""Step B4 of the Round 3 plan: write the values-only copies of both Bloomberg workbooks.

When Excel saves a workbook, it also stores the last result of every formula. This script reads those stored
results (openpyxl, data_only=True), so it gives the same file as Ctrl+A, Copy, Paste Values on every sheet.
It never opens Excel and never recalculates, so it is safe to run on a laptop without Bloomberg.

On the terminal: refresh, wait until no cell shows "#N/A Requesting Data...", then press Ctrl+S on
r3_bloomberg.xlsx and r7_bloomberg.xlsx. Copy both files to this laptop, into their "Bloomberg template" folders,
and run from the repo root:

    python3 "Round 3 AMC/save_bloomberg_values.py"

It writes
    Quant/Strategy/Data/r3_bloomberg_values.xlsx
    Macro/Macro TA - copy/Data/r7_bloomberg_values.xlsx   (replaces the old file, which stays in git)
and stops without writing if a workbook still has "Requesting Data" cells or formulas without a stored result.
"""
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent
END_DATE = "2026-11-27"
FILES = {
    "quant": (ROOT / "Quant/Strategy/Bloomberg template/r3_bloomberg.xlsx",
              ROOT / "Quant/Strategy/Data/r3_bloomberg_values.xlsx"),
    "macro": (ROOT / "Macro/Macro TA - copy/Bloomberg template/r7_bloomberg.xlsx",
              ROOT / "Macro/Macro TA - copy/Data/r7_bloomberg_values.xlsx"),
}


def to_values(src, dst):
    formulas = openpyxl.load_workbook(src)                    # to find the formula cells
    values = openpyxl.load_workbook(src, data_only=True)      # the results Excel stored at the last save
    problems, report = [], []
    for ws in values.worksheets:
        f_ws = formulas[ws.title]
        n_na = n_requesting = n_formulas = n_empty = 0
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if isinstance(v, str) and v.startswith("#N/A"):
                    n_na += 1
                    n_requesting += "Requesting" in v
                if f_ws[c.coordinate].data_type == "f":
                    n_formulas += 1
                    n_empty += v is None           # a "" result (e.g. the template's spare rows) also reads as None
        report.append(f"   {ws.title:<11} {ws.max_row:>4} rows x {ws.max_column:>3} cols | #N/A cells: {n_na}"
                      + (f" | blank formula results: {n_empty} of {n_formulas}" if n_empty else ""))
        if n_requesting:
            problems.append(f"{ws.title}: {n_requesting} cells still say 'Requesting Data'")
        if n_formulas and n_empty == n_formulas:
            problems.append(f"{ws.title}: none of its {n_formulas} formulas has a result (file not refreshed?)")
    return values, problems, report


def settings(wb):
    return {r[0]: r[1] for r in wb["Settings"].iter_rows(min_row=2, values_only=True) if r and r[0]}


def live_prices(wb):
    return {r[0].replace(" US Equity", ""): r[2] for r in wb["Live"].iter_rows(min_row=2, values_only=True)
            if r and isinstance(r[0], str) and isinstance(r[2], (int, float))}


missing = [str(src) for src, _ in FILES.values() if not src.exists()]
if missing:
    sys.exit("Not found (copy the refreshed workbooks from the terminal first):\n  " + "\n  ".join(missing))

books, failed = {}, False
for name, (src, dst) in FILES.items():
    wb, problems, report = to_values(src, dst)
    s = settings(wb)
    end = s.get("End date")
    print(f"{name}: {src.name}  |  End date {end:%d %b %Y}" if hasattr(end, "strftime") else f"{name}: End date {end}")
    print("\n".join(report))
    if not (hasattr(end, "strftime") and f"{end:%Y-%m-%d}" == END_DATE):
        problems.append(f"Settings 'End date' is {end}, not {END_DATE}")
    if name == "quant" and s.get("Screen name") != "AMC R3 BABQM":
        problems.append(f"Settings 'Screen name' is {s.get('Screen name')!r}, not 'AMC R3 BABQM'")
    if problems:
        failed = True
        print("   NOT SAVED:\n   - " + "\n   - ".join(problems))
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        wb.save(dst)
        print(f"   saved -> {dst.relative_to(ROOT)}")
    books[name] = wb
    print()

# the same ticker must have the same last price in both files (B3: both refreshed in the same session)
q, m = live_prices(books["quant"]), live_prices(books["macro"])
common = sorted(set(q) & set(m))
diff = {t: (q[t], m[t]) for t in common if abs(q[t] - m[t]) > 1e-6}
print(f"Live prices in both files: {', '.join(common) or 'none'} | "
      + (f"⚠️ DIFFERENT (refresh both in the same session): {diff}" if diff else "all equal"))
sys.exit(1 if failed else 0)
