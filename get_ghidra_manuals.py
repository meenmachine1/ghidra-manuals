#!/usr/bin/env python3

import argparse
import filetype
import json
import requests
import pathlib
import os

CONFIG_FILE = "config.json"
SAVE_DIR = "pdfs"

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

    return 'pdf' == t if t is not None else False

def download_pdf_and_store(urls, filename, file_path):
    pdf_content = None

    check_folder_exists(SAVE_DIR, make=True)

    pdf_save_filepath = f"{SAVE_DIR}/{filename}"
    for url in urls:
        try:
            pdf_content = requests.get(url).content

            with open(pdf_save_filepath, "wb") as pdf_f:
                pdf_f.write(pdf_content)

            if check_file_is_pdf(pdf_save_filepath):
                break
        except Exception as e:
            print("Could not open url: {}")

    if pdf_content is None:
        print(f"Warning: Could not download filename: {filename} to place in {file_path}")
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

    config = load_config()

    if not check_folder_exists(pathlib.Path(args.ghidra_path + "/Ghidra/").as_posix()):
        print("Ghidra path given does not contain a ghidra installation.")
        print("Exiting...")
        exit(-1)

    if not (isinstance(config, dict) and 'manuals' in config):
        print("Config file is not set up properly.")
        print("Exiting...")
        exit(-1)
    
    for manual_idx, manual in enumerate(config['manuals']):
        if not ('path' in manual and 'filename' in manual and 'urls' in manual):
            print(f"Manual num: {manual_idx} does not have all proper fields. Skipping...\n")
            continue
        
        filename, manual_file_path, urls = manual['filename'], f"{args.ghidra_path}/{manual['path']}", manual["urls"]
        manual_file_path = pathlib.Path(manual_file_path).as_posix()

        if not check_folder_exists(manual_file_path):
            print(f"Could not find manual store path folder: {manual_file_path}. Skipping...\n")
            continue

        if download_pdf_and_store(urls, filename, manual_file_path):
            print(f"Successfully got manual: {filename}.\n")
        else:
            print(f"Could not get manual: {filename}.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get ghidra manuals from the internet and put into your ghidra installation")

    parser.add_argument("ghidra_path",
                        help="Path to ghidra installation",
                        metavar="~/ghidra_xx.xx")

    args = parser.parse_args()

    main(args)