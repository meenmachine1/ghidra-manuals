"""
Download Ghidra processor manuals and place them into a Ghidra installation.

Which manuals a Ghidra install needs is read from the `.idx` files that ship in
`Ghidra/Processors/*/data/manuals/`. The first line of each `.idx` file names the
PDF Ghidra expects next to it, e.g.:

    @pa11_acd.pdf[PA-RISC 1.1 Architecture and Instruction Set Reference Manual, ...]

Download URLs and the sha256 of the correct revision of each manual live in config.json.
Each manual is fetched from the ghidra-processor-manuals GitHub release first, then from
the URLs in config.json.
"""

import argparse
import hashlib
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath

import requests

BUNDLED_CONFIG = Path(__file__).resolve().parent / "config.json"

IDX_GLOB = "Ghidra/Processors/*/data/manuals/*.idx"
# "@<filename>[<info>]" where the "[<info>]" part is optional (e.g. M16C_60.idx is just "@m16csm.pdf")
IDX_HEADER_RE = re.compile(r"^@\s*(?P<filename>[^\[]+?)\s*(?:\[(?P<info>.*)\])?\s*$")

MIRROR_REPO = "meenmachine1/ghidra-processor-manuals"
MIRROR_RELEASE_TAG = "manuals"
MIRROR_RELEASE_URL = f"https://github.com/{MIRROR_REPO}/releases/download/{MIRROR_RELEASE_TAG}/"

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) ghidra-manuals"
# (connect, read) timeouts in seconds. The read timeout is per chunk, not for the whole file.
TIMEOUT = (10, 60)


def bailout(msg):
    print(f"Error: {msg}")
    print("Bailing out...")
    sys.exit(1)


def default_cache_dir():
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "ghidra-manuals"


def new_config_entry(path="", filename="", info=""):
    return {
        "info": info,
        "path": path,
        "filename": filename,
        "sha256": [],
        "urls": [],
        "invalid_urls": [],
        "notes": "",
    }


def manual_key(manual):
    return manual["path"] + manual["filename"]


def mirror_asset_name(manual):
    """Release asset name for a manual, e.g. "ARM-DDI0487H_a_a-profile_architecture_reference_manual.pdf"."""
    parts = PurePosixPath(manual["path"]).parts
    processor = parts[parts.index("Processors") + 1] if "Processors" in parts[:-1] else "_".join(parts[1:])
    return f"{processor}-{manual['filename']}"


def mirror_url(manual):
    return MIRROR_RELEASE_URL + mirror_asset_name(manual)


def manual_urls(manual):
    return [mirror_url(manual)] + [url for url in manual.get("urls", []) if url != mirror_url(manual)]


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


def load_config(config_path):
    if not config_path.exists():
        bailout(f"Could not find config file {config_path}.\n"
                "Run with --get-manual-idxs to create it, then fill in the URLs.")

    with open(config_path, "r") as config_f:
        config = json.load(config_f)

    if not (isinstance(config, dict) and isinstance(config.get("manuals"), list)):
        bailout(f"{config_path} is not set up properly.")

    return config


def save_config(config, config_path):
    with open(config_path, "w") as config_f:
        json.dump(config, config_f, indent=4, ensure_ascii=False)
        config_f.write("\n")

    print(f"Manuals info dumped to {config_path}")


def is_installed_package(path):
    return any(part in ("site-packages", "dist-packages") for part in path.parts)


def update_config(ghidra_path, config_path, overwrite):
    installed = find_installed_manuals(ghidra_path)

    if overwrite:
        print(f"Overwriting {config_path}. URLs will be cleared.")
        save_config({"manuals": installed}, config_path)
        return

    if config_path.exists():
        config = load_config(config_path)
    else:
        # Start from the bundled config so the known URLs carry over
        config = load_config(BUNDLED_CONFIG)

    known = {manual_key(manual) for manual in config["manuals"]}
    missing = [manual for manual in installed if manual_key(manual) not in known]

    if not missing:
        print(f"Did not update {config_path} as there were no missing manuals...")
        if not config_path.exists():
            save_config(config, config_path)
        return

    for manual in missing:
        print(f"Adding {manual_key(manual)} (fill in its URLs and sha256 in {config_path})")
    config["manuals"].extend(missing)

    print(f"Updated config with {len(missing)} configs.")
    save_config(config, config_path)


def is_pdf(data):
    # The PDF spec allows the header to appear anywhere in the first 1024 bytes
    return data is not None and b"%PDF-" in data[:1024]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def accepted_hashes(manual):
    """sha256s of the copies of a manual known to match Ghidra's .idx. Empty if not pinned yet."""
    return set(manual.get("sha256") or [])


def fetch_pdf(url):
    """Download `url`, returning its contents if it's a PDF. Raises on network errors."""
    with requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as response:
        response.raise_for_status()
        data = response.content

    return data if is_pdf(data) else None


