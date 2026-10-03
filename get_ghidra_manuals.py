#!/usr/bin/env python3

"""
Download Ghidra processor manuals and place them into a Ghidra installation.

Which manuals a Ghidra install needs is read from the `.idx` files that ship in
`Ghidra/Processors/*/data/manuals/`. The first line of each `.idx` file names the
PDF Ghidra expects next to it, e.g.:

    @pa11_acd.pdf[PA-RISC 1.1 Architecture and Instruction Set Reference Manual, ...]

Download URLs for each manual live in config.json.
"""

import argparse
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import requests

REPO_DIR = Path(__file__).resolve().parent
CONFIG_FILE = REPO_DIR / "config.json"
CACHE_DIR = REPO_DIR / "pdfs"

IDX_GLOB = "Ghidra/Processors/*/data/manuals/*.idx"
# "@<filename>[<info>]" where the "[<info>]" part is optional (e.g. M16C_60.idx is just "@m16csm.pdf")
IDX_HEADER_RE = re.compile(r"^@\s*(?P<filename>[^\[]+?)\s*(?:\[(?P<info>.*)\])?\s*$")

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) ghidra-manuals"
# (connect, read) timeouts in seconds. The read timeout is per chunk, not for the whole file.
TIMEOUT = (10, 60)


def bailout(msg):
    print(f"Error: {msg}")
    print("Bailing out...")
    sys.exit(1)


def new_config_entry(path="", filename="", info=""):
    return {
        "info": info,
        "path": path,
        "filename": filename,
        "urls": [],
        "invalid_urls": [],
        "notes": "",
    }


def manual_key(manual):
    return manual["path"] + manual["filename"]


def read_idx_header(idx_path):
    with open(idx_path, "rb") as idx_f:
        first_line = idx_f.readline().strip()

    # Ghidra's idx files are a mix of UTF-8 and Windows-1252
    try:
        return first_line.decode("utf-8")
    except UnicodeDecodeError:
        return first_line.decode("cp1252", errors="replace")


def find_installed_manuals(ghidra_path):
    """Return a config entry for every manual referenced by the Ghidra installation's .idx files."""
    manuals = {}

    for idx_path in sorted(ghidra_path.glob(IDX_GLOB)):
        header = read_idx_header(idx_path)
        match = IDX_HEADER_RE.match(header)
        if match is None:
            print(f"WARNING: Unable to parse manual name from {idx_path}: {header!r}. Skipping...")
            continue

        path = f"./{idx_path.parent.relative_to(ghidra_path).as_posix()}/"
        manual = new_config_entry(path, match["filename"], (match["info"] or "").strip())

        # Several .idx files can reference the same PDF (e.g. MIPS mipsMic.idx and mipsM16.idx)
        manuals.setdefault(manual_key(manual), manual)

    return list(manuals.values())


def load_config():
    if not CONFIG_FILE.exists():
        bailout(f"Could not find config file {CONFIG_FILE}.\n"
                "Run with --get-manual-idxs to create it, then fill in the URLs.")

    with open(CONFIG_FILE, "r") as config_f:
        config = json.load(config_f)

    if not (isinstance(config, dict) and isinstance(config.get("manuals"), list)):
        bailout(f"{CONFIG_FILE} is not set up properly.")

    return config


def save_config(config):
    with open(CONFIG_FILE, "w") as config_f:
        json.dump(config, config_f, indent=4, ensure_ascii=False)
        config_f.write("\n")

    print(f"Manuals info dumped to {CONFIG_FILE}")


def update_config(ghidra_path, overwrite):
    installed = find_installed_manuals(ghidra_path)

    if overwrite:
        print(f"Overwriting current {CONFIG_FILE}. URLs will be cleared.")
        save_config({"manuals": installed})
        return

    config = load_config() if CONFIG_FILE.exists() else {"manuals": []}
    known = {manual_key(manual) for manual in config["manuals"]}
    missing = [manual for manual in installed if manual_key(manual) not in known]

    if not missing:
        print(f"Did not update {CONFIG_FILE} as there were no missing manuals...")
        return

    for manual in missing:
        print(f"Adding {manual_key(manual)} (fill in its URLs in {CONFIG_FILE})")
    config["manuals"].extend(missing)

    print(f"Updated config with {len(missing)} configs.")
    save_config(config)


def is_pdf(data):
    # The PDF spec allows the header to appear anywhere in the first 1024 bytes
    return data is not None and b"%PDF-" in data[:1024]


def fetch_pdf(url):
    """Download `url`, returning its contents if it's a PDF. Raises on network errors."""
    with requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as response:
        response.raise_for_status()
        data = response.content

    return data if is_pdf(data) else None


def download_pdf(urls):
    for url in urls:
        print(f"  Downloading {url}")
        try:
            data = fetch_pdf(url)
        except requests.exceptions.RequestException as e:
            print(f"  WARNING: Could not download {url}: {e}")
            continue

        if data is None:
            print(f"  WARNING: {url} is not a PDF. Trying next URL.")
            continue

        return data

    return None


