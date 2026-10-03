# ghidra-manuals
A way to download Ghidra processor manuals that should be future proof. When future versions of Ghidra add support for new processors and have new processor manuals, this program will be able to add those new manuals to its config to download later.

Currently updated for **12.1** (all 43 manuals referenced by Ghidra 12.1.4 are available). A [weekly check](.github/workflows/check-manuals.yml) runs against the latest Ghidra release and opens an issue if anything breaks.

# How to Use

Using [uv](https://docs.astral.sh/uv/):

```
uvx --from git+https://github.com/meenmachine1/ghidra-manuals ghidra-manuals ~/ghidra_12.1.4_PUBLIC
```

Using pipx or pip:

```
pipx install git+https://github.com/meenmachine1/ghidra-manuals
```

Then run `ghidra-manuals ~/ghidra_12.1.4_PUBLIC`. If `$GHIDRA_INSTALL_DIR` is set, the path can be left out.

From a clone, `pip3 install -r requirements.txt` then `./get_ghidra_manuals.py ~/ghidra_12.1.4_PUBLIC`

ghidra-manuals reads the `.idx` files in your Ghidra install to find which manuals it needs, downloads each one and places it in the correct folder. Every manual is checked against the sha256 of the revision Ghidra's `.idx` was made from. Manuals are downloaded from the [ghidra-processor-manuals](https://github.com/meenmachine1/ghidra-processor-manuals/releases/tag/manuals) release first, then from the backup URLs in `config.json`. Downloads are cached in `~/.cache/ghidra-manuals` and manuals that are already installed are skipped. It exits non-zero and lists the manuals it couldn't get if any are missing.

# Usage

```
usage: ghidra-manuals [-h] [--config PATH] [--cache-dir PATH]
                      [--get-manual-idxs] [--overwrite-config] [--no-cache]
                      [~/ghidra_xx.xx]

Get ghidra manuals from the internet and put into your ghidra installation

positional arguments:
  ~/ghidra_xx.xx      Path to ghidra installation. Defaults to
                      $GHIDRA_INSTALL_DIR

options:
  -h, --help          show this help message and exit
  --config PATH       config.json to use. Defaults to the one bundled with
                      ghidra-manuals
  --cache-dir PATH    Where downloaded PDFs are cached (default:
                      ~/.cache/ghidra-manuals)
  --get-manual-idxs   Update the config to include manuals from current ghidra
                      installation
  --overwrite-config  Overwrite the config with the new manual indexes. This
                      is not typically what you want to do. Will clear current
                      URLs from the config
  --no-cache          Force download of PDFs. Do not use cached or already
                      installed PDFs.
```

# Updating config with new manuals

When a new Ghidra version references manuals that aren't in the config, run this from a clone (it edits `src/ghidra_manuals/config.json`):

```
./get_ghidra_manuals.py <path_to_new_ghidra_dir> --get-manual-idxs
```

With an installed copy, pass `--config my-config.json` to write an updated copy of the bundled config instead.

```shell
# There was a new processor manual added:
 > ./get_ghidra_manuals.py ~/ghidra_12.2_PUBLIC --get-manual-idxs
Updating manual config json with current ghidra install
Adding ./Ghidra/Processors/NEW/data/manuals/new.pdf (fill in its URLs and sha256 in .../config.json)
Updated config with 1 configs.
```

Then for each new entry:

1. Find a copy of the manual and add its URL to `urls`.
2. Install it and run `tools/verify_pages.py <ghidra_dir>` to make sure it's the revision the `.idx` was made from.
3. Run `tools/check_urls.py --pin --write` to pin its `sha256`.
4. Run `tools/publish_mirror.py --upload` to add it to the ghidra-processor-manuals release.

If you do this, please open an issue so it can be adde to the repo (if the manual/ver is not already in here).

# config.json

Each manual has:

- `path`/`filename`: where Ghidra expects the PDF.
- `sha256`: hashes of the copies known to match Ghidra's `.idx`. Any download that doesn't match one of these is rejected.
- `urls`: backup download URLs, tried in order after the release asset. `invalid_urls` are dead or serve the wrong revision.
- `page_count` (optional): for manuals where some copies have extra pages at the front (e.g. Renesas' "Old Company Name" notice). Downloads with more pages have the extras removed from the front before the hash is checked.

It also contains manuals that older Ghidra versions referenced (e.g. the 6805 processor folder from 10.1.2). They're only installed if your Ghidra's `.idx` files reference them.

# Maintenance tools

These need a clone (`pip install -e .` or just run them, they find the package in `src/`).

- `tools/check_urls.py` downloads every URL and the release asset for each manual and checks them against the pinned hashes. Dead URLs are moved to `invalid_urls`, working ones back to `urls`, and URLs serving an unknown file are reported so their revision can be checked. Writes `updated_manuals.json`, or the config in place with `--write`. Exits non-zero if anything changed.
- `tools/verify_pages.py ~/ghidra_xx.xx` checks the manuals installed in a Ghidra install match its `.idx` files, by looking for each instruction on the page the `.idx` file points at. A wrong revision shows up as a `FAIL`. It needs `pdftotext` (`apt install poppler-utils` / `brew install poppler`).
- `tools/publish_mirror.py --upload` uploads any manuals missing from (or different in) the ghidra-processor-manuals release. Needs the [GitHub CLI](https://cli.github.com/) logged in with write access to that repo.

# Known Issues

 - **HCS12** (`S12XCPUV2.pdf`): the only copies found are of the older S12CPUV2 Rev 4.0 manual, not the S12XCPUV2 (CPU12/CPU12X) manual the `.idx` was made from, so most pages are off. If anyone has `S12XCPUV2.pdf` please let me know.
 - Some upstream `.idx` files list mnemonics that aren't in their manual (e.g. microMIPS instructions in `mipsMic.idx`, AltiVec instructions in `PowerPC.idx`, ColdFire instructions in `68000.idx`). Ghidra will open those on whatever page the `.idx` says.

Please feel free to open a pull request to add more backup URLs to this project.
