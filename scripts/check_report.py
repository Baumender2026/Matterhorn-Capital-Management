"""Check that no page of a report (report/*.dc.html) runs past the bottom, and optionally print its PDF.

Pages are fixed A4 sheets that clip what does not fit, so an overflow is silent in the PDF. The report's last
<script> writes each page's layout into <html data-overflow="…"> after the fonts load; headless Chrome reads it
with --dump-dom. Same mechanism as scripts/build_round2_report.py (export), for any round.

    python3 scripts/check_report.py report/round3-strategies.dc.html
    python3 scripts/check_report.py report/round3-strategies.dc.html --pdf report/pdf/Matterhorn_Round3_Strategies.pdf

Needs Google Chrome and an internet connection (the runtime loads React from unpkg and the fonts from Google).
Exit code: 0 = every page fits, 1 = a page overflows, 2 = the layout could not be measured.
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


def chrome():
    for c in (os.environ.get("CHROME"), r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chrome")):
        if c and Path(c).exists():
            return c
    sys.exit("Google Chrome not found: set CHROME to its path")


def main():
    ap = argparse.ArgumentParser(description="Check a report for page overflow and optionally print it to PDF.")
    ap.add_argument("report", type=Path, help="the .dc.html file")
    ap.add_argument("--pdf", type=Path, help="also print the PDF to this path")
    args = ap.parse_args()
    uri = args.report.resolve().as_uri()               # percent-encodes the spaces in the repo path
    exe = chrome()

    dom = subprocess.run([exe, *FLAGS, "--dump-dom", uri], capture_output=True, text=True, encoding="utf-8",
                         timeout=180).stdout
    found = re.search(r'data-overflow="([^"]*)"', dom)
    if args.pdf:
        args.pdf.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([exe, *FLAGS, f"--print-to-pdf={args.pdf.resolve()}", uri], capture_output=True, timeout=180)
        print(f"PDF: {args.pdf}" if args.pdf.exists() else "PDF: export failed")
    if not found:
        print("Could not measure the layout: the page did not finish rendering. Check the internet connection "
              "(React from unpkg, fonts from Google) and that the report ends with the overflow <script>.")
        sys.exit(2)

    layout = json.loads(html.unescape(found.group(1)))
    for p in layout:
        print(f"  {p['label']}: free {p['free']}px" + (f", OVERFLOW {p['overflow']}px" if p["overflow"] else ""))
    clipped = [p for p in layout if p["overflow"] > 0]
    if clipped:
        print("Too long: " + "; ".join(f"{p['label']} runs {p['overflow']}px past the bottom" for p in clipped))
        sys.exit(1)
    print(f"OK: {len(layout)} pages, none overflows")


if __name__ == "__main__":
    main()