def trim_to_page_count(data, page_count):
    """
    Drop pages from the front of a PDF until it has `page_count` pages. Used when some copies
    of a manual have extra pages prepended (e.g. Renesas' "Old Company Name" notice), which
    would otherwise shift every page number in Ghidra's .idx file. Copies that already have
    the right number of pages are left alone.
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("  WARNING: pypdf is not installed so this manual can't be checked for extra leading pages. "
              "Ghidra may open it on the wrong page. Run `pip3 install -r requirements.txt`.")
        return data

    reader = PdfReader(io.BytesIO(data))
    extra_pages = len(reader.pages) - page_count
    if extra_pages <= 0:
        return data

    print(f"  Removing {extra_pages} leading page(s) so page numbers match Ghidra's .idx")
    writer = PdfWriter(clone_from=reader)
    for _ in range(extra_pages):
        writer.remove_page(0)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def write_file_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as tmp_f:
            tmp_f.write(data)
        os.chmod(tmp_path, 0o644)
        os.replace(tmp_path, path)
    except BaseException:
        os.unlink(tmp_path)
        raise


def read_cached_pdf(cache_path):
    if not cache_path.is_file():
        return None

    data = cache_path.read_bytes()
    return data if is_pdf(data) else None


def get_manual(manual, ghidra_path, use_cache):
    """Fetch a manual (from cache or the internet) and install it. Returns True on success."""
    filename = manual["filename"]
    cache_path = CACHE_DIR / manual["path"] / filename
    install_dir = ghidra_path / manual["path"]

    if not install_dir.is_dir():
        print(f"  WARNING: Ghidra folder for manual `{install_dir}` doesn't exist.")
        return False

    data = read_cached_pdf(cache_path) if use_cache else None

    if data is not None:
        print(f"  Found manual in cache. Delete {cache_path} if you'd like to redownload.")
    else:
        if not manual.get("urls"):
            print(f"  WARNING: {filename} does not have any URLs in {CONFIG_FILE.name}.")
            return False

        data = download_pdf(manual["urls"])
        if data is None:
            return False

        if manual.get("page_count"):
            data = trim_to_page_count(data, manual["page_count"])

        write_file_atomic(cache_path, data)

    write_file_atomic(install_dir / filename, data)
    return True


def install_manuals(ghidra_path, use_cache):
    config = load_config()
    config_manuals = {manual_key(manual): manual for manual in config["manuals"]}
    installed = find_installed_manuals(ghidra_path)

    if not installed:
        bailout(f"No processor manual .idx files found in {ghidra_path}.")

    print(f"Getting {len(installed)} manuals...\n")

    failed = []
    for idx_manual in installed:
        key = manual_key(idx_manual)
        print(f"{key}")

        manual = config_manuals.get(key)
        if manual is None:
            print(f"  WARNING: Not in {CONFIG_FILE.name}. Run with --get-manual-idxs to add it, then fill in URLs.\n")
            failed.append(key)
            continue

        if get_manual(manual, ghidra_path, use_cache):
            print(f"  Successfully got manual: {manual['filename']}.\n")
        else:
            print(f"  WARNING: Could not get manual: {manual['filename']}.\n")
            failed.append(key)

    print(f"Installed {len(installed) - len(failed)}/{len(installed)} manuals into {ghidra_path}.")
    if failed:
        print("Missing manuals:")
        for key in failed:
            print(f"  {key}")

    return not failed


def main():
    parser = argparse.ArgumentParser(description="Get ghidra manuals from the internet and put into your ghidra installation")

    parser.add_argument("ghidra_path",
                        help="Path to ghidra installation",
                        metavar="~/ghidra_xx.xx")

    parser.add_argument("--get-manual-idxs",
                        help=f"Update {CONFIG_FILE.name} to include manuals from current ghidra installation",
                        action="store_true")

    parser.add_argument("--overwrite-config",
                        help=f"Overwrite {CONFIG_FILE.name} with the new manual indexes. "
                             f"This is not typically what you want to do. Will clear current URLs from {CONFIG_FILE.name}",
                        action="store_true")

    parser.add_argument("--no-cache",
                        help="Force download of PDFs. Do not use cached PDFs.",
                        action="store_true")

    args = parser.parse_args()

    if args.overwrite_config and not args.get_manual_idxs:
        bailout("--overwrite-config flag must only be used with --get-manual-idxs flag.")

    ghidra_path = Path(args.ghidra_path).expanduser().resolve()
    if not (ghidra_path / "Ghidra").is_dir():
        bailout(f"Ghidra path given ({ghidra_path}) does not contain a ghidra installation.")

    if args.get_manual_idxs:
        print("Updating manual config json with current ghidra install")
        update_config(ghidra_path, args.overwrite_config)
        print(f"\nDone updating {CONFIG_FILE.name}.")
        return

    if not install_manuals(ghidra_path, use_cache=not args.no_cache):
        sys.exit(1)


if __name__ == "__main__":
    main()
