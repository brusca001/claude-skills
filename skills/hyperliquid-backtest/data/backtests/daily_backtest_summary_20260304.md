# Daily Hyperliquid Backtest Summary
**Date:** Wednesday, March 4th, 2026 @ 1:00 AM UTC

## Status: ❌ FAILED

### Root Cause
Hyperliquid API returning **HTTP 502 Bad Gateway** errors across all requests.

### Scope
- **Timeframes:** 5m, 15m, 1h, 4h, 1d
- **Assets:** BTC, ETH, SOL
- **Data Window:** 30 days historical

### Results
- **Data Fetched:** 0 / 15 attempts (0%)
- **Backtest Executed:** No (insufficient data)
- **Results File:** `/home/node/clawd/data/backtests/multitimeframe_20260304_010008.json` (empty)

### Attempted Message Target
Discord Channel: `1468801291164581979` (delivery unavailable in current config)

### Next Steps
- Automatic retry on next scheduled run (24h)
- Monitor Hyperliquid API status
- No action required if API recovers

---
*Script: `/home/node/clawd/scripts/hyperliquid_backtester_multitimeframe.py`*
