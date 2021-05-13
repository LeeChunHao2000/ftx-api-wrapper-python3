PUBLIC_API_URL = "https://ftx.com/api"
PRIVATE_API_URL = "https://ftx.com/api"
DEFAULT_LIMIT = None
DEFAULT_K_LINE_RESOLUTION = 14_400
VALID_K_LINE_RESOLUTIONS = (15, 60, 300, 900, 3600, 14400, 86400)
PRIVATE_ENDPOINTS = (
    "positions",
    "wallet",
    "account",
    "spot_margin",
    "srm_stakes",
    "orders",
    "conditional_orders",
    "leverage",
    "subaccounts",
    "fills",
    "funding_payments",
)
VALID_CHAINS = ("omni", "erc20", "trx", "sol", "bep2")
RATE_LIMIT_PER_SECOND = 30
