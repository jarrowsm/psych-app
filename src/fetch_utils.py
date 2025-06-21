""" 
Helper functions for fetching data, enabling the server to act as a client.
"""

import os
import requests
from datetime import datetime


def format_response_date(date: str) -> str:
    tz = date.split(' ')[-1]
    date = datetime.strptime(date,
            "%a, %d %b %Y %H:%M:%S %Z").strftime(
            "%d/%b/%Y %H:%M:%S")

    return f"{date} {tz}"


def print_response_info(uri: str, response: requests.Response) -> None:
    date = format_response_date(response.headers['Date'])
    status = response.status_code
    print(f"(Server) - - [{date}] \"GET {uri}\" {status} -")


def fetch_data(uri: str,
               json: bool = True,
               quiet: bool = False) -> dict | list | requests.Response:
    # General method to fetch (meta)data and print info

    response = requests.get(uri)

    if not quiet:
        print_response_info(uri, response)

    return response.json() if json else response


def check_img(img_path: str) -> bool:
    # Check that the image is supported
    extn = img_path.split('.')[-1]
    return extn in ['jpg', 'jpeg', 'png', 'gif']


def download_img(url: str, quiet: bool = True) -> str:
    # Given an image's URL, download it to the server
    # and return the local reference.
    # The local filename derives from the URL string

    response = fetch_data(url, False)

    # Dump the response content to the file
    os.makedirs('images', exist_ok=True)
    filename = os.path.join('images', url.split('/')[-1])
    with open(filename, 'wb') as fout:
        fout.write(response.content)

    if not quiet:
        print('  ->', filename)

    return filename

