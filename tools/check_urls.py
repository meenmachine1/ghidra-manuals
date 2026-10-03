#!/usr/bin/env python3

"""
Validate every URL (both `urls` and `invalid_urls`) for each manual in config.json.

URLs in `urls` that no longer serve a PDF are moved into `invalid_urls`. URLs in
`invalid_urls` are only moved back into `urls` if they serve the exact same file as one
of the manual's valid URLs, since a different file is often a different revision whose
page numbers don't match Ghidra's .idx (check those with verify_pages.py and move them
by hand).

The result is written to updated_manuals.json, or back into config.json with --write.
"""

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from get_ghidra_manuals import CONFIG_FILE, fetch_pdf, load_config, manual_key, save_config  # noqa: E402

OUTPUT_FILE = Path("updated_manuals.json")
RETRIES = 2


def check_url(url):
    """Return the md5 of the PDF at `url`, or None if it isn't reachable or isn't a PDF."""
    for attempt in range(RETRIES + 1):
        try:
            data = fetch_pdf(url)
            break
        except requests.RequestException as e:
            # Some hosts (e.g. web.archive.org) rate limit, so back off and retry
            if attempt == RETRIES:
                print(f"INVALID {url} ({e})")
                return None
            time.sleep(5 * (attempt + 1))

    if data is None:
        print(f"INVALID {url} (not a PDF)")
        return None

    print(f"ok      {url}")
    return hashlib.md5(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help=f"Update {CONFIG_FILE.name} in place")
    parser.add_argument("-j", "--jobs", type=int, default=4, help="Number of parallel downloads")
    args = parser.parse_args()

    config = load_config()
    all_urls = {url for manual in config["manuals"]
                for url in manual.get("urls", []) + manual.get("invalid_urls", [])}

    with ThreadPoolExecutor(args.jobs) as pool:
        hashes = dict(zip(all_urls, pool.map(check_url, all_urls)))

    print()
    for manual in config["manuals"]:
        key = manual_key(manual)
        urls = manual.get("urls", [])
        invalid_urls = manual.get("invalid_urls", [])

        valid = [url for url in urls if hashes[url]]
        valid_hashes = {hashes[url] for url in valid}

        promoted = [url for url in invalid_urls if hashes[url] in valid_hashes]
        for url in invalid_urls:
            if hashes[url] and url not in promoted:
                print(f"Serves a different PDF than the valid URLs, check its revision: {key}\n  {url}")

        manual["urls"] = valid + promoted
        manual["invalid_urls"] = [url for url in urls if not hashes[url]] + \
                                 [url for url in invalid_urls if url not in promoted]

        if not manual["urls"]:
            print(f"No valid URLs: {key}")

        # Different files may be different revisions, so the .idx page numbers might not line up for all of them
        if len(valid_hashes) > 1:
            print(f"Valid URLs serve different files: {key}")

    if args.write:
        save_config(config)
    else:
        with open(OUTPUT_FILE, "w") as out_f:
            json.dump(config, out_f, indent=4, ensure_ascii=False)
            out_f.write("\n")
        print(f"\nURLs have been validated. Saved to '{OUTPUT_FILE}'.")


if __name__ == "__main__":
    main()
