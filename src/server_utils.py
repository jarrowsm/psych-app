"""
Helper functions specific to the server.
"""

import os
import json
from http.server import BaseHTTPRequestHandler
from http.client import HTTPMessage

from analysis import analyse
from response_utils import send_response


# Define hidden paths for security
HIDDEN_PATHS = [
    'analysis.py', 'auth.json', 'authentication.py', 'default_input.json'
    'Dockerfile', 'fetch_utils.py', 'requirements.txt', 'reset_blacklist.py',
    'response_utils.py', 'server.py', 'server_utils.py', 'weights.json'
]


# Dictionary of content types and file i/o modes according to file
# extension. These are the ones supported in this app.
CONTENT_MAP = {
    'ico'  : ('image/x-icon', 'rb'),
    'html' : ('text/html', 'r'),
    'js'   : ('text/javascript', 'r'),
    'css'  : ('text/css', 'rb'),
    'jpg'  : ('image/jpeg', 'rb'),
    'jpeg' : ('image/jpeg', 'rb'),
    'png'  : ('image/png', 'rb'),
    'gif'  : ('image/gif', 'rb'),
    'json' : ('application/json', 'r')
}


# Resets the IP logs/blacklist
def reset_ip_logs() -> None:
    if not os.path.exists(auth_file := 'auth.json'):
        raise FileNotFoundError('Missing `{auth_file}`!')

    with open(auth_file, 'r') as fin:
        auth_json = json.load(fin)

    if not auth_json['attempts']:
        print('No attempts to reset.')
        return

    print(f'Found attempts {auth_json['attempts']}. Resetting...')

    auth_json['attempts'] = {}

    with open(auth_file, 'w') as fout:
        json.dump(auth_json, fout)


# Load serialised JSON string into a Python data structure
def load_json(json_str: str):
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return False
    
    return data


# Extract the raw POST string from the request body
def get_payload_str(handler: BaseHTTPRequestHandler) -> str:
    if 'Content-Length' in handler.headers:
        content_length = int(handler.headers['Content-Length'])
        return handler.rfile.read(content_length).decode()
    else:
        # May occur when actioning /analyze via curl/wget
        return "null"


# Check headers and parse POST string
def parse_payload_str(headers: HTTPMessage, post_str: str):
    if headers['Content-Type'] == 'application/json':
        return load_json(post_str)
    else:
        # Only supports JSON serialisation for now
        return False


# Logic for /submit
def do_submit(handler: BaseHTTPRequestHandler) -> None:
    post_str = get_payload_str(handler)
    data = parse_payload_str(handler.headers, post_str)

    if data == False:
        send_response(handler, 400,
            message='Improperly formatted JSON or missing Content-Type header')
        return

    if data == 'repeat':
        # 'Submit' before 'View Form'
        data_path = os.path.join('data', 'input.json')
        message = (
            'Form already submitted!' if os.path.exists(data_path)
            else 'You need to fill in the form!'
        )
        send_response(handler, 400, message=message)
        return

    # Fill any missing inputs (possible with curl/wget)
    default_path = 'default_input.json'

    if not os.path.exists(default_path):
        print(f"Warning: `{default_path}` not found, "
              f"unable to copy default inputs if needed")

    with open(default_path, 'r') as f:
        default = json.load(f)

    for k in default:
        if k not in data:
            data[k] = default[k]

    # Save responses
    os.makedirs('data', exist_ok=True)

    with open(os.path.join('data', 'input.json'), 'w') as fout:
        json.dump(data, fout)

    # Ensure no old analysis
    if os.path.exists(old_path := os.path.join('data', 'profile.json')):
        os.remove(old_path)

    send_response(handler, 200, message='Form responses saved!')


# Logic for /analyze
def do_analyse(handler: BaseHTTPRequestHandler) -> None:
    post_str = get_payload_str(handler)

    if post_str not in [None, "null"]:
        # Possible with Curl/Wget
        send_response(handler, 400,
            message='Unexpected payload for /analyze URI')
        return

    data_path = os.path.join('data', 'input.json')

    if os.path.exists(data_path):
        # Check for analysed tag
        with open(data_path, 'r') as f:
            if json.load(f).get('analysed'):
                send_response(handler, 400, message='Form already analysed!')
                return
    else:
        send_response(handler, 400, message='You need to submit the form!')
        return
    try:
        analyse()
    except Exception as e:
        print(f'Error during analysis: {e}')
        send_response(handler, 500,
            message="Server is misconfigured! There was an error during analysis")
        return

    send_response(handler, 200, message='Profile successfully created!')

