#!/usr/bin/env python3

import argparse
import filetype
import json
import requests
import pathlib
import os

CONFIG_FILE = "config.json"
SAVE_DIR = "pdfs"

manual_config_skel = {
    "info": "",
    "path": "",
    "filename": "",
    "urls": []
}

def get_real_path(path):
    idx_name = path.split("/")[-1]

    return path[:path.index(idx_name)]

def get_idx_files_headers(ghidra_path, current_config={}):
    # https://stackoverflow.com/questions/18394147/how-to-do-a-recursive-sub-folder-search-and-return-files-in-a-list
    idx_paths = list(pathlib.Path(ghidra_path).rglob("*.idx"))

    patterns = [
        {
            "start": "@",
            "end": "[",
            "field": "filename"
        },
        {
            "start": "[",
            "end": "]",
            "field": "info"
        },
    ]

    manuals = []
    for idx_path in idx_paths:
        with open(idx_path, "rb") as idx_f:
            first_line = idx_f.readline().strip()
            first_line = first_line.decode(errors='ignore')
        
        cur_manual_config = dict(manual_config_skel)

        for pattern_num, pattern in enumerate(patterns):
            if not ("start" in pattern and "end" in pattern and "field" in pattern):
                print(f"Warning: Pattern num: {pattern_num} does not have all info.")
            
            start, end, field = pattern["start"], pattern["end"], pattern["field"]

            try:
                l = first_line
                cur_manual_config[field] = l[l.index(start)+len(start):l.index(end)]
            except ValueError as e:
                print(f"Warning: Unable to find start ({start}) or end ({end}) in line: {l}")
                print("Skipping...")
                continue
        
        cur_manual_config["path"] = get_real_path(f"./{idx_path.relative_to(ghidra_path)}")
        cur_manual_config["filename"] = cur_manual_config["filename"].strip()

        manuals.append(cur_manual_config)

    new_config = {"manuals": manuals}

    if current_config:
        # Yes this whole else statement is a disgustingly slow solve but I'm tired of this ish. Sorry
        filenames_current = set([manual["path"] + manual["filename"] for manual in current_config["manuals"]])
        filenames_new = set([manual["path"] + manual["filename"] for manual in new_config["manuals"]])

        missing_filenames = set(filenames_new) - set(filenames_current)

        if not missing_filenames:
            print(f"Did not update {CONFIG_FILE} as there were no missing manuals...")
            return current_config

        for missing_filename in missing_filenames:
            missing_manual = None
            for manual in new_config["manuals"]:
                if (manual["path"] + manual["filename"]) == missing_filename:
                    missing_manual = manual
            
            # Yes I understand this can never happen
            if missing_manual is None:
                print("Warning??: Unable to find missing manual in new_config. This should be impossible. Open up an issue")
                continue
            
            current_config["manuals"].append(dict(missing_manual))

        print(f"Updated config with {len(missing_filenames)} configs.")
    else:
        current_config = new_config

    with open(CONFIG_FILE, "w") as config_json_f:
        json.dump(current_config, config_json_f, indent=4)

    print(f"Manuals info dumped to {CONFIG_FILE}")
    
    return current_config

def check_folder_exists(folder_path, make=False):
    if os.path.exists(folder_path):
        if not (os.path.isdir(folder_path)):
            print(f"Folder '{folder_path}' is a file not a directory. Please delete.")
            print("Exiting...")
            exit(-1)
        return True
    elif make:
        # TODO: Catch exceptions
        pathlib.Path(folder_path).mkdir(folder_path, exist_ok=True, parents=True)
        return True
    
    return False

def check_file_is_pdf(file_path):
    t = filetype.guess(file_path)

    return 'pdf' in t.mime if t is not None else False

# Don't redownload the pdf file if it already exists
def use_pdf_cache(pdf_save_filepath):
    pdf_content = None

    if check_folder_exists(SAVE_DIR):
        if os.path.exists(pdf_save_filepath) and check_file_is_pdf(pdf_save_filepath):
            with open(pdf_save_filepath, "rb") as pdf_f:
                pdf_content = pdf_f.read()

    return pdf_content

