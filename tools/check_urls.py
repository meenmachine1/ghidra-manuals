#!/usr/bin/env python3

"""
Validate the download URLs for each manual in config.json.

Every URL in `urls` and `invalid_urls` is downloaded, along with the manual's
ghidra-processor-manuals release asset. A URL is valid if it serves a copy of the
manual whose sha256 is in the manual's `sha256` list.

- Valid URLs in `invalid_urls` are moved back into `urls`, and invalid URLs in
  `urls` are moved into `invalid_urls`.
- URLs that serve a PDF with an unknown hash are reported. That's usually a different
  revision whose page numbers don't match Ghidra's .idx, so check it with
  verify_pages.py before adding its hash to `sha256`.
- With --pin, manuals that have no `sha256` yet are pinned to the file served by their
  first working URL (check that copy with verify_pages.py first).

The result is written to updated_manuals.json, or back into the config with --write.

Exits non-zero if a release asset is missing or wrong, a manual isn't pinned, or a
manual has no working URL at all. Backup URLs changing state are only warnings, since
some hosts block datacenter IPs (e.g. CI runners); pass --strict to fail on those too.
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

# Use the checkout's package if ghidra-manuals isn't installed
sys.path.insert(1, str(Path(__file__).resolve().parent.parent / "src"))
from ghidra_manuals.cli import (BUNDLED_CONFIG, accepted_hashes, fetch_manual, load_config,  # noqa: E402
                                manual_key, mirror_url, save_config, sha256)

OUTPUT_FILE = Path("updated_manuals.json")
RETRIES = 2
IN_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"


def report(level, msg):
    """Print a problem, as a GitHub Actions annotation when running in CI."""
    print(f"::{level}::{msg}" if IN_GITHUB_ACTIONS else msg)


def check_url(manual, url):
    """Return the sha256 of the copy of `manual` served by `url`, or None if it's unreachable or not a PDF."""
    unpinned = dict(manual, sha256=[])

    for attempt in range(RETRIES + 1):
        try:
            data, problem = fetch_manual(url, unpinned, quiet=True)
            break
        except requests.RequestException as e:
            # Some hosts (e.g. web.archive.org) rate limit, so back off and retry
            if attempt == RETRIES:
                print(f"INVALID {url} ({e})")
                return None
            time.sleep(5 * (attempt + 1))

    if data is None:
        print(f"INVALID {url} ({problem})")
        return None

    print(f"ok      {url}")
    return sha256(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=BUNDLED_CONFIG, help="config.json to check (default: bundled)")
    parser.add_argument("--write", action="store_true", help="Update the config in place")
    parser.add_argument("--pin", action="store_true", help="Pin manuals with no sha256 to their first working URL")
    parser.add_argument("--strict", action="store_true", help="Also exit non-zero if any backup URL changed state")
    parser.add_argument("-j", "--jobs", type=int, default=4, help="Number of parallel downloads")
    args = parser.parse_args()

    config = load_config(args.config)
    manuals = config["manuals"]

    jobs = [(i, url) for i, manual in enumerate(manuals)
            for url in [mirror_url(manual)] + manual.get("urls", []) + manual.get("invalid_urls", [])]

    with ThreadPoolExecutor(args.jobs) as pool:
        results = list(pool.map(lambda job: check_url(manuals[job[0]], job[1]), jobs))

    hashes = {}
    for (i, url), digest in zip(jobs, results):
        hashes[i, url] = digest

    print()
    problems, warnings = 0, 0
    for i, manual in enumerate(manuals):
        key = manual_key(manual)
        urls = manual.get("urls", [])
        invalid_urls = manual.get("invalid_urls", [])
        all_urls = list(dict.fromkeys(urls + invalid_urls))

        if not accepted_hashes(manual):
            first_working = next((url for url in [mirror_url(manual)] + all_urls if hashes[i, url]), None)
            if args.pin and first_working:
                manual["sha256"] = [hashes[i, first_working]]
                print(f"Pinned {key} to {first_working}")
            else:
                report("error", f"Not pinned (no sha256): {key}")
                problems += 1

        expected = accepted_hashes(manual)
        is_valid = {url: hashes[i, url] is not None and (not expected or hashes[i, url] in expected)
                    for url in all_urls}

        for url in all_urls:
            if hashes[i, url] and not is_valid[url]:
                print(f"Serves an unknown file, check its revision: {key}\n  {url} (sha256 {hashes[i, url]})")

        new_urls = [url for url in all_urls if is_valid[url]]
        new_invalid = [url for url in all_urls if not is_valid[url]]
        if new_urls != urls or new_invalid != invalid_urls:
            dead = [url for url in urls if not is_valid[url]]
            revived = [url for url in invalid_urls if is_valid[url]]
            report("warning", f"Backup URLs changed for {key}: "
                              f"{len(dead)} stopped working, {len(revived)} working again "
                              f"(may just be blocked from this IP)")
            warnings += 1
        manual["urls"], manual["invalid_urls"] = new_urls, new_invalid

        mirror_ok = hashes[i, mirror_url(manual)] is not None and \
            (not expected or hashes[i, mirror_url(manual)] in expected)
        if not mirror_ok:
            report("error", f"Release asset missing or wrong: {key} ({mirror_url(manual)})")
            problems += 1

        if not new_urls and not mirror_ok:
            report("error", f"No working URLs: {key}")

    if args.write:
        save_config(config, args.config)
    else:
        with open(OUTPUT_FILE, "w") as out_f:
            json.dump(config, out_f, indent=4, ensure_ascii=False)
            out_f.write("\n")
        print(f"\nSaved to '{OUTPUT_FILE}'.")

    print(f"{problems} problem(s), {warnings} backup URL warning(s).")
    sys.exit(1 if problems or (args.strict and warnings) else 0)


if __name__ == "__main__":
    main()
