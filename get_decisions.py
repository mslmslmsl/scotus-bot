"""Script to export all SCOTUS opinions (through 2013; needs to be updated)"""

import re
import json
import os
import time
import requests
from bs4 import BeautifulSoup

MAX_ATTEMPTS_LOADING_EACH_PAGE = 3
RETRY_DELAY = 30
CASES_FILE = 'cases.json'
FOLDER = 'pages'


def extract_cases_from_page(response):
    """Review the U.S. Reports page and extract case info"""

    cases = []
    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")

    # Find the links
    us_reports_links = soup.find_all(
        "a",
        href=True,
        text=lambda text: text and text.strip().startswith("U.S. Reports:")
    )

    for case in us_reports_links:

        # Define link pattern indicating we're looking at a case
        case_link_pattern = re.compile(
            r'https:\/\/www\.loc\.gov\/item\/usrep\d{3}(\d+|[ivxlcdm]+)\/'
        )
        case_link = case.get('href')

        # Check if the link takes us to something that looks like a decision
        if case_link_pattern.match(case_link):

            raw = re.search(r'U\.S\. Reports\: (.*)', str(case)).group(1)
            all_parts_present = re.search(
                r'U\.S\. Reports\: (.*)'            # Capture name
                r'\,\s(\d+)\sU\.S\.\s'              # Capture volume
                r'(?:\(.*\)\s)?'                    # Skip alt reporter
                r'(?:\[)?(\d+|[ivxlcdm]+)(?:\])?'   # Capture page
                r'\s\((\d{4}.*)\)',                 # Capture year
                str(case)
            )

            # Sometimes, the case name is too long
            if not all_parts_present:
                match = re.search(r'.*\/usrep(\d{3})(\d+)', case_link)
                volume, page = match.groups()
                name, year = "", ""
            else:
                name, volume, page, year = \
                    all_parts_present.groups()

            # Add the case information to our list
            cases.append({
                "raw case info": f"{raw}",
                "name": f"{name}",
                "citation": f"{volume} U.S. {page}",
                "year": f"{year}",
                "url": (
                    "https://tile.loc.gov/storage-services/service/ll/usrep/"
                    f"usrep{volume.zfill(3)}/usrep{volume.zfill(3)}"
                    f"{page.zfill(3)}/usrep{volume.zfill(3)}{page.zfill(3)}"
                    ".pdf"
                )
            })

    # Return the list of cases
    return cases


def save_data_to_file(data, index):
    """Save case info to file"""
    full_path = os.path.join(FOLDER, f"cases_page_{str(index).zfill(3)}.json")
    with open(full_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=2)
        file.write('\n')


def main():
    """main"""

    index = 1
    more_pages = True

    while more_pages:
        # Sometimes the USR page doesn't load, so try a few times
        for _ in range(MAX_ATTEMPTS_LOADING_EACH_PAGE):
            try:
                print(f"Trying to access page {index}.")
                full_url = (
                    "https://www.loc.gov/collections/united-states-reports/?c="
                    f"150&fa=subject:court+opinions&sb=date&sp={index}&st=list"
                )
                response = requests.get(full_url, timeout=100)

                if response.status_code == 200:
                    data = extract_cases_from_page(response)
                    if data is not None:
                        print(f"Adding cases from page {index}")
                        save_data_to_file(data, index)
                        index += 1
                    else:
                        print(f"No data to add from page {index}.")
                    break

                # If we get a 404, I assume we've reviewed every page
                elif response.status_code == 404:
                    print(f"Page {index} not found.")
                    more_pages = False
                    break

                # If we get anything else, wait some seconds then try again
                else:
                    print(f"Got code {response.status_code} on page {index}.")
                    print(f"Trying again in {RETRY_DELAY} seconds.")
                    time.sleep(RETRY_DELAY)

            except requests.RequestException as e:
                print(f"Error loading page {index}: {e}.")
                print(f"Retrying in {RETRY_DELAY} seconds.")
                time.sleep(RETRY_DELAY)


if __name__ == "__main__":
    main()