def download_pdf_and_store(urls, filename, file_path, no_cache):
    check_folder_exists(SAVE_DIR, make=True)

    pdf_save_filepath = f"{SAVE_DIR}/{filename}"

    # Try local cache first
    pdf_content = use_pdf_cache(pdf_save_filepath) if not no_cache else None

    if pdf_content is None:
        # Download from internet
        for url in urls:
            # Check return code to make sure it was a success
            try:
                pdf_content = requests.get(url).content

                with open(pdf_save_filepath, "wb") as pdf_f:
                    pdf_f.write(pdf_content)

                if check_file_is_pdf(pdf_save_filepath):
                    break
                else:
                    print(f"WARNING: File in url: {url} is not a PDF. Trying next URL.")
                    pdf_content = None
            except requests.exceptions.RequestException as e:
                print(f"WARNING: Could not open url: {url}. Got error: {e}")
    else:
        print(f"Found manual in cache. Using that instead. Delete file in {SAVE_DIR} if you'd like to redownload.")

    if pdf_content is None:
        print(f"WARNING: Could not download filename: {filename} to place in {file_path}")
        return False

    with open(f"{file_path}/{filename}", "wb") as pdf_f:
        pdf_f.write(pdf_content)

    return True

def load_config():
    if not os.path.exists(CONFIG_FILE):
        #TODO: Update this message when you combine get.py and get_ghidra_manuals.py"
        print(f"Could not find config file {CONFIG_FILE}.")
        print("If it does not exist you can run get.py to create it but manually fill URLs.")
        print("Exiting...")
        exit(-1)
    with open(CONFIG_FILE, "r") as config_f:
        return json.load(config_f)

def main(args):

    if args.overwrite_config and not args.get_manual_idxs:
        print(f"--overwrite-config flag must only be used with --get-manual-idxs flag.")
        print("Exiting...")
        exit(-1)

    if not check_folder_exists(pathlib.Path(args.ghidra_path + "/Ghidra/").as_posix()):
        print("Ghidra path given does not contain a ghidra installation.")
        print("Exiting...")
        exit(-1)

    # Get the new manual_idxs without worrying about if config.json is okay
    if args.overwrite_config and args.get_manual_idxs:
        print(f"Overwriting current {CONFIG_FILE}. URLs will be cleared.")
        get_idx_files_headers(args.ghidra_path)

    config = load_config()
    if not (isinstance(config, dict) and 'manuals' in config):
        print("Config file is not set up properly.")
        print("Exiting...")
        exit(-1)
    
    # Done down here AFTER the config load since we we'll be updating the config
    if args.get_manual_idxs and not args.overwrite_config:
        print("Updating manual config json with current ghidra install")
        get_idx_files_headers(args.ghidra_path, config)
    
    if args.get_manual_idxs:
        print(f"\nDone updating {CONFIG_FILE}.")
        exit()

    print("Getting manuals...\n")
    for manual_idx, manual in enumerate(config['manuals']):
        if not ('path' in manual and 'filename' in manual and 'urls' in manual):
            print(f"Manual num: {manual_idx} does not have all proper fields. Skipping...\n")
            continue
        
        filename, manual_file_path, urls = manual['filename'], f"{args.ghidra_path}/{manual['path']}", manual["urls"]
        manual_file_path = pathlib.Path(manual_file_path).as_posix()

        if not check_folder_exists(manual_file_path):
            print(f"WARNING: Could not find manual store path folder: {manual_file_path} for {filename}.")
            print("Is your Ghidra path correct? Skipping...\n")
            continue

        if not urls:
            print(f"WARNING: {filename} does not have any URLs in its config. Skipping...\n")
            continue

        if download_pdf_and_store(urls, filename, manual_file_path, args.no_cache):
            print(f"Successfully got manual: {filename}.\n")
        else:
            print(f"WARNING: Could not get manual: {filename}.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get ghidra manuals from the internet and put into your ghidra installation")

    parser.add_argument("ghidra_path",
                        help="Path to ghidra installation",
                        metavar="~/ghidra_xx.xx")

    parser.add_argument("--get-manual-idxs",
                        help=f"Update {CONFIG_FILE} to include manuals from current ghidra installation",
                        action="store_true",
                        default=False)
    
    parser.add_argument("--overwrite-config",
                        help=f"""\
Overwrite {CONFIG_FILE} with the new manual indexes. \
This is not typically what you want to do. Will clear current URLs from {CONFIG_FILE}""",
                        action="store_true",
                        default=False)

    parser.add_argument("--no-cache",
                        help="Force download of PDFs. Do not use cached PDFs.",
                        action="store_true",
                        default=False)

    args = parser.parse_args()

    main(args)