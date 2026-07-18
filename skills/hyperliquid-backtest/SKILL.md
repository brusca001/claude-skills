---
name: hyperliquid-backtest
description: Runs a multi-timeframe backtest (MA crossover + RSI mean reversion, across 5m/15m/1h/4h/1d on BTC/ETH/SOL) against Hyperliquid's public testnet data, reports the top combinations to Discord, and suggests a half-Kelly position size for the best one. Usage — /hyperliquid-backtest, or "run the hyperliquid backtest"
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

Runs daily via a `/schedule` cloud routine (not `/loop` — this needs to fire even when the laptop is asleep). The routine prompt clones this skill's source (from whatever repo it's pushed to), runs `multitimeframe_backtest.py`, and posts the result via `report.py`. `DISCORD_WEBHOOK_URL` is configured as an env var on the routine itself, not read from this local `.env`.

## Notes / provenance

- `scripts/hyperliquid_client.py` — extracted from the original ClawdBot script's inline `HyperliquidAPI` class, unchanged.
- `scripts/risk_manager.py` — Kelly-sizing formula adapted from `ai-contrarian-bot/scripts/risk_manager.py` (the full circuit-breaker/exposure-tracking machinery from that project isn't relevant here since this is backtest-only, not live trading).
- `scripts/multitimeframe_backtest.py` — same MA/RSI strategy logic as the VPS original, refactored into smaller functions and extended to track avg_win/avg_loss (needed for Kelly sizing) and emit the Kelly suggestion.
- This replaces the retired `eth-15-strategy`, `sol-rsi-trader-bot`, `polymarket-copy-trader`, and `ETH-PERP 3x Leverage Bot` — none of those are ported; this is backtesting only, no bot places trades.
