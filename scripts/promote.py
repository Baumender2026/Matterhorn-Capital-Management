#!/usr/bin/env python3
"""Promote run outputs into report/, and record which run each one came from.

    python scripts/promote.py runs/round2/2026-11-06/<TICKER>.dc.html runs/round2/2026-11-06/portfolio.json
    python scripts/promote.py --check      every promoted file still matches the run it came from

runs/round<N>/<run>/<name> is copied to report/figures/round<N>-<name> and recorded in
report/manifest.json (source, run, sha256, date). The report uses only these copies, never runs/.
Promoting the same name again, for example from a later run, replaces the copy and its record.
A page (.html) gets its runtime path rewritten so that the copy renders from report/figures/.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REPORT = REPO / "report"
FIGURES = REPORT / "figures"
MANIFEST = REPORT / "manifest.json"
RUN_FILE = re.compile(r"^runs/(round\d+)/([^/]+)/([^/]+)$")      # runs/round2/2026-11-06/portfolio.json
TEXT = {".json", ".html", ".csv", ".yaml", ".md", ".txt"}
RUNTIME = (b'"../../../report/runtime/', b'"../runtime/')        # from runs/round<N>/<run>/ to report/figures/
ABOUT = ("Files in report/figures/ and the run each one was promoted from. "
         "Written by scripts/promote.py; check with: python scripts/promote.py --check")


def content(path):
    """Bytes, with text line endings normalised: git may check text out with CRLF on Windows."""
    data = path.read_bytes()
    return data.replace(b"\r\n", b"\n") if path.suffix in TEXT else data


def as_promoted(src):
    data = content(src)
    return data.replace(*RUNTIME) if src.suffix == ".html" else data


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load():
    if not MANIFEST.exists():
        return {}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]


def save(files):
    doc = {"about": ABOUT, "files": dict(sorted(files.items()))}
    MANIFEST.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")


def promote(paths):
    files = load()
    for arg in paths:
        src = Path(arg).resolve()
        try:
            rel = src.relative_to(REPO).as_posix()
        except ValueError:
            sys.exit(f"{arg}: not inside the repo")
        hit = RUN_FILE.match(rel)
        if not hit or hit.group(2) == "inputs":
            sys.exit(f"{rel}: promote an output of a run, runs/round<N>/<run>/<file>")
        if not src.is_file():
            sys.exit(f"{rel}: no such file")
        rnd, run, name = hit.groups()
        dest = FIGURES / f"{rnd}-{name}"
        FIGURES.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(as_promoted(src))
        key = dest.relative_to(REPORT).as_posix()
        files[key] = {"source": rel, "run": f"{rnd}/{run}", "sha256": sha256(content(src)),
                      "promoted": date.today().isoformat()}
        print(f"{rel}  ->  report/{key}")
    save(files)


def check():
    files, bad = load(), 0
    for key, e in sorted(files.items()):
        src, dest = REPO / e["source"], REPORT / key
        if not src.is_file():
            problem = "its source in runs/ is missing"
        elif sha256(content(src)) != e["sha256"]:
            problem = "the run file changed after promotion: promote it again"
        elif not dest.is_file():
            problem = "the copy in report/ is missing"
        elif content(dest) != as_promoted(src):
            problem = "the copy in report/ was edited: change the run, not the copy"
        else:
            problem = None
        bad += problem is not None
        print(f"{'ok  ' if problem is None else 'FAIL'} report/{key}  <-  {e['source']}" + (f"  ({problem})" if problem else ""))
    for f in sorted(FIGURES.glob("*")) if FIGURES.exists() else []:
        key = f.relative_to(REPORT).as_posix()
        if key not in files:
            bad += 1
            print(f"FAIL report/{key}  (not in the manifest: promote it from its run)")
    print("All promoted files match their runs." if not bad else f"{bad} problem(s).")
    return bad == 0


def main():
    ap = argparse.ArgumentParser(description="Copy run outputs into report/figures/ and record where they came from.")
    ap.add_argument("files", nargs="*", help="Run outputs, runs/round<N>/<run>/<file>")
    ap.add_argument("--check", action="store_true", help="Check every promoted file against its run")
    args = ap.parse_args()
    if args.check:
        sys.exit(0 if check() else 1)
    if not args.files:
        ap.error("give run files to promote, or --check")
    promote(args.files)


if __name__ == "__main__":
    main()
