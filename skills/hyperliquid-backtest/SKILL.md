---
name: hyperliquid-backtest
description: Runs a multi-timeframe backtest (MA crossover + RSI mean reversion, across 5m/15m/1h/4h/1d on BTC/ETH/SOL) against Hyperliquid's public testnet data, reports the top combinations (Discord locally, real email via the n8n MCP connector in the cloud routine), and suggests a half-Kelly position size for the best one. Usage — /hyperliquid-backtest, or "run the hyperliquid backtest"
---

Ported from ClawdBot's `hyperliquid_backtester_multitimeframe.py` (VPS 31.97.49.240) — same strategy logic and output format, so `data/backtests/` is one continuous historical series (306 files pulled from the VPS archive, Feb 2026 → present, plus everything generated locally from here on).

## What it does

1. Fetches candle data from Hyperliquid's public testnet `info` endpoint for BTC/ETH/SOL across 5 timeframes — **no API key needed**, backtest-only, never places a live order.
2. Backtests two strategies per symbol/timeframe: MA crossover (9/21) and RSI mean reversion (30/70, exit at RSI 50).
3. Ranks all 30 combinations by return, saves the full result set to `data/backtests/multitimeframe_<timestamp>.json`.
4. Computes a half-Kelly suggested position size for the #1 combination (assumes $1000 bankroll, capped at $200 — informational only, not a live sizing recommendation).
5. Posts a Top-5 summary to Discord (or prints it if `DISCORD_WEBHOOK_URL` isn't set) and saves it to `data/backtests/discord_multitimeframe_<timestamp>.txt`.

## Running it

```bash
cd ~/.claude/skills/hyperliquid-backtest
python3 scripts/multitimeframe_backtest.py
```

This writes the JSON + Discord-text files locally. To actually post to Discord:

```bash
python3 scripts/multitimeframe_backtest.py && \
  python3 scripts/report.py "$(tail -n +1 data/backtests/discord_multitimeframe_*.txt | tail -30)"
```

Or, simpler — call `report.py` directly with the message from the last run's discord file.

## Env vars

See `.env.example`. Only `DISCORD_WEBHOOK_URL` is needed; everything else is a public, keyless API.

## Scheduling

Runs daily via a `/schedule` cloud routine (not `/loop` — this needs to fire even when the laptop is asleep).

**Cloud network limitation, and how it's solved:** this cloud sandbox's network egress policy blocks `api.hyperliquid.xyz`/`api.hyperliquid-testnet.xyz` and `discord.com` at the proxy/CONNECT level (confirmed via diagnostic) — only GitHub/PyPI/npm and MCP-connector traffic get through. Rather than wait for that to change, we route around it: an n8n workflow (`n8n/claude-mcp-tools.json`, imported into the user's own n8n instance at `n8n.srv988809.hstgr.cloud`, added as the **"Routines" custom MCP connector**, connector_uuid `523d0e56-2f6b-4449-8d38-94cfa94a9d80`) exposes two tools the cloud routine calls instead:
- **`get_hyperliquid_candles`** — n8n makes the actual HTTP call from its own unrestricted network, since n8n isn't inside Anthropic's sandbox.
- **`send_email`** — real SMTP send via n8n's `send-email-subworkflow.json`, not a Gmail draft.

**Cloud routine flow** (see the routine prompt on `claude.ai/code/routines` for the exact instructions given to the agent):
1. For each of BTC/ETH/SOL × 5m/15m/1h/4h/1d (15 calls total), call `get_hyperliquid_candles` with `startTime`/`endTime` computed the same way `fetch_data()` does locally: `endTime = now`, `startTime = endTime - days*86400000` where days = 7 (5m), 14 (15m), 30 (1h), 60 (4h), 365 (1d).
2. Assemble all 15 results into `{"BTC": {"5m": [...], ...}, "ETH": {...}, "SOL": {...}}` and write to a JSON file.
3. Run `python3 scripts/compute_from_prefetched.py <that file>` — this reuses the exact same MA/RSI/Kelly logic as the local path (`MultiTimeframeBacktester.run_from_prefetched()`), just skipping the network-fetching step, and writes the same output files.
4. Call `send_email` with the resulting Discord-format summary text.

## Local vs. cloud entry points

- **Local**: `scripts/multitimeframe_backtest.py` → `MultiTimeframeBacktester.run_timeframe_comparison()` — fetches its own data via direct HTTP (`hyperliquid_client.py`).
- **Cloud**: `scripts/compute_from_prefetched.py <candles.json>` → `MultiTimeframeBacktester.run_from_prefetched(data)` — takes already-fetched candle data (from the MCP tool), does zero network I/O itself. Both paths share the same strategy math (`_process_combo`, `backtest_ma_crossover`, `backtest_rsi_mean_reversion`, `_finalize`) so results are directly comparable and both append to the same `data/backtests/` historical series.

## Notes / provenance

- `scripts/hyperliquid_client.py` — extracted from the original ClawdBot script's inline `HyperliquidAPI` class, unchanged.
- `scripts/risk_manager.py` — Kelly-sizing formula adapted from `ai-contrarian-bot/scripts/risk_manager.py` (the full circuit-breaker/exposure-tracking machinery from that project isn't relevant here since this is backtest-only, not live trading).
- `scripts/multitimeframe_backtest.py` — same MA/RSI strategy logic as the VPS original, refactored into smaller functions and extended to track avg_win/avg_loss (needed for Kelly sizing) and emit the Kelly suggestion.
- This replaces the retired `eth-15-strategy`, `sol-rsi-trader-bot`, `polymarket-copy-trader`, and `ETH-PERP 3x Leverage Bot` — none of those are ported; this is backtesting only, no bot places trades.
