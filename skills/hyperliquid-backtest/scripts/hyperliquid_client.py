"""Minimal Hyperliquid public info-endpoint client. No API key needed for market data."""

import json
import logging
import ssl
import urllib.request

logger = logging.getLogger(__name__)

try:
    import certifi

    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = None


class HyperliquidAPI:
    def __init__(self, testnet: bool = True):
        self.base_url = "https://api.hyperliquid-testnet.xyz" if testnet else "https://api.hyperliquid.xyz"
        self.info_url = f"{self.base_url}/info"

    def get_candles(self, coin: str, interval: str = "1h", start_time: int = None, end_time: int = None):
        """Fetch candle data. start_time/end_time are ms epoch."""
        payload = {
            "type": "candleSnapshot",
            "req": {"coin": coin, "interval": interval, "startTime": start_time, "endTime": end_time},
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.info_url, data=data, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=30, context=_SSL_CONTEXT) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Error fetching candles for {coin} {interval}: {e}")
            return []
