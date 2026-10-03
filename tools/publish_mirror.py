#!/usr/bin/env python3

"""
Upload every manual in config.json to the ghidra-processor-manuals GitHub release.

Each manual is taken from the cache (or downloaded), checked against its pinned
sha256, and saved as "<Processor>-<filename>" (the name ghidra-manuals looks for).
With --upload, assets that are missing from the release or differ from it are
uploaded with the GitHub CLI (`gh auth login` first). The release is created if it
doesn't exist yet.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Use the checkout's package if ghidra-manuals isn't installed
sys.path.insert(1, str(Path(__file__).resolve().parent.parent / "src"))
from ghidra_manuals.cli import (BUNDLED_CONFIG, MIRROR_RELEASE_TAG, MIRROR_REPO, accepted_hashes,  # noqa: E402
                                default_cache_dir, download_manual, is_good_copy, load_config,
                                manual_key, mirror_asset_name, sha256, write_file_atomic)


def gh(*args, check=True):
    return subprocess.run(["gh", *args], check=check, capture_output=True, text=True)


def release_asset_hashes():
    """Return {asset name: sha256} for the existing release, or None if it doesn't exist."""
    result = gh("api", f"repos/{MIRROR_REPO}/releases/tags/{MIRROR_RELEASE_TAG}", check=False)
    if result.returncode != 0:
        return None
    return {asset["name"]: (asset.get("digest") or "").removeprefix("sha256:")
            for asset in json.loads(result.stdout)["assets"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=BUNDLED_CONFIG, help="config.json to use (default: bundled)")
    parser.add_argument("--cache-dir", type=Path, default=default_cache_dir(), help="ghidra-manuals cache dir")
    parser.add_argument("--out-dir", type=Path, default=Path("release_assets"), help="Where to collect the assets")
    parser.add_argument("--upload", action="store_true", help=f"Upload changed assets to {MIRROR_REPO}")
    args = parser.parse_args()

    config = load_config(args.config)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    assets, failed = {}, []
    for manual in config["manuals"]:
        key = manual_key(manual)
        if not accepted_hashes(manual):
            print(f"Skipping {key}: no sha256 pinned")
            failed.append(key)
            continue

        out_path = args.out_dir / mirror_asset_name(manual)
        cache_path = args.cache_dir / manual["path"] / manual["filename"]

        if not is_good_copy(out_path, manual):
            print(key)
            if is_good_copy(cache_path, manual):
                data = cache_path.read_bytes()
            else:
                data = download_manual(manual)
                if data is None:
                    print("  Could not get a copy matching the pinned sha256")
                    failed.append(key)
                    continue
            write_file_atomic(out_path, data)

        assets[out_path.name] = (out_path, sha256(out_path.read_bytes()))

    print(f"\nCollected {len(assets)} assets in {args.out_dir}")
    if failed:
        print("Missing:\n  " + "\n  ".join(failed))

    if not args.upload:
        return

    existing = release_asset_hashes()
    if existing is None:
        print(f"Creating release {MIRROR_RELEASE_TAG} on {MIRROR_REPO}")
        gh("release", "create", MIRROR_RELEASE_TAG, "-R", MIRROR_REPO, "--title", "Processor manuals",
           "--notes", "PDFs used by https://github.com/meenmachine1/ghidra-manuals. "
                      "Asset names are <Processor>-<filename>.")
        existing = {}

    to_upload = [path for name, (path, digest) in sorted(assets.items()) if existing.get(name) != digest]
    print(f"{len(to_upload)} asset(s) to upload ({len(assets) - len(to_upload)} already up to date)")

    for path in to_upload:
        print(f"  Uploading {path.name}")
        gh("release", "upload", MIRROR_RELEASE_TAG, str(path), "-R", MIRROR_REPO, "--clobber")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
