# ghidra-manuals
A way to download Ghidra processor manuals that should be future proof. When future versions of Ghidra add support for new processors and have new processor manuals, this program will be able to add those new manuals to its config to download later.

Currently updated for **12.1** (all 43 manuals referenced by Ghidra 12.1.4 are available). A [weekly check](.github/workflows/check-manuals.yml) runs against the latest Ghidra release and opens an issue if anything breaks.

# How to Install

Requires Python 3.9+. Pick one:

**[uv](https://docs.astral.sh/uv/)** (runs it without a separate install step). Use this in place of `ghidra-manuals` in the commands below:

```
uvx --from git+https://github.com/meenmachine1/ghidra-manuals ghidra-manuals
```

**pipx** (installs a `ghidra-manuals` command):

```
pipx install git+https://github.com/meenmachine1/ghidra-manuals
pipx upgrade ghidra-manuals   # later, to pick up new manuals and fixed URLs
```

**pip** (into an existing virtualenv):

```
pip install git+https://github.com/meenmachine1/ghidra-manuals
```

**From a clone** (no install, use `./get_ghidra_manuals.py` in place of `ghidra-manuals`):

```
git clone https://github.com/meenmachine1/ghidra-manuals
cd ghidra-manuals
pip3 install -r requirements.txt
```

# How to Use

## Install the manuals into Ghidra

Point it at the folder you unzipped Ghidra into (the one containing `ghidraRun`):

```
ghidra-manuals ~/ghidra_12.1.4_PUBLIC
```

It reads the `.idx` files in that install to work out which manuals it needs, downloads each one and puts it where Ghidra looks for it (e.g. `Ghidra/Processors/x86/data/manuals/`). The manuals for Ghidra 12.1 are about 330MB in total. The output ends with a summary:

```
Installed 43/43 manuals into /home/you/ghidra_12.1.4_PUBLIC.
```

If any manual couldn't be downloaded it's listed under `Missing manuals:` and the command exits non-zero. Running it again is safe: manuals that are already installed are skipped, so it only downloads what's missing.

If you set `GHIDRA_INSTALL_DIR` (e.g. in your shell profile), the path can be left out:

```
export GHIDRA_INSTALL_DIR=~/ghidra_12.1.4_PUBLIC
ghidra-manuals
```

## Open a manual in Ghidra

In the Listing, right-click an instruction and select **Processor Manual**. The manual opens in your web browser at the page for that instruction. If there's no instruction under the cursor it opens at the first page.

If Ghidra can't work out which browser to launch it shows a warning with the file path, and a button to edit the Processor Manual options (the command and arguments Ghidra uses to open manuals, e.g. `firefox`).

## Upgrading Ghidra

Each Ghidra version is a separate folder, so run `ghidra-manuals` again on the new install. Downloaded PDFs are cached in `~/.cache/ghidra-manuals`, so manuals that haven't changed between versions are copied from the cache instead of downloaded again.

If a newer Ghidra references a manual this project doesn't know about yet, it's listed as missing with a note that it's not in the config. Please open an issue (or see [Updating config with new manuals](#updating-config-with-new-manuals)).

## Other options

- `--no-cache`: download everything again, ignoring the cache and already installed manuals.
- `--cache-dir PATH`: keep the download cache somewhere other than `~/.cache/ghidra-manuals`. Delete the cache folder any time to free up space.
- `--config PATH`: use your own copy of `config.json` (e.g. with extra backup URLs).

Every manual is checked against the sha256 of the revision Ghidra's `.idx` was made from, so a copy that would open on the wrong pages is never installed. Manuals are downloaded from the [ghidra-processor-manuals](https://github.com/meenmachine1/ghidra-processor-manuals/releases/tag/manuals) release first, then from the backup URLs in `config.json`.

## Full usage

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

If you do this, please open an issue so it can be added to the repo (if the manual/ver is not already in here).

# config.json

Each manual has:

- `path`/`filename`: where Ghidra expects the PDF.
- `sha256`: hashes of the copies known to match Ghidra's `.idx`. Any download that doesn't match one of these is rejected.
- `urls`: backup download URLs, tried in order after the release asset. `invalid_urls` are dead or serve the wrong revision.
- `page_count` (optional): for manuals where some copies have extra pages at the front (e.g. Renesas' "Old Company Name" notice). Downloads with more pages have the extras removed from the front before the hash is checked.

It also contains manuals that older Ghidra versions referenced (e.g. the 6805 processor folder from 10.1.2). They're only installed if your Ghidra's `.idx` files reference them.

# Maintenance tools

These need a clone (`pip install -e .` or just run them, they find the package in `src/`).

- `tools/check_urls.py` downloads every URL and the release asset for each manual and checks them against the pinned hashes. Dead URLs are moved to `invalid_urls`, working ones back to `urls`, and URLs serving an unknown file are reported so their revision can be checked. Writes `updated_manuals.json`, or the config in place with `--write`. Exits non-zero if a release asset is broken or a manual has no working source; backup URLs changing state are warnings unless `--strict` is passed.
- `tools/verify_pages.py ~/ghidra_xx.xx` checks the manuals installed in a Ghidra install match its `.idx` files, by looking for each instruction on the page the `.idx` file points at. A wrong revision shows up as a `FAIL`. It needs `pdftotext` (`apt install poppler-utils` / `brew install poppler`).
- `tools/publish_mirror.py --upload` uploads any manuals missing from (or different in) the ghidra-processor-manuals release. Needs the [GitHub CLI](https://cli.github.com/) logged in with write access to that repo.

# Known Issues

 - **HCS12** (`S12XCPUV2.pdf`): the only copies found are of the older S12CPUV2 Rev 4.0 manual, not the S12XCPUV2 (CPU12/CPU12X) manual the `.idx` was made from, so most pages are off. If anyone has `S12XCPUV2.pdf` please let me know.
 - Some upstream `.idx` files list mnemonics that aren't in their manual (e.g. microMIPS instructions in `mipsMic.idx`, AltiVec instructions in `PowerPC.idx`, ColdFire instructions in `68000.idx`). Ghidra will open those on whatever page the `.idx` says.

Please feel free to open a pull request to add more backup URLs to this project.