def trim_to_page_count(data, page_count, quiet=False):
    """
    Drop pages from the front of a PDF until it has `page_count` pages. Used when some copies
    of a manual have extra pages prepended (e.g. Renesas' "Old Company Name" notice), which
    would otherwise shift every page number in Ghidra's .idx file. Copies that already have
    the right number of pages are left alone.
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("  WARNING: pypdf is not installed so this manual can't be checked for extra leading pages.")
        return data

    reader = PdfReader(io.BytesIO(data))
    extra_pages = len(reader.pages) - page_count
    if extra_pages <= 0:
        return data

    if not quiet:
        print(f"  Removing {extra_pages} leading page(s) so page numbers match Ghidra's .idx")
    writer = PdfWriter(clone_from=reader)
    for _ in range(extra_pages):
        writer.remove_page(0)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def fetch_manual(url, manual, quiet=False):
    """
    Download one candidate copy of a manual. Returns (data, problem): data is the manual
    ready to install, or None with `problem` describing why the URL was rejected.
    Raises requests exceptions on network errors.
    """
    data = fetch_pdf(url)
    if data is None:
        return None, "is not a PDF"

    if manual.get("page_count"):
        data = trim_to_page_count(data, manual["page_count"], quiet)

    expected = accepted_hashes(manual)
    if expected and sha256(data) not in expected:
        return None, f"served an unknown file (sha256 {sha256(data)[:12]}…), probably a different revision"

    return data, None


def download_manual(manual):
    for url in manual_urls(manual):
        print(f"  Downloading {url}")
        try:
            data, problem = fetch_manual(url, manual)
        except requests.exceptions.RequestException as e:
            print(f"  WARNING: Could not download {url}: {e}")
            continue

        if data is None:
            print(f"  WARNING: {url} {problem}. Trying next URL.")
            continue

        return data

    return None


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


def is_good_copy(path, manual):
    if not path.is_file():
        return False

    data = path.read_bytes()
    expected = accepted_hashes(manual)
    return sha256(data) in expected if expected else is_pdf(data)


def get_manual(manual, ghidra_path, cache_dir, use_cache):
    """Fetch a manual (from cache or the internet) and install it. Returns True on success."""
    filename = manual["filename"]
    cache_path = cache_dir / manual["path"] / filename
    install_dir = ghidra_path / manual["path"]
    install_path = install_dir / filename

    if not install_dir.is_dir():
        print(f"  WARNING: Ghidra folder for manual `{install_dir}` doesn't exist.")
        return False

    if use_cache and accepted_hashes(manual) and is_good_copy(install_path, manual):
        print("  Already installed.")
        return True

    if use_cache and is_good_copy(cache_path, manual):
        print(f"  Found manual in cache ({cache_path}).")
        data = cache_path.read_bytes()
    else:
        data = download_manual(manual)
        if data is None:
            return False
        write_file_atomic(cache_path, data)

    write_file_atomic(install_path, data)
    return True


def install_manuals(ghidra_path, config_path, cache_dir, use_cache):
    config = load_config(config_path)
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
            print(f"  WARNING: Not in {config_path.name}. Run with --get-manual-idxs to add it, then fill in URLs.\n")
            failed.append(key)
            continue

        if get_manual(manual, ghidra_path, cache_dir, use_cache):
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


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ghidra-manuals",
                                     description="Get ghidra manuals from the internet and put into your ghidra installation")

    parser.add_argument("ghidra_path",
                        nargs="?",
                        default=os.environ.get("GHIDRA_INSTALL_DIR"),
                        help="Path to ghidra installation. Defaults to $GHIDRA_INSTALL_DIR",
                        metavar="~/ghidra_xx.xx")

    parser.add_argument("--config",
                        type=Path,
                        help="config.json to use. Defaults to the one bundled with ghidra-manuals",
                        metavar="PATH")

    parser.add_argument("--cache-dir",
                        type=Path,
                        default=default_cache_dir(),
                        help="Where downloaded PDFs are cached (default: %(default)s)",
                        metavar="PATH")

    parser.add_argument("--get-manual-idxs",
                        help="Update the config to include manuals from current ghidra installation",
                        action="store_true")

    parser.add_argument("--overwrite-config",
                        help="Overwrite the config with the new manual indexes. "
                             "This is not typically what you want to do. Will clear current URLs from the config",
                        action="store_true")

    parser.add_argument("--no-cache",
                        help="Force download of PDFs. Do not use cached or already installed PDFs.",
                        action="store_true")

    args = parser.parse_args(argv)

    if args.overwrite_config and not args.get_manual_idxs:
        bailout("--overwrite-config flag must only be used with --get-manual-idxs flag.")

    if not args.ghidra_path:
        parser.error("no Ghidra installation given and $GHIDRA_INSTALL_DIR is not set")

    ghidra_path = Path(args.ghidra_path).expanduser().resolve()
    if not (ghidra_path / "Ghidra").is_dir():
        bailout(f"Ghidra path given ({ghidra_path}) does not contain a ghidra installation.")

    config_path = (args.config or BUNDLED_CONFIG).expanduser().resolve()

    if args.get_manual_idxs:
        if args.config is None and is_installed_package(config_path):
            bailout("The bundled config is part of the installed package and shouldn't be edited.\n"
                    "Pass --config PATH to write an updated copy of it somewhere else.")

        print("Updating manual config json with current ghidra install")
        update_config(ghidra_path, config_path, args.overwrite_config)
        print(f"\nDone updating {config_path}.")
        return

    if not install_manuals(ghidra_path, config_path, args.cache_dir.expanduser(), use_cache=not args.no_cache):
        sys.exit(1)


if __name__ == "__main__":
    main()
