#!/usr/bin/env python3
"""
Cloud path entry point: reads candle data already fetched via the n8n
get_hyperliquid_candles MCP tool (this sandbox blocks direct calls to
api.hyperliquid.xyz), runs the same MA/RSI backtest math as the local path,
and writes the same output files.

Usage:
    python3 compute_from_prefetched.py candles.json

candles.json shape:
    {"BTC": {"5m": [...], "15m": [...], "1h": [...], "4h": [...], "1d": [...]},
     "ETH": {...}, "SOL": {...}}
Each candle list is exactly what Hyperliquid's /info candleSnapshot endpoint
returns (list of {"t":..., "o":..., "h":..., "l":..., "c":..., "v":...} objects).
Timeframes/symbols with no data or an empty list are skipped gracefully.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from multitimeframe_backtest import MultiTimeframeBacktester


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 compute_from_prefetched.py <candles.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    backtester = MultiTimeframeBacktester()
    results = backtester.run_from_prefetched(data)

    discord_msg = backtester.format_discord_summary(results)
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    discord_file = backtester.results_dir / f"discord_multitimeframe_{timestamp}.txt"
    with open(discord_file, "w") as f:
        f.write(discord_msg)

    print(f"Discord-format summary saved to: {discord_file}")
    print(discord_msg)
    return results, discord_msg


if __name__ == "__main__":
    main()
