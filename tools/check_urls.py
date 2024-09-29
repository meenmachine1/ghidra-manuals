#!/usr/bin/env python3

"""
This script validates all the urls for each config entry
"""

import requests
import filetype
import json
import pathlib
import hashlib


with open("../config.json", "r") as f:
    data = json.load(f)

def check_url_status_and_type(url, path, filename):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # Raises an error for 4xx or 5xx status codes
        
        # Check if the file is a PDF
        kind = filetype.guess(response.content)
        if kind is not None and kind.mime == 'application/pdf':
            path = pathlib.Path(f"{path}")
            path.mkdir(parents=True, exist_ok=True)

            with open(str(path.absolute()) + "/" + filename, "wb") as f:
                f.write(response.content)
            
            return hashlib.md5(response.content)
        else:
            return None
    
    except requests.RequestException as e:
        print(f"invalid (error: {e})")
        return None

def validate_manual_urls(manuals):
    for manual in manuals:
        valid_urls = list(manual.get("urls", []))
        invalid_urls = list(manual.get("invalid_urls", []))

        hashes = []
        for url in manual['urls']:
            print(f"Testing: {url}")
            result = check_url_status_and_type(url, "pdfs/" + manual["path"], manual["filename"])
            if result != None:
                valid_urls.append(url)
                hashes.append(result)
            else:
                invalid_urls.append(url)
        
        # Determine if all the pdfs downloaded are the same for the same proc manual. If not print a warning
        hashes = [hash.digest() for hash in hashes]
        if len(set(hashes)) > 1:
            print(f"Bad hashes for manual: {manual}")
            print(hashes)

        manual['urls'] = valid_urls
        manual['invalid_urls'] = invalid_urls

    return manuals

updated_data = validate_manual_urls(data['manuals'])

with open('updated_manuals.json', 'w') as outfile:
    json.dump({"manuals": updated_data}, outfile, indent=4)

print("URLs have been validated and the JSON has been updated. Saved to 'updated_manuals.json'.")
