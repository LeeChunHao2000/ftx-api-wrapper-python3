import hashlib
import hmac
import json
import requests
from typing import List, NewType, Optional, Dict
import urllib
from urllib.parse import urlencode

from . import constants
from . import helpers


ListOfDicts = NewType("ListOfDicts", List[dict])
# shape:
#   {'bids': [[2259.5, 0.0013],
#             ...],
#    'asks': [[2299.5, 1.8906],
#             ...],
#   }
BidsAndAsks = NewType("BidsAndAsks", Dict[str, List[List[float]]])


class Invalid(Exception):
    pass


class DoesntExist(Exception):
    pass


class Client:
    def __init__(self, key, secret, subaccount=None, timeout=30):
        self._api_key = key
        self._api_secret = secret
        self._api_subaccount = subaccount
        self._api_timeout = int(timeout)

    def _build_headers(self, scope, method, endpoint, query=None):
        if query is None:
            query = {}

        endpoint = "/api/" + endpoint

        headers = {
            "Accept": "application/json",
            "User-Agent": "FTX-Trader/1.0",
        }

        if scope.lower() == "private":
            nonce = str(helpers.get_current_timestamp())
            payload = f"{nonce}{method.upper()}{endpoint}"
            if method == "GET" and query:
                payload += "?" + urlencode(query)
            elif query:
                payload += json.dumps(query)
            sign = hmac.new(
                bytes(self._api_secret, "utf-8"),
                bytes(payload, "utf-8"),
                hashlib.sha256,
            ).hexdigest()

            headers.update(
                {
                    # This header is REQUIRED to send JSON data.
                    "Content-Type": "application/json",
                    "FTX-KEY": self._api_key,
                    "FTX-SIGN": sign,
                    "FTX-TS": nonce,
                }
            )

            if self._api_subaccount:
                headers.update(
                    {
                        # If you want to access a subaccount
                        "FTX-SUBACCOUNT": urllib.parse.quote(self._api_subaccount)
                    }
                )

        return headers

    def _build_url(self, scope, method, endpoint, query=None):
        if query is None:
            query = {}

        if scope.lower() == "private":
            url = f"{constants.PRIVATE_API_URL}/{endpoint}"
        else:
            url = f"{constants.PUBLIC_API_URL}/{endpoint}"

        if method == "GET":
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

        try:
            if method == "GET":
                response = requests.get(url, headers=headers).json()
            elif method == "POST":
                response = requests.post(url, headers=headers, json=query).json()
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, json=query).json()
        except Exception as e:
            print("[x] Error: {}".format(e.args[0]))

        if "result" in response:
            return response["result"]
        elif "error" in response:
            raise DoesntExist(response["error"])
        else:
            return response

    # Public API
    def get_markets(self) -> ListOfDicts:
        """
        https://docs.ftx.com/#markets
        """
        return self._send_request("public", "GET", "markets")

    def get_market(self, pair: str) -> Optional[dict]:
        """
        https://docs.ftx.com/#get-single-market
        :param pair: the trading pair to query
        """
        return self._send_request("public", "GET", f"markets/{pair.upper()}")

    def get_orderbook(self, pair: str, depth=20) -> BidsAndAsks:
        """
        https://docs.ftx.com/#get-orderbook

        :param pair: the trading pair to query
        :param depth: the price levels depth to query (max: 100 default: 20)
        :return: a dict contains asks and bids data
        """
        if depth > 100 or depth < 20:
            raise Invalid("depth must be between 20 and 100")

        return self._send_request(
            "public", "GET", f"markets/{pair}/orderbook", {"depth": depth}
        )

    def get_recent_trades(
        self, pair, limit=constants.DEFAULT_LIMIT, start_time=None, end_time=None
    ) -> ListOfDicts:
        """
        https://docs.ftx.com/#get-trades

        :param pair: the trading pair to query
        :param limit: the records limit to query
        :param start_time: the target period after an Epoch time in seconds
        :param end_time: the target period before an Epoch time in seconds
        :return: a list contains all completed orders in exchange
        """
        query = helpers.build_query(
            limit=limit, start_time=start_time, end_time=end_time
        )

        return self._send_request("public", "GET", f"markets/{pair}/trades", query)

    def get_k_line(
        self,
        pair,
        resolution=constants.DEFAULT_K_LINE_RESOLUTION,
        limit=constants.DEFAULT_LIMIT,
        start_time=None,
        end_time=None,
    ) -> ListOfDicts:
        """
        https://docs.ftx.com/#get-historical-prices

        :param pair: the trading pair to query
        :param resolution: the time period of K line in seconds
        :param limit: the records limit to query
        :param start_time: the target period after an Epoch time in seconds
        :param end_time: the target period before an Epoch time in seconds
        :return: a list contains all OHLC prices in exchange
        """
        if resolution not in constants.VALID_K_LINE_RESOLUTIONS:
            raise Invalid(
                f"resolution must be in {', '.join(constants.VALID_K_LINE_RESOLUTIONS)}"
            )

        query = {"resolution": resolution}

        query = helpers.build_query(
            query, limit=limit, start_time=start_time, end_time=end_time
        )

        return self._send_request("public", "GET", f"markets/{pair}/candles", query)

    def get_public_all_futures(self) -> ListOfDicts:
        """
        https://docs.ftx.com/#list-all-futures

        :return: a list contains all available futures
        """

        return self._send_request("public", "GET", f"/futures")

    def get_public_all_perpetual_futures(self) -> ListOfDicts:
        """
        https://docs.ftx.com/#list-all-futures

        :return: a list contains all available perpetual futures
        """
        return [
            future for future in self.get_public_all_futures() if future["perpetual"]
        ]

    def get_public_single_future(self, pair):
        """
        https://docs.ftx.com/#get-future

        :param pair: the trading pair to query
        :return: a list contains single future info
        """

        return self._send_request("public", "GET", f"futures/{pair.upper()}")

    def get_public_future_stats(self, pair):
        """
        https://docs.ftx.com/#get-future-stats

        :param pair: the trading pair to query
        :return: a list contains stats of a future
        """

        return self._send_request("public", "GET", f"futures/{pair.upper()}/stats")

    def get_public_all_funding_rates(self):
        """
        https://docs.ftx.com/#get-funding-rates

        :return: a list contains all funding rate of perpetual futures
        """

        return self._send_request("public", "GET", f"funding_rates")

    # TODO: Note that this only applies to index futures, e.g. ALT/MID/SHIT/EXCH/DRAGON.
    def get_public_etf_future_index(self, index):
        """
        https://docs.ftx.com/#get-index-weights

        :param index: the trading index to query
        :return: a list contains all component coins in ETF Future
        """

        return self._send_request("public", "GET", f"indexes/{index}/weights")

    def get_public_all_expired_futures(self):
        """
        https://docs.ftx.com/#get-expired-futures

        :return: a list contains all expired futures
        """

        return self._send_request("public", "GET", f"expired_futures")

    def get_public_index_k_line(
        self, index, resolution=14400, limit=20, start_time=None, end_time=None
    ):
        """
        https://docs.ftx.com/#get-historical-index

        :param index: the trading index to query
        :param resolution: the time period of K line in seconds
        :param limit: the records limit to query
        :param start_time: the target period after an Epoch time in seconds
        :param end_time: the target period before an Epoch time in seconds
        :return: a list contains all OHLC prices of etf index in exchange
        """

        query = {
            "resolution": resolution,
            "limit": limit,
        }

        if start_time is not None:
            query.update(
                {
                    "start_time": start_time,
                }
            )

        if end_time is not None:
            query.update({"end_time": end_time})

        return self._send_request("public", "GET", f"indexes/{index}/candles", query)

    # Private API

    def get_private_account_information(self):
        """
        https://docs.ftx.com/#get-account-information

        :return: a dict contains all personal profile and positions information
        """

        return self._send_request("private", "GET", f"account")

    def get_private_account_positions(self, showAvgPrice=False):
        """
        https://docs.ftx.com/#get-positions

        :param showAvgPrice: display AvgPrice or not
        :return: a dict contains all positions
        """

        return self._send_request(
            "private", "GET", f"positions", {"showAvgPrice": showAvgPrice}
        )

    def get_private_all_subaccounts(self):
        """
        https://docs.ftx.com/#get-all-subaccounts

        :return: a list contains all subaccounts
        """

        return self._send_request("private", "GET", f"subaccounts")

    def get_private_subaccount_balances(self, name):
        """
        https://docs.ftx.com/#get-subaccount-balances

        :param name: the subaccount name to query
        :return: a list contains subaccount balances
        """

        return self._send_request("private", "GET", f"subaccounts/{name}/balances")

    def get_private_wallet_coins(self):
        """
        https://docs.ftx.com/#get-coins

        :return: a list contains all coins in wallet
        """

        return self._send_request("private", "GET", f"wallet/coins")

    def get_private_wallet_balances(self):
        """
        https://docs.ftx.com/#get-balances

        :return: a list contains current account balances
        """

        return self._send_request("private", "GET", f"wallet/balances")

    def get_private_wallet_single_balance(self, coin):
        """
        https://docs.ftx.com/#get-balances

        :params coin: the coin of balance
        :return: a list contains current account single balance
        """

        balance_coin = [
            balance
            for balance in self.get_private_wallet_balances()
            if balance["coin"] == coin
        ]

        if balance_coin == []:
            return None
        return balance_coin[0]

    def get_private_wallet_all_balances(self):
        """
        https://docs.ftx.com/#get-balances-of-all-accounts

        :return: a list contains all accounts balances
        """

        return self._send_request("private", "GET", f"wallet/all_balances")

    def get_private_wallet_deposit_address(self, coin, chain):
        """
        https://docs.ftx.com/#get-deposit-address

        :param currency: the specific coin to endpoint
        :param chain: the blockchain deposit from, should be 'omni' or 'erc20', 'trx' or 'sol'
        :return: a list contains deposit address
        """

        return self._send_request(
            "private",
            "GET",
            f"wallet/deposit_address/{coin.upper()}",
            {"method": chain},
        )

    def get_private_wallet_deposit_history(
        self, limit=20, start_time=None, end_time=None
    ):
        """
        https://docs.ftx.com/#get-deposit-history

        :param limit: the records limit to query
        :param start_time: the target period after an Epoch time in seconds
        :param end_time: the target period before an Epoch time in seconds
        :return: a list contains deposit history
        """

        query = {
            "limit": limit,
        }

        if start_time is not None:
            query.update(
                {
                    "start_time": start_time,
                }
            )

        if end_time is not None:
            query.update({"end_time": end_time})

        return self._send_request("private", "GET", f"wallet/deposits", query)

    def get_private_wallet_withdraw_history(
        self, limit=20, start_time=None, end_time=None
    ):
        """
        https://docs.ftx.com/#get-withdrawal-history

        :param limit: the records limit to query
        :param start_time: the target period after an Epoch time in seconds
        :param end_time: the target period before an Epoch time in seconds
        :return: a list contains withdraw history
        """

        query = {
            "limit": limit,
        }

        if start_time is not None:
            query.update(
                {
                    "start_time": start_time,
                }
            )

        if end_time is not None:
            query.update({"end_time": end_time})

        return self._send_request("private", "GET", f"wallet/withdrawals", query)

    def get_private_wallet_airdrops(self, limit=20, start_time=None, end_time=None):
        """
        https://docs.ftx.com/#get-airdrops

        :param limit: the records limit to query
        :param start_time: the target period after an Epoch time in seconds
        :param end_time: the target period before an Epoch time in seconds
        :return: a list contains airdrop history
        """

        query = {
            "limit": limit,
        }

        if start_time is not None:
            query.update(
                {
                    "start_time": start_time,
                }
            )

        if end_time is not None:
            query.update({"end_time": end_time})

        return self._send_request("private", "GET", f"wallet/airdrops", query)

    def get_private_funding_payments(self, coin=None, start_time=None, end_time=None):
        """
        https://docs.ftx.com/#funding-payments

        :param coin: the trading coin to query
        :param start_time: the target period after an Epoch time in seconds
        :param end_time: the target period before an Epoch time in seconds
        :return: a list contains all funding payments of perpetual future
        """

        query = {}

        if start_time is not None:
            query.update(
                {
                    "start_time": start_time,
                }
            )

        if end_time is not None:
            query.update(
                {
                    "end_time": end_time,
                }
            )

        if coin is not None:
            query.update({"future": coin.upper() + "-PERP"})

        return self._send_request("private", "GET", f"funding_payments", query)

    def get_private_bills(
        self, pair, limit=20, start_time=None, end_time=None, order=None, _orderId=None
    ):
        """
        https://docs.ftx.com/#fills

        :param pair: the trading pair to query
        :param limit: the records limit to query
        :param start_time: the target period after an Epoch time in seconds
        :param end_time: the target period before an Epoch time in seconds
        :param order: sort the bill by created time, default is descending, supply 'asc' to receive fills in ascending order of time
        :param _orderId: the id of the order
        :return: a list contains all bills
        """

        query = {
            "market": pair,
            "limit": limit,
        }

        if start_time is not None:
            query.update(
                {
                    "start_time": start_time,
                }
            )

        if end_time is not None:
            query.update(
                {
                    "end_time": end_time,
                }
            )

        if order is not None:
            query.update(
                {
                    "order": order,
                }
            )

        if _orderId is not None:
            query.update({"orderId": _orderId})

        return self._send_request("private", "GET", f"fills", query)

    def get_private_open_orders(self, pair=None):
        """
        https://docs.ftx.com/?python#get-open-orders

        :param pair: the trading pair to query
        :return: a list contains all open orders
        """
        query = {}

        if pair is not None:
            query["market"] = pair

        return self._send_request("private", "GET", f"orders", query)

    def get_private_order_history(
        self, pair=None, start_time=None, end_time=None, limit=None
    ):
        """
        https://docs.ftx.com/?python#get-order-history

        :param pair: the trading pair to query
        :param start_time: the target period after an Epoch time in seconds
        :param end_time: the target period before an Epoch time in seconds
        :param limit: the records limit to query
        :return: a list contains all history orders
        """

        query = {}

        if pair is not None:
            query.update(
                {
                    "market": pair,
                }
            )

        if start_time is not None:
            query.update(
                {
                    "start_time": start_time,
                }
            )

        if end_time is not None:
            query.update(
                {
                    "end_time": end_time,
                }
            )

        if limit is not None:
            query.update({"limit": limit})

        return self._send_request("private", "GET", f"orders/history", query)

    def get_private_open_trigger_orders(self, pair=None, _type=None):
        """
        https://docs.ftx.com/?python#get-open-trigger-orders

        :param pair: the trading pair to query
        :param _type: type of trigger order, should only be stop, trailing_stop, or take_profit
        :return: a list contains all open trigger orders
        """

        query = {}

        if pair is not None:
            query.update(
                {
                    "market": pair,
                }
            )

        if _type is not None:
            query.update({"type": _type})

        return self._send_request("private", "GET", f"conditional_orders", query)

    def get_private_trigger_order_triggers(self, _orderId):
        """
        https://docs.ftx.com/?python#get-open-trigger-orders

        :param _orderId: the id of the order
        :return: a list contains trigger order triggers
        """

        return self._send_request(
            "private", "GET", f"conditional_orders/{_orderId}/triggers"
        )

    def get_private_trigger_order_history(
        self,
        pair=None,
        start_time=None,
        end_time=None,
        side=None,
        _type=None,
        _orderType=None,
        limit=None,
    ):
        """
        https://docs.ftx.com/?python#get-trigger-order-history

        :param pair: the trading pair to query
        :param start_time: the target period after an Epoch time in seconds
        :param end_time: the target period before an Epoch time in seconds
        :param side: the trading side, should only be buy or sell
        :param _type: type of trigger order, should only be stop, trailing_stop, or take_profit
        :param _orderType: the order type, should only be limit or market
        :param limit: the records limit to query
        :return: a list contains all history trigger orders
        """

        query = {}

        if pair is not None:
            query.update(
                {
                    "market": pair,
                }
            )

        if start_time is not None:
            query.update(
                {
                    "start_time": start_time,
                }
            )

        if end_time is not None:
            query.update(
                {
                    "end_time": end_time,
                }
            )

        if side is not None:
            query.update(
                {
                    "side": side,
                }
            )

        if _type is not None:
            query.update(
                {
                    "type": _type,
                }
            )

        if _orderType is not None:
            query.update(
                {
                    "orderType": _orderType,
                }
            )

        if limit is not None:
            query.update({"limit": limit})

        return self._send_request(
            "private", "GET", f"conditional_orders/history", query
        )

    def get_private_order_status(self, orderId):
        """
        https://docs.ftx.com/#get-order-status

        :param orderId: the order ID
        :return a list contains status of the order
        """

        return self._send_request("private", "GET", f"orders/{orderId}")

    def get_public_order_status_by_clientId(self, clientId):
        """
        https://docs.ftx.com/#get-order-status-by-client-id

        :param clientOrderId: the client order ID
        :return a list contains status of the order
        """

        return self._send_request("private", "GET", f"orders/by_client_id/{clientId}")

    # Private API (Write)
    def set_private_create_subaccount(self, name):
        """
        https://docs.ftx.com/?python#create-subaccount

        :param name: new subaccount name
        :return: a list contains new subaccount info
        """

        return self._send_request("private", "POST", f"subaccounts", {"nickname": name})

    def set_private_change_subaccount_name(self, name, newname):
        """
        https://docs.ftx.com/?python#change-subaccount-name

        :param name: current subaccount name
        :param newname: new nickname of subaccount
        :return: a list contains status
        """

        query = {"nickname": name, "newNickname": newname}

        return self._send_request("private", "POST", f"subaccounts/update_name", query)

    def set_private_delete_subaccount(self, name):
        """
        https://docs.ftx.com/?python#delete-subaccount

        :param name: the nickname wanna delete
        :return: a list contains status
        """

        return self._send_request(
            "private", "DELETE", f"subaccounts", {"nickname": name}
        )

    # TODO: Endpoint Error > Not allowed with internal-transfers-disabled permissions
    def set_private_transfer_balances(self, coin, size, source, destination):
        """
        https://docs.ftx.com/?python#transfer-between-subaccounts

        :param coin: the transfering coin to query
        :param size: the size wanna transfer to query
        :param source: the name of the source subaccount. Use null or 'main' for the main account
        :param destination: the name of the destination subaccount. Use null or 'main' for the main account
        :return: a list contains status
        """

        query = {
            "coin": coin,
            "size": size,
            "source": source,
            "destination": destination,
        }

        return self._send_request("private", "POST", f"subaccounts/transfer", query)

    def set_private_change_account_leverage(self, leverage):
        """
        https://docs.ftx.com/?python#change-account-leverage

        :param leverage: desired acccount-wide leverage setting
        :return: a list contains status
        """

        return self._send_request(
            "private", "POST", f"account/leverage", {"leverage": leverage}
        )

    def set_private_create_order(
        self,
        pair,
        side,
        price,
        _type,
        size,
        reduceOnly=False,
        ioc=False,
        postOnly=False,
        clientId=None,
    ):
        """
        https://docs.ftx.com/?python#place-order

        :param pair: the trading pair to query. e.g. "BTC/USD" for spot, "XRP-PERP" for futures
        :param side: the trading side, should only be buy or sell
        :param price: the order price, Send null for market orders.
        :param _type: type of order, should only be limit or market
        :param size: the amount of the order for the trading pair
        :param reduceOnly: only reduce position, default is false (future only)
        :param ioc: immediate or cancel order, default is false
        :param postOnly: always maker, default is false
        :param clientId: client order id
        :return: a list contains all info about new order
        """

        query = {
            "market": pair,
            "side": side,
            "price": price,
            "type": _type,
            "size": size,
            "reduceOnly": reduceOnly,
            "ioc": ioc,
            "postOnly": postOnly,
        }

        if clientId is not None:
            query.update({"clientId": clientId})

        return self._send_request("private", "POST", f"orders", query)

    def set_private_create_trigger_order(
        self,
        pair,
        side,
        triggerPrice,
        size,
        orderPrice=None,
        _type="stop",
        reduceOnly=False,
        retryUntilFilled=True,
    ):
        """
        https://docs.ftx.com/?python#place-trigger-order

        :param pair: the trading pair to query. e.g. "BTC/USD" for spot, "XRP-PERP" for futures
        :param side: the trading side, should only be buy or sell
        :param triggerPrice: the order trigger price
        :param orderPrice: the order price, order type is limit if this is specified; otherwise market
        :param size: the amount of the order for the trading pair
        :param _type: type of order, should only be stop, trailingStop or takeProfit, default is stop
        :param reduceOnly: only reduce position, default is false (future only)
        :param retryUntilFilled: Whether or not to keep re-triggering until filled. optional, default true for market orders
        :return: a list contains all info about new trigger order
        """

        query = {
            "market": pair,
            "side": side,
            "triggerPrice": triggerPrice,
        }

        if orderPrice is not None:
            query.update(
                {
                    "orderPrice": orderPrice,
                }
            )

        query.update(
            {
                "size": size,
                "type": _type,
                "reduceOnly": reduceOnly,
                "retryUntilFilled": retryUntilFilled,
            }
        )

        return self._send_request("private", "POST", f"conditional_orders", query)

    # TODO: Either price or size must be specified
    def set_private_modify_order(self, orderId, price=None, size=None, clientId=None):
        """
        https://docs.ftx.com/#modify-order

        Please note that the order's queue priority will be reset, and the order ID of the modified order will be different from that of the original order. Also note: this is implemented as cancelling and replacing your order. There's a chance that the order meant to be cancelled gets filled and its replacement still gets placed.

        :param orderId: the order ID
        :param price: the modify price
        :param size: the modify amount of the order for the trading pair
        :param clientId: client order id
        :return a list contains all info after modify the order
        """

        query = {}

        if price is not None:
            query.update = {
                "price": price,
            }

        if size is not None:
            query.update = {
                "size": size,
            }

        if clientId is not None:
            query.update({"clientId": clientId})

        return self._send_request("private", "POST", f"orders/{orderId}/modify", query)

    # TODO: Either price or size must be specified
    def set_private_modify_order_by_clientId(
        self, clientOrderId, price=None, size=None, clientId=None
    ):
        """
        https://docs.ftx.com/#modify-order-by-client-id

        Please note that the order's queue priority will be reset, and the order ID of the modified order will be different from that of the original order. Also note: this is implemented as cancelling and replacing your order. There's a chance that the order meant to be cancelled gets filled and its replacement still gets placed.

        :param clientOrderId: the client order ID
        :param price: the modify price
        :param size: the modify amount of the order for the trading pair
        :param clientId: client order id
        :return a list contains all info after modify the order
        """

        query = {}

        if price is not None:
            query.update = {
                "price": price,
            }

        if size is not None:
            query.update = {
                "size": size,
            }

        if clientId is not None:
            query.update({"clientId": clientId})

        return self._send_request(
            "private", "POST", f"orders/by_client_id/{clientOrderId}/modify", query
        )

    def set_private_modify_trigger_order(
        self, orderId, _type, size, triggerPrice=None, orderPrice=None, trailValue=None
    ):
        """
        https://docs.ftx.com/#modify-trigger-order

        Please note that the order ID of the modified order will be different from that of the original order.


        :param orderId: the order ID
        :param _type: type of order, should only be stop, trailingStop or takeProfit, default is stop
        :param size: the modify amount of the order for the trading pair
        :param triggerPrice: the modify trigger price
        :param orderPrice: the order price, order type is limit if this is specified; otherwise market
        :param trailValue: negative for sell orders; positive for buy orders
        :return a list contains all info after modify the trigger order
        """

        if _type == "stop" or _type == "takeProfit":
            query = {
                "size": size,
                "triggerPrice": triggerPrice,
            }
            if orderPrice is not None:
                query.update({"orderPrice": orderPrice})
        else:
            query = {"size": size, "trailValue": trailValue}

        return self._send_request(
            "private", "POST", f"conditional_orders/{orderId}/modify", query
        )

    def set_private_cancel_order(self, orderId):
        """
        https://docs.ftx.com/#cancel-order

        :param orderId: the order ID
        :return a list contains result
        """

        return self._send_request("private", "DELETE", f"orders/{orderId}")

    def set_private_cancel_order_by_clientID(self, clientId):
        """
        https://docs.ftx.com/#cancel-order-by-client-id

        :param clientOrderId: the client order ID
        :return a list contains result
        """

        return self._send_request(
            "private", "DELETE", f"orders/by_client_id/{clientId}"
        )

    def set_private_cancel_trigger_order(self, orderId):
        """
        https://docs.ftx.com/#cancel-open-trigger-order

        :param orderId: the order ID
        :return a list contains result
        """

        return self._send_request("private", "DELETE", f"conditional_orders/{orderId}")

    def set_private_cancel_all_order(
        self, pair=None, conditionalOrdersOnly=False, limitOrdersOnly=False
    ):
        """
        https://docs.ftx.com/#cancel-all-orders

        :param pair: the trading pair to query.
        :param conditionalOrdersOnly: default False.
        :param limitOrdersOnly: default False.
        :return a list contains result
        """
        if pair is not None:
            query = {
                "market": pair,
                "conditionalOrdersOnly": conditionalOrdersOnly,
                "limitOrdersOnly": limitOrdersOnly,
            }
        else:
            query = {
                "conditionalOrdersOnly": conditionalOrdersOnly,
                "limitOrdersOnly": limitOrdersOnly,
            }

        return self._send_request("private", "DELETE", f"orders", query)

    # SRM Stake

    def get_private_srm_stake_history(self):
        """
        https://docs.ftx.com/#get-stakes

        :return a list contains srm stake history
        """

        return self._send_request("private", "GET", f"srm_stakes/stakes")

    def get_private_srm_unstake_history(self):
        """
        https://docs.ftx.com/#unstake-request

        :return a list contains srm unstake history
        """

        return self._send_request("private", "GET", f"srm_stakes/unstake_requests")

    def get_private_srm_stake_balances(self):
        """
        https://docs.ftx.com/#get-stake-balances

        :return a list contains actively staked, scheduled for unstaking and lifetime rewards balances
        """

        return self._send_request("private", "GET", f"srm_stakes/balances")

    def get_private_srm_stake_rewards_history(self):
        """
        https://docs.ftx.com/#get-staking-rewards

        :return a list contains srm staking rewards
        """

        return self._send_request("private", "GET", f"srm_stakes/staking_rewards")

    def set_private_srm_unstake(self, coin, size):
        """
        https://docs.ftx.com/#unstake-request-2

        :param coin: the staking coin to query
        :param size: the amount of the request for the stake coin
        :return a list contains result
        """

        query = {"coin": coin, "size": size}

        return self._send_request(
            "private", "POST", f"srm_stakes/unstake_requests", query
        )

    def set_private_cancel_srm_unstake(self, stakeId):
        """
        https://docs.ftx.com/#cancel-unstake-request

        :param stakeId: the id of staking request
        :return a list contains result
        """

        return self._send_request(
            "private", "DELETE", f"srm_stakes/unstake_requests/{stakeId}"
        )

    def set_private_srm_stake(self, coin, size):
        """
        https://docs.ftx.com/#stake-request

        :param coin: the staking coin to query
        :param size: the amount of the request for the stake coin
        :return a list contains result
        """

        query = {"coin": coin, "size": size}

        return self._send_request("private", "POST", f"srm_stakes/stakes", query)

    def get_private_margin_lending_rates(self):
        """
        https://docs.ftx.com/#get-lending-rates
        :return a list contains lending rates (include estimate rates and previous rates)
        """

        return self._send_request("private", "GET", f"spot_margin/lending_rates")

    def set_private_margin_lending_offer(self, coin, size, rate):
        """
        https://docs.ftx.com/#submit-lending-offer
        :param coin: the lending coin to query
        :param size: the amount of the request for the lend coin (Cancel for 0)
        :param rate: the rate wanna offer
        :return a list contains result
        """

        query = {"coin": coin, "size": size, "rate": rate}

        return self._send_request("private", "POST", f"spot_margin/offers", query)
