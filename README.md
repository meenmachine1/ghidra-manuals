# ghidra-manuals

# How to Use

Install dependencies
`pip3 install -r requirements.txt`

Run `get_ghidra_manuals.py` with your ghidra installation path. For example:

```
./get_ghidra_manuals.py ~/ghidra_10.1.2
```

The pdfs will be downloaded automatically and placed in the correct folders.

# Update config with new manuals

Using `get.py` you can overwrite the config.json.

TODO: merge get.py with get_ghidra_manuals.py. Add option to update current config. Use Popen to get the .idx file headers automatically instead of with a hardcoded string.

# Usage

```
usage: get_ghidra_manuals.py [-h] ~/ghidra_xx.xx

Get ghidra manuals from the internet and put into your ghidra installation

positional arguments:
  ~/ghidra_xx.xx  Path to ghidra installation

optional arguments:
  -h, --help      show this help message and exit
```
