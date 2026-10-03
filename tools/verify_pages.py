#!/usr/bin/env python3

"""
Check that the manuals installed in a Ghidra installation match its .idx files.

Each .idx line after the header is "<mnemonic>, <page>". For every line this checks
the mnemonic appears in the text of that PDF page, or within the next few pages since
some .idx files point at the start of the section an instruction is documented in.
A wrong revision of a manual (or extra pages at the front) shows up as a low match rate.

Some upstream .idx files list mnemonics that never appear literally in the manual
(e.g. AVR32's "ADD{EQ}" condition-code expansions, or microMIPS instructions indexed
against the MIPS64 manual). Those are reported but don't count against the match rate.

Scanned manuals have no text layer, so they are reported as "no text" rather than failing.

Requires poppler's pdftotext (`apt install poppler-utils` / `brew install poppler`).
"""

import argparse
import re
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from get_ghidra_manuals import IDX_GLOB, IDX_HEADER_RE, read_idx_header  # noqa: E402

LOOKAHEAD_PAGES = 3


def read_idx_entries(idx_path):
    entries = []
    with open(idx_path, "rb") as idx_f:
        idx_f.readline()  # header
        for line in idx_f:
            mnemonic, _, page = line.decode("utf-8", errors="replace").strip().rpartition(",")
            if mnemonic and page.strip().isdigit():
                entries.append((mnemonic.strip(), int(page)))
    return entries


def squash(text):
    # Ignore whitespace and case since PDF text extraction tends to mangle both
    return re.sub(r"\s+", "", text).lower()


@lru_cache(maxsize=4)
def pdf_pages(pdf_path):
    """Return the squashed text of each page of the PDF (index 0 is page 1)."""
    text = subprocess.run(["pdftotext", "-q", str(pdf_path), "-"],
                          capture_output=True, text=True, errors="replace").stdout
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()  # pdftotext ends every page with a form feed
    return [squash(page) for page in pages]


def verify_idx(idx_path, min_match):
    """Returns (status, detail)."""
    match = IDX_HEADER_RE.match(read_idx_header(idx_path))
    if match is None:
        return "ERROR", "unparseable header"

    pdf_path = idx_path.parent / match["filename"]
    if not pdf_path.is_file():
        return "MISSING", pdf_path.name

    entries = read_idx_entries(idx_path)
    if not entries:
        return "OK", "no page entries"

    pages = pdf_pages(pdf_path)
    if not any(pages):
        return "NO TEXT", "can't check (scanned PDF?)"

    whole_pdf = "".join(pages)
    exact, near, misses, absent = 0, 0, [], 0
    for mnemonic, page in entries:
        found = [squash(mnemonic) in text for text in pages[page - 1:page + LOOKAHEAD_PAGES]]
        if found[:1] == [True]:
            exact += 1
        elif any(found):
            near += 1
        elif squash(mnemonic) not in whole_pdf:
            absent += 1
        else:
            misses.append(f"{mnemonic}@{page}")

    checkable = len(entries) - absent
    detail = f"{exact}/{checkable} on page, {near} within {LOOKAHEAD_PAGES} pages after"
    if misses:
        detail += f", {len(misses)} on other pages (e.g. {', '.join(misses[:4])})"
    if absent:
        detail += f", {absent} not in PDF"
    if max(page for _, page in entries) > len(pages):
        detail += f", idx references pages past the end of the PDF ({len(pages)} pages)"

    ok = checkable > 0 and (exact + near) / checkable >= min_match
    return ("OK" if ok else "FAIL"), detail


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ghidra_path", help="Path to ghidra installation", metavar="~/ghidra_xx.xx")
    parser.add_argument("--min-match", type=float, default=0.9,
                        help="Fraction of idx entries (that appear somewhere in the PDF) that must be on the right page (default 0.9)")
    args = parser.parse_args()

    if not shutil.which("pdftotext"):
        sys.exit("pdftotext is required (install poppler-utils)")

    ghidra_path = Path(args.ghidra_path).expanduser().resolve()
    idx_paths = sorted(ghidra_path.glob(IDX_GLOB))
    if not idx_paths:
        sys.exit(f"No processor manual .idx files found in {ghidra_path}")

    bad = 0
    for idx_path in idx_paths:
        status, detail = verify_idx(idx_path, args.min_match)
        bad += status in ("ERROR", "MISSING", "FAIL")
        print(f"{status:8} {idx_path.relative_to(ghidra_path)}: {detail}", flush=True)

    print(f"\n{len(idx_paths) - bad}/{len(idx_paths)} idx files OK or uncheckable.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
