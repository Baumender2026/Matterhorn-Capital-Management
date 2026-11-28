"""Check that no page of a report (report/*.dc.html) runs past the bottom, and optionally print its PDF.

Pages are fixed A4 sheets that clip what does not fit, so an overflow is silent in the PDF. The report's last
<script> writes each page's layout into <html data-overflow="…"> after the fonts load; headless Chrome reads it
with --dump-dom. Same mechanism as scripts/build_round2_report.py (export), for any round.

    python3 scripts/check_report.py report/round3-strategies.dc.html
    python3 scripts/check_report.py report/round3-strategies.dc.html --pdf report/pdf/Matterhorn_Round3_Strategies.pdf

The PDF is written only when every page fits; a file already at that path is deleted first, so an old PDF is never
mistaken for a new one. Needs Google Chrome and an internet connection (React from unpkg, the fonts from Google).
Exit code: 0 = every page fits (and the PDF is written, if asked); 1 = a page overflows (no PDF);
2 = no check possible (Chrome missing or too slow, layout not measured, PDF export failed).
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FLAGS = ["--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=30000"]
TIMEOUT = 180


def stop(message, code):
    print(message)
    sys.exit(code)


def chrome():
    for c in (os.environ.get("CHROME"), r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chrome")):
        if c and Path(c).exists():
            return c
    stop("Google Chrome not found: set CHROME to its path", 2)


def run(exe, extra, **kw):
    try:
        return subprocess.run([exe, *FLAGS, *extra], capture_output=True, timeout=TIMEOUT, **kw)
    except subprocess.TimeoutExpired:
        stop(f"Chrome did not finish within {TIMEOUT} s: no check, no PDF.", 2)


def main():
    ap = argparse.ArgumentParser(description="Check a report for page overflow and optionally print it to PDF.")
    ap.add_argument("report", type=Path, help="the .dc.html file")
    ap.add_argument("--pdf", type=Path, help="also print the PDF to this path (only if every page fits)")
    args = ap.parse_args()
    uri = args.report.resolve().as_uri()               # percent-encodes the spaces in the repo path
    exe = chrome()
    if args.pdf and args.pdf.exists():
        args.pdf.unlink()                              # never leave an old PDF that looks like the new one

    dom = run(exe, ["--dump-dom", uri], text=True, encoding="utf-8").stdout or ""
    found = re.search(r'data-overflow="([^"]*)"', dom)
    if not found:
        stop("Could not measure the layout: the page did not finish rendering. Check the internet connection "
             "(React from unpkg, fonts from Google) and that the report ends with the overflow <script>. No PDF written.", 2)

    layout = json.loads(html.unescape(found.group(1)))
    for p in layout:
        free = f"free {p['free']}px" if p.get("free") is not None else "free —"
        print(f"  {p['label']}: {free}" + (f", OVERFLOW {p['overflow']}px" if p["overflow"] else ""))
    clipped = [p for p in layout if p["overflow"] > 0]
    if clipped:
        stop("Too long: " + "; ".join(f"{p['label']} runs {p['overflow']}px past the bottom" for p in clipped)
             + ". No PDF written: shorten these pages first.", 1)
    print(f"OK: {len(layout)} pages, none overflows")

    if args.pdf:
        args.pdf.parent.mkdir(parents=True, exist_ok=True)
        r = run(exe, [f"--print-to-pdf={args.pdf.resolve()}", uri])
        if r.returncode != 0 or not args.pdf.exists():
            stop("PDF export failed: no PDF written.", 2)
        print(f"PDF: {args.pdf}")


if __name__ == "__main__":
    main()
