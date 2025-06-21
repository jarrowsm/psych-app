"""
Helper functions for sending responses.
"""

import os
import json
from http.server import BaseHTTPRequestHandler
from http.client import HTTPMessage


def gobble_file(filename: str, mode: str = 'r') -> bytes | str:
    if mode not in ['r', 'rb']:
        raise ValueError('`mode` must be `r` or `rb`')

    with open(filename, mode) as fin:
        content = fin.read()

    return content


def load_and_check_content(handler: BaseHTTPRequestHandler,
                           path: str,
                           ctype: str,
                           rmode: str) -> bytes | bool:
    # Read the content using the appropriate read mode
    try:
        content = gobble_file(path, mode=rmode)
        if rmode == 'r':
            if 'json' in ctype:
                    jsond = json.loads(content)
                    jsond['status'] = 'ok'
                    content = json.dumps(jsond)
            content = content.encode()
        return content

    except Exception:
        send_response(handler, 500,
            message="Server misconfigured! Could not send content")
        return False


def send_content(handler: BaseHTTPRequestHandler,
                 ctype: str,
                 content: bytes) -> None:
    handler.send_header('Content-Type', ctype)
    handler.end_headers()
    handler.wfile.write(content)


def send_response(handler: BaseHTTPRequestHandler,
                  status: int,
                  **kwargs) -> None:
    if kwargs.get('beautiful', False):
        if status not in [403, 404]:
            print('`beautiful` is only for 404 or 403 (not {status})! Sending JSON')
        elif not os.path.exists(err_path := f'{status}.html'):
            print(f'`{err_path}` does not exist! Sending JSON')
        else:
            if (content := load_and_check_content(handler, err_path, 'text/html', 'r')):
                handler.send_response(status)
                send_content(handler, 'text/html', content)
            return

    handler.send_response(status)

    if status == 401:
        auth = kwargs.get('auth', 'Web 159352')
        handler.send_header('WWW-Authenticate', f'Basic realm="{auth}"')
        handler.end_headers()
        return

    handler.send_header('Content-Type', 'application/json')
    handler.end_headers()

    if status == 200:
        content = json.dumps(
            {'status'  : status,
             'message' : kwargs.get('message', 'OK')}
        ).encode()
    elif status == 400:
        content = json.dumps(
            {'status'  : status,
             'message' : kwargs.get('message', 'Bad request')}
        ).encode()
    elif status == 403:
        content = json.dumps(
            {'status'  : status,
             'message' : kwargs.get('message', 'Access forbidden')}
        ).encode()
    elif status == 404:
        contentd = {'status'  : status,
                    'message' : kwargs.get('message', 'Resource not recognised')}
        if (path := kwargs.get('path')):
            contentd['path'] = path
        content = json.dumps(contentd).encode()
    elif status == 500:
        content = json.dumps(
            {'status'  : status,
             'message' : kwargs.get('message', 'Server error')}
        ).encode()
    else:
        raise ValueError(f"{status} response is not supported")

    handler.wfile.write(content)

