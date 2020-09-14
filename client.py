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
            if method is 'GET' and query:
                payload += '?' + urlencode(query)
            elif query:
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

    def get_public_single_market(self, pair):
        """
        https://docs.ftx.com/#get-single-market

        :param pair: the trading pair to query
        :return: a list contains single market info
        """

        return self._send_request('public', 'GET', f"markets/{pair.upper()}")

    def get_public_orderbook(self, pair, depth=20):
        """
        https://docs.ftx.com/#get-orderbook

        :param pair: the trading pair to query
        :param depth: the price levels depth to query
        :return: a dict contains asks and bids data
        """
    
        return self._send_request('public', 'GET', f"/markets/{pair}/orderbook", {'depth': depth})

    def get_public_recent_trades(self, pair, limit=20, start_time=None, end_time=None):
        """
        https://docs.ftx.com/#get-trades

        :param pair: the trading pair to query
        :param limit: the records limit to query
        :param start_time: the target period after Epoch time in seconds
        :param end_time: the target period before Epoch time in seconds
        :return: a list contains all completed orders in exchange
        """

        query = {
            'limit': limit,
        }

        if start_time != None:
            query.update({ 
                'start_time': start_time,
            })
        
        if end_time != None:
            query.update({ 
                'end_time': end_time
            })

        return self._send_request('public', 'GET', f"/markets/{pair}/trades", query)

    def get_public_k_line(self, pair, resolution=14400, limit=20, start_time=None, end_time=None):
        """
        https://docs.ftx.com/#get-historical-prices

        :param pair: the trading pair to query
        :param resolution: the time period of K line in seconds
        :param limit: the records limit to query
        :param start_time: the target period after Epoch time in seconds
        :param end_time: the target period before Epoch time in seconds
        :return: a list contains all OHLC prices in exchange
        """

        query = {
            'resolution': resolution,
            'limit': limit,
        }

        if start_time != None:
            query.update({ 
                'start_time': start_time,
            })
        
        if end_time != None:
            query.update({ 
                'end_time': end_time
            })

        return self._send_request('public', 'GET', f"/markets/{pair}/candles", query)
    
    def get_public_all_futures(self):
        """
        https://docs.ftx.com/#list-all-futures

        :return: a list contains all available futures
        """

        return self._send_request('public', 'GET', f"/futures")
    
    def get_public_single_future(self, pair):
        """
        https://docs.ftx.com/#get-single-market

        :param pair: the trading pair to query
        :return: a list contains single future info
        """

        return self._send_request('public', 'GET', f"futures/{pair.upper()}")
        
    # Private API

    def get_private_account_information(self):
        """
        https://docs.ftx.com/#get-account-information

        :return: a dict contains all personal profile and positions information
        """

        return self._send_request('private', 'GET', f"account")
    
    def get_private_account_positions(self, showAvgPrice=False):
        """
        https://docs.ftx.com/#get-positions

        :param showAvgPrice: display AvgPrice or not
        :return: a dict contains all positions
        """
        
        return self._send_request('private', 'GET', f"positions", {'showAvgPrice': showAvgPrice})
    
    def get_private_all_subaccounts(self):
        """
        https://docs.ftx.com/#get-all-subaccounts
        
        :return: a list contains all subaccounts
        """

        return self._send_request('private', 'GET', f"subaccounts")
    
    def get_private_subaccount_balances(self, name):
        """
        https://docs.ftx.com/#get-subaccount-balances

        :param name: the subaccount name to query
        :return: a list contains subaccount balances
        """

        return self._send_request('private', 'GET', f"subaccounts/{name}/balances")
    
    def get_private_wallet_coins(self):
        """
        https://docs.ftx.com/#get-coins

        :return: a list contains all coins in wallet
        """

        return self._send_request('private', 'GET', f"wallet/coins")
    
    def get_private_wallet_balances(self):
        """
        https://docs.ftx.com/#get-balances

        :return: a list contains current account balances
        """

        return self._send_request('private', 'GET', f"wallet/balances")
    
    def get_private_wallet_all_balances(self):
        """
        https://docs.ftx.com/#get-balances-of-all-accounts

        :return: a list contains all accounts balances
        """
        
        return self._send_request('private', 'GET', f"wallet/all_balances")
    
    def get_private_wallet_deposit_address(self, coin, chain):
        """
        https://docs.ftx.com/#get-deposit-address

        :param currency: the specific coin to endpoint
        :param chain: the blockchain deposit from, should be 'omni' or 'erc20', 'trx' or 'sol'
        :return: a list contains deposit address
        """

        return self._send_request('private', 'GET', f"wallet/deposit_address/{coin.upper()}", {'method': chain})

    def get_private_wallet_deposit_history(self, limit=20, start_time=None, end_time=None):
        """
        https://docs.ftx.com/#get-deposit-history

        :param limit: the records limit to query
        :param start_time: the target period after Epoch time in seconds
        :param end_time: the target period before Epoch time in seconds
        :return: a list contains deposit history
        """

        query = {
            'limit': limit,
        }

        if start_time != None:
            query.update({ 
                'start_time': start_time,
            })
        
        if end_time != None:
            query.update({ 
                'end_time': end_time
            })

        return self._send_request('private', 'GET', f"wallet/deposits", query)

    def get_private_wallet_withdraw_history(self, limit=20, start_time=None, end_time=None):
        """
        https://docs.ftx.com/#get-withdrawal-history

        :param limit: the records limit to query
        :param start_time: the target period after Epoch time in seconds
        :param end_time: the target period before Epoch time in seconds
        :return: a list contains withdraw history
        """
    
        query = {
            'limit': limit,
        }

        if start_time != None:
            query.update({ 
                'start_time': start_time,
            })
        
        if end_time != None:
            query.update({ 
                'end_time': end_time
            })

        return self._send_request('private', 'GET', f"wallet/withdrawals", query)

    def get_private_wallet_airdrops(self, limit=20, start_time=None, end_time=None):
        """
        https://docs.ftx.com/#get-airdrops

        :param limit: the records limit to query
        :param start_time: the target period after Epoch time in seconds
        :param end_time: the target period before Epoch time in seconds
        :return: a list contains airdrop history
        """
    
        query = {
            'limit': limit,
        }

        if start_time != None:
            query.update({ 
                'start_time': start_time,
            })
        
        if end_time != None:
            query.update({ 
                'end_time': end_time
            })

        return self._send_request('private', 'GET', f"wallet/airdrops", query)