# ghidra-manuals
A way to download Ghidra processor manuals that should be future proof. When future versions of Ghidra add support for new processors and have new processor manuals, this program will be able to add those new manuals to its config to download later.

# How to Use

Install dependencies
`pip3 install -r requirements.txt`

Run `get_ghidra_manuals.py` with your ghidra installation path. For example:

```
./get_ghidra_manuals.py ~/ghidra_10.1.2
```

The pdfs will be downloaded automatically and placed in the correct folders.

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
 > ./get_ghidra_manuals.py ~/ghidra_10.1.5 --get-manual-idxs          
Updated config with 1 configs.
Manuals info dumped to config.json

Done updating config.json.
```

or

```shell
# No new processor manuals were added:
 > ./get_ghidra_manuals.py ~/ghidra_10.1.5 --get-manual-idxs          
Did not update config.json as there were no missing manuals...

Done updating config.json.
```

# Missing Manuals

This project was originally created against ghidra 10.1.2 which had the 6805 processor folder which apparently no longer exists. If you get a warning about 

Currently the only missing manuals are:
 - HCS12 -- S12XCPUV2.pdf

Please feel free to open a pull request to add more backup URLs to this project.