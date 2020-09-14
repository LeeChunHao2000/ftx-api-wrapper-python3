import hashlib
import hmac
import json
import requests

from urllib.parse import urlencode

from constants import *
from helpers import *


class Client(object):
    def __init__(self, key, secret, subaccount=None, timeout=30):
        self._api_key = key
        self._api_secret = secret
        self._api_subacc = subaccount
        self._api_timeout = int(timeout)

    def _build_headers(self, scope, method, endpoint, query=None):
        if query is None:
            query = {}

        endpoint = '/api/' + endpoint

        headers = {
            'Accept': 'application/json',
            'User-Agent': 'FTX-Trader/1.0',
        }

        if scope.lower() == 'private':
            nonce = str(get_current_timestamp())
            payload = f'{nonce}{method.upper()}{endpoint}'
            if query:
                payload += json.dumps(query)
            print (payload)
            sign = hmac.new(bytes(self._api_secret, 'utf-8'), bytes(payload, 'utf-8'), hashlib.sha256).hexdigest()

            headers.update({
                # This header is REQUIRED to send JSON data.
                # or you have to send PLAIN form data instead.
                'Content-Type': 'application/json',
                'FTX-KEY': self._api_key,
                'FTX-SIGN': sign,
                'FTX-TS': nonce
            })

            if self._api_subacc:
                headers.update({
                # Only include line if you want to access a subaccount 
                'FTX-SUBACCOUNT': urllib.parse.quote(self._api_subacc)
            })

        return headers

    def _build_url(self, scope, method, endpoint, query=None):
        if query is None:
            query = {}

        if scope.lower() == 'private':
            url = f"{PRIVATE_API_URL}/{endpoint}"
        else:
            url = f"{PUBLIC_API_URL}/{endpoint}"

        if method == 'GET':
            return f"{url}?{urlencode(query, True, '/[]')}" if len(query) > 0 else url
        else:
            return url

    def _send_request(self, scope, method, endpoint, query=None):
        if query is None:
            query = {}

        # Build header first
        headers = self._build_headers(scope, method, endpoint, query)

        # Build final url here
        url = self._build_url(scope, method, endpoint, query)

        if method == 'GET':
            response = requests.get(url, headers = headers).json()
        elif method == 'POST':
            response = requests.post(url, headers = headers, json = query).json()
        elif method == 'DELETE':
            response == requests.delete(url, headers = headers, json = query).json()

        return response

    # Public API
    def get_public_all_markets(self):
        """
        https://docs.ftx.com/#markets

        :return: a list contains all available markets
        """
        return self._send_request('public', 'GET', f"markets")

    # Private API

    def get_private_account_information(self):
        """
        https://docs.ftx.com/#get-account-information

        :return: a dict contains all personal profile and positions information
        """

        return self._send_request('private', 'GET', f"account")