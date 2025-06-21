"""
Implements a micro-framework to serve the website.
"""

import os
import json
import http.server
import argparse
import urllib.parse
from socketserver import ThreadingMixIn

from authentication import Authenticator, AuthStatus
from response_utils import load_and_check_content, send_content, send_response
from server_utils import ( HIDDEN_PATHS, CONTENT_MAP, reset_ip_logs,
                           do_submit, do_analyse )


DESC = "HTTP server."


class MyHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.do_auth = kwargs.pop('do_auth', True)
        self.authenticator = kwargs.pop('authenticator')
        self.setup_actions()
        super().__init__(*args, **kwargs)

    def setup_actions(self) -> None:
        if hasattr(self, 'headers'):
            if ('User-Agent' in self.headers):
                user_agent = self.headers['User-Agent'].lower()
                self.beautiful = (
                    False if 'wget' in user_agent or 'curl' in user_agent
                    else True
                )
        else:
            self.beautiful = True

        self.auth_actions = {
            AuthStatus.RETRY: lambda: send_response(self, 401),
            AuthStatus.FAIL: lambda: send_response(
                self,
                403,
                beautiful=self.beautiful
            )
        }

    def handle_get(self) -> None:
        path_map = {
            '/': 'index.html',
            '/form': 'psycho.html',
            '/view/input': 'data/input.json',
            '/view/profile': 'data/profile.json',
        }
        path = path_map.get(self.path, self.path.lstrip('/'))
        extn = path.split('.')[-1]

        if path in HIDDEN_PATHS:
            # User tried to access hidden files
            print('Warning: attempt to access hidden server files')
            send_response(self, 404, beautiful=self.beautiful, path=path)
            return

        # File must exist and extension must be supported
        if os.path.exists(path) and extn in CONTENT_MAP:
            ctype, rmode = CONTENT_MAP[extn]            
            if (content := load_and_check_content(self, path, ctype, rmode)):
                self.send_response(200)
                send_content(self, ctype, content)
        else:
            # Handle user error (4xx)
            if self.path in ['/view/input', '/view/profile']:
                task = (
                    'submit' if self.path.endswith('input')
                    else 'analyse'
                )
                send_response(self, 400,
                    message=f'You need to {task} the form!'
                )
            else:
                send_response(self, 404, beautiful=self.beautiful, path=path)

    def handle_post(self) -> None:
        path_map = {
            '/submit': lambda:do_submit(self),
            '/analyze': lambda: do_analyse(self)
        }
        action = path_map.get(self.path)
        if action is None:
            send_response(self, 404, path=path)
        else:
            action()

    def do_action(self) -> None:
        if self.do_auth:
            status = self.authenticator.handle_auth_and_get_status(self)
            self.auth_actions[status]()
        else:
            self.auth_actions[AuthStatus.SUCCESS]()

    def do_GET(self) -> None:
        self.setup_actions()
        self.auth_actions[AuthStatus.SUCCESS] = self.handle_get
        self.do_action()

    def do_POST(self) -> None:
        self.setup_actions()
        self.auth_actions[AuthStatus.SUCCESS] = self.handle_post
        self.do_action()


class ThreadedHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    """Handle requests in a separate thread."""

def main(args: argparse.Namespace) -> None:
    try:
        if args.reset_auth:
            reset_ip_logs()

        port_msg = f"Launching server on port: {args.port}."
        auth_msg = f"Authentication: {'dis' if args.disable_auth else 'en'}abled."
        ban_msg = '' if args.disable_auth else 'IP ban: ' + (
            'disabled.'if args.disable_ban
            else f"after {args.auth_attempts} failed attempts."
        )
        print(port_msg, auth_msg, ban_msg)

        authenticator = Authenticator(
            ban=not args.disable_ban,
            n_attempts=args.auth_attempts
        )
        webServer = ThreadedHTTPServer(
            ('', args.port),
            lambda *inner_args, **kwargs: MyHandler(
                *inner_args, **kwargs,
                do_auth=not args.disable_auth,
                authenticator=authenticator,
            )
        )
        webServer.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped server.')
    except Exception as e:
        print('\nServer did not start due to the following exception:', e)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=DESC)
    parser.add_argument('-p', '--port', type=int, default=8080,
                        help='port to listen on (default 8080)')
    parser.add_argument('-a', '--auth-attempts', type=int, default=3,
                        help='maximum authentication attempts (default 3)')
    parser.add_argument('--disable-ban', action='store_true', default=False,
                        help='disable IP blacklisting while logging IPs')
    parser.add_argument('--disable-auth', action='store_true', default=False,
                        help='disable IP logging and blacklisting')
    parser.add_argument('--reset-auth', action='store_true', default=False,
                        help='reset IP logs and blacklist')
    args = parser.parse_args()

    main(args)

