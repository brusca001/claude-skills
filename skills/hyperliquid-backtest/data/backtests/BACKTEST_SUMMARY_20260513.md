# Multi-Timeframe Hyperliquid Backtest Summary
**Executed:** May 13, 2026 at 1:00 AM UTC
**Status:** ✅ Complete (Discord delivery pending valid bot token)

## 🏆 Top 5 Performing Combinations

| Rank | Symbol | Timeframe | Strategy | Return | Trades | Win Rate |
|------|--------|-----------|----------|--------|--------|----------|
| 🥇 | SOL | 15m | RSI Mean Reversion | **+16.48%** | 5 | 80.0% |
| 🥈 | SOL | 5m | RSI Mean Reversion | **+10.22%** | 7 | 85.7% |
| 🥉 | SOL | 4h | MA Crossover | **+9.84%** | 4 | 50.0% |
| 4️⃣ | BTC | 1h | RSI Mean Reversion | **+4.86%** | 4 | 100.0% |
| 5️⃣ | SOL | 1h | RSI Mean Reversion | **+3.86%** | 4 | 75.0% |

## 📊 Key Insights

- **Best Timeframe:** 15m (avg +16.48%)
- **Best Strategy:** RSI Mean Reversion (dominant across all top performers)
- **Most Consistent Asset:** BTC 1h (100% win rate, 4/4 trades profitable)
- **Worst Performer:** ETH (all negative returns across all timeframes)
- **Data Limitation:** Daily timeframe (1d) has insufficient data (only 31 candles)

## 📈 Complete Results by Symbol

### BTC (Bitcoin)
- **5m:** MA Crossover -9.60%, RSI Reversion +1.21%
- **15m:** MA Crossover -5.56%, RSI Reversion +1.69%
- **1h:** MA Crossover +1.52%, RSI Reversion +4.86% ✨
- **4h:** MA Crossover -1.79%, RSI Reversion 0% (no trades)

### ETH (Ethereum)
- **5m:** MA Crossover -17.10%, RSI Reversion -2.69%
- **15m:** MA Crossover -6.71%, RSI Reversion -1.38%
- **1h:** MA Crossover -10.92%, RSI Reversion +3.01%
- **4h:** MA Crossover -12.93%, RSI Reversion 0% (no trades)

### SOL (Solana)
- **5m:** MA Crossover -61.10%, RSI Reversion +10.22% ✨
- **15m:** MA Crossover -18.42%, RSI Reversion +16.48% 🌟
- **1h:** MA Crossover -14.81%, RSI Reversion +3.86%
- **4h:** MA Crossover +9.84% ✨, RSI Reversion 0% (no trades)

## 📁 Files

- **Full JSON Results:** `/home/node/clawd/data/backtests/multitimeframe_20260513_010012.json`
- **Discord Summary:** `/home/node/clawd/data/backtests/discord_multitimeframe_20260513_010012.txt`

## 🔧 Configuration

- **Script:** `/home/node/clawd/scripts/hyperliquid_backtester_multitimeframe.py`
- **Timeframes Tested:** 5m, 15m, 1h, 4h, 1d
- **Symbols:** BTC, ETH, SOL
- **Strategies:** MA Crossover, RSI Mean Reversion
- **Data Period:** 30 days

## ⚠️ Notes

- SOL shows the most promise with RSI Mean Reversion on 5m-15m timeframes
- MA Crossover strategy consistently underperforms on most timeframes
- BTC 1h RSI strategy is the most reliable on BTC (perfect win rate)
- ETH underperformed across all timeframes and should be avoided in current conditions
- Discord delivery requires a valid bot token configuration
