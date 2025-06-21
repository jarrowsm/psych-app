"""
Provides flexible authentication by matching the hashed credentials with the correct hash
stored on the server. The user may optionally be IP banned after a specified number of
failed attempts - this behaviour is enabled by default.
Use `python server.py --help` for more information.
"""

import json
import base64
import hashlib
from enum import Enum
from typing import Optional
from http.server import BaseHTTPRequestHandler
from http.client import HTTPMessage

class AuthStatus(Enum):
    SUCCESS = 1
    RETRY = 0
    FAIL = -1

class Authenticator:
    def __init__(self,
                 ban: bool = True,
                 n_attempts: int = 3,
                 auth_file: str = 'auth.json'):
        self.ban = ban
        self.nattempts = n_attempts
        self.authf = auth_file
        self.status = AuthStatus.RETRY
        self.authd = self.load_auth()
    
    def load_auth(self) -> Optional[str]:
        try:
            with open(self.authf, "r") as f:
                authd = json.load(f)
                if 'hash' not in authd:
                    raise FileNotFoundError
                else:
                    self.hash = authd['hash']
                    return authd

        except FileNotFoundError:
            print(f'Missing {self.authf}. Authentication is disabled.')
            return None

    def save_auth(self) -> None:
        try:
            if not hasattr(self, 'authd'):
                raise ValueError
            with open(self.authf, "w") as f:
                json.dump(self.authd, f)
        except ValueError:
            print("Auth dict does not exist")

    def authenticate(self, headers: HTTPMessage) -> bool:
        # If the authentication header is present, extract the authentication
        # string sent from the client
        authstr = headers['Authorization'].split()[-1]

        # Decode & hash the authentication string
        decoded_str = base64.b64decode(authstr)
        hash_str = hashlib.sha256(decoded_str).hexdigest()
        
        return hash_str == self.hash

    def handle_auth(self, handler: BaseHTTPRequestHandler) -> None:
        if self.authd is None:
            # Disable authentication
            self.status = AuthStatus.SUCCESS
            return

        client_addr = handler.client_address[0]
        auth_attempts = self.authd.get('attempts', {})
        client_attempts = auth_attempts.get(client_addr, 0)

        if self.ban and client_attempts >= self.nattempts:
            # Client was previously banned
            self.status = AuthStatus.FAIL
            return

        if 'Authorization' not in handler.headers:
            # Client did not provide authentication
            self.status = AuthStatus.RETRY
            return
    
        # Perform authentication
        if self.authenticate(handler.headers):
            # Success, reset attempts
            auth_attempts.pop(client_addr, None)
            self.authd['attempts'] = auth_attempts
            self.save_auth()
            self.status = AuthStatus.SUCCESS
        else:
            self.status = AuthStatus.RETRY
            if self.ban:
                # Increment attempts
                client_attempts += 1
                auth_attempts[client_addr] = client_attempts
                self.authd['attempts'] = auth_attempts
                self.save_auth()
                print('IP: {} has {} failed attempts'.format(
                    client_addr, client_attempts
                ))
    
                if client_attempts >= self.nattempts:
                    # Ban user IP
                    self.status = AuthStatus.FAIL
    
    def get_status(self, as_value: bool = False) -> AuthStatus:
        return self.status.value if as_value else self.status

    def handle_auth_and_get_status(self,
                                   handler: BaseHTTPRequestHandler,
                                   as_value: bool = False) -> AuthStatus:
        self.handle_auth(handler)
        return self.get_status(as_value)

