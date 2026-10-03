# ghidra-manuals
A way to download Ghidra processor manuals that should be future proof. When future versions of Ghidra add support for new processors and have new processor manuals, this program will be able to add those new manuals to its config to download later.

Currently updated for **12.1** (all 43 manuals referenced by Ghidra 12.1.4 are available).

# How to Use

Install dependencies
`pip3 install -r requirements.txt`

Run `get_ghidra_manuals.py` with your ghidra installation path. For example:

```
./get_ghidra_manuals.py ~/ghidra_12.1.4_PUBLIC
```

The script reads the `.idx` files in your Ghidra install to find which manuals it needs, downloads each one (or uses the copy cached in `pdfs/`) and places it in the correct folder. It exits non-zero and lists the manuals it couldn't get if any are missing.

# Usage

```
usage: get_ghidra_manuals.py [-h] [--get-manual-idxs] [--overwrite-config] [--no-cache] ~/ghidra_xx.xx

Get ghidra manuals from the internet and put into your ghidra installation

positional arguments:
  ~/ghidra_xx.xx      Path to ghidra installation

optional arguments:
  -h, --help          show this help message and exit
  --get-manual-idxs   Update config.json to include manuals from current ghidra installation
  --overwrite-config  Overwrite config.json with the new manual indexes. This is not typically what you want to do. Will clear current URLs from config.json
  --no-cache          Force download of PDFs. Do not use cached PDFs.
```

# Notes and Updating config with new manuals

This whole repo is meant to be futureproof. If you initially used this script for a previous version of ghidra, and now want to use it for a newer version, you can simply run:

`./get_ghidra_manuals.py <path_to_new_ghidra_dir> --get-manual-idxs`

Which should give you one of the following outputs:

```shell
# There was a new processor manual added:
 > ./get_ghidra_manuals.py ~/ghidra_11.2.1 --get-manual-idxs          
Updated config with 1 configs.
Manuals info dumped to config.json

Done updating config.json.
```

or

```shell
# No new processor manuals were added:
 > ./get_ghidra_manuals.py ~/ghidra_11.2.1 --get-manual-idxs          
Did not update config.json as there were no missing manuals...

Done updating config.json.
```

# Checking manuals

`tools/check_urls.py` tries every URL in `config.json` (including `invalid_urls`) and sorts them into `urls`/`invalid_urls` depending on whether they still serve a PDF. It writes `updated_manuals.json`, or updates `config.json` in place with `--write`.

`tools/verify_pages.py ~/ghidra_xx.xx` checks the manuals installed in a Ghidra install actually match its `.idx` files, by looking for each instruction on the page the `.idx` file points at. A wrong revision of a manual shows up as a `FAIL`. It needs `pdftotext` (`apt install poppler-utils` / `brew install poppler`).

When adding a URL for a manual, make sure it's the same revision Ghidra's `.idx` was made from, otherwise Ghidra will open it on the wrong page.

Manuals where some copies have extra pages at the front (e.g. Renesas' "Old Company Name" notice) can set `"page_count": N` in `config.json` to the page count of the right copy. Downloads with more pages have the extras removed from the front (needs `pypdf`).

# Known Issues

 - **HCS12** (`S12XCPUV2.pdf`): the only copies found are of the older S12CPUV2 Rev 4.0 manual, not the S12XCPUV2 (CPU12/CPU12X) manual the `.idx` was made from, so most pages are off. If anyone has `S12XCPUV2.pdf` please let me know.
 - Some upstream `.idx` files list mnemonics that aren't in their manual (e.g. microMIPS instructions in `mipsMic.idx`, AltiVec instructions in `PowerPC.idx`, ColdFire instructions in `68000.idx`). Ghidra will open those on whatever page the `.idx` says.

Please feel free to open a pull request to add more backup URLs to this project.

## Notes

`config.json` also contains manuals that older Ghidra versions referenced (e.g. the 6805 processor folder from 10.1.2). They're only installed if your Ghidra's `.idx` files reference them.
