# Multi-Timeframe Hyperliquid Backtest Results
**Date:** Tuesday, July 14th, 2026 — 1:00 AM UTC

## 📊 Summary

### Top 5 Performing Combinations

| Rank | Symbol | Timeframe | Strategy | Return | Trades | Win Rate |
|------|--------|-----------|----------|--------|--------|----------|
| 🥇 | SOL | 1h | RSI Mean Reversion | **+15.20%** | 7 | 85.7% |
| 🥈 | BTC | 1h | RSI Mean Reversion | **+13.68%** | 8 | 87.5% |
| 🥉 | SOL | 1h | MA Crossover | **+11.26%** | 18 | 33.3% |
| 📈 | ETH | 15m | RSI Mean Reversion | **+9.89%** | 8 | 75.0% |
| 📈 | SOL | 4h | RSI Mean Reversion | **+6.90%** | 1 | 100.0% |

## Key Insights

- **Best timeframe:** 1h (avg +13.38%)
- **Best strategy:** RSI Mean Reversion (avg +11.42%)
- **Most consistent:** BTC (min +13.68%)

## Recommendation

The **1h timeframe with RSI Mean Reversion strategy** shows the strongest performance across multiple assets:
- SOL: +15.20% return
- BTC: +13.68% return
- Both maintain high win rates (85%+)

This strategy appears most suitable for mean reversion trades on liquid pairs with good data availability.

## Data Collection

- **Timeframes tested:** 5m, 15m, 1h, 4h, 1d
- **Symbols tested:** BTC, ETH, SOL
- **Data period:** 30 days (adjusted per timeframe)
- **Total candles processed:** ~16,000+

**Note:** Daily (1d) timeframe excluded due to insufficient historical data in 30-day period.

---
*Results saved to: `/home/node/clawd/data/backtests/multitimeframe_20260714_010029.json`*
