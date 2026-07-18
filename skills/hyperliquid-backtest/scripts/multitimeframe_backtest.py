#!/usr/bin/env python3
"""
Hyperliquid Multi-Timeframe Backtester.

Ported from ClawdBot's hyperliquid_backtester_multitimeframe.py (VPS 31.97.49.240,
~/clawd/scripts/), preserving the original strategy logic (MA crossover, RSI mean
reversion) and output format so this continues the same historical result series
in data/backtests/. Runs against Hyperliquid's public testnet info API — no key
needed, no live orders are ever placed.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hyperliquid_client import HyperliquidAPI
from risk_manager import kelly_size

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SKILL_ROOT = Path(__file__).parent.parent


class MultiTimeframeBacktester:
    def __init__(self, results_dir: Path = None):
        self.api = HyperliquidAPI(testnet=True)
        self.results_dir = results_dir or (SKILL_ROOT / "data" / "backtests")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.timeframes = ["5m", "15m", "1h", "4h", "1d"]

    def fetch_data(self, symbol, timeframe, days=30):
        logger.info(f"Fetching {symbol} {timeframe} data ({days} days)")
        end_time = int(datetime.now().timestamp() * 1000)

        days = {
            "5m": min(days, 7),
            "15m": min(days, 14),
            "1h": min(days, 30),
            "4h": min(days, 60),
            "1d": min(days, 365),
        }.get(timeframe, days)

        start_time = end_time - (days * 24 * 60 * 60 * 1000)
        candles = self.api.get_candles(symbol, timeframe, start_time, end_time)
        if not candles:
            logger.warning(f"No data for {symbol} {timeframe}")
            return None
        logger.info(f"Fetched {len(candles)} candles for {symbol} {timeframe}")
        return candles

    @staticmethod
    def calculate_ma(prices, period):
        if len(prices) < period:
            return prices[-1] if prices else 0
        return sum(prices[-period:]) / period

    @staticmethod
    def calculate_rsi(prices, period=14):
        if len(prices) < period + 1:
            return 50
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [abs(d) if d < 0 else 0 for d in deltas]
        avg_gains = sum(gains[:period]) / period
        avg_losses = sum(losses[:period]) / period
        for i in range(period, len(gains)):
            avg_gains = (avg_gains * (period - 1) + gains[i]) / period
            avg_losses = (avg_losses * (period - 1) + losses[i]) / period
        if avg_losses == 0:
            return 100
        rs = avg_gains / avg_losses
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _summarize(trades):
        closed = [t for t in trades if "pnl" in t]
        winning = [t for t in closed if t["pnl"] > 0]
        losing = [t for t in closed if t["pnl"] <= 0]
        total_pnl = sum(t["pnl"] for t in closed)
        avg_win = sum(t["pnl"] for t in winning) / len(winning) if winning else 0
        avg_loss = abs(sum(t["pnl"] for t in losing) / len(losing)) if losing else 0
        return {
            "trades": len(closed),
            "win_rate": (len(winning) / len(closed) * 100) if closed else 0,
            "total_return": total_pnl,
            "avg_trade": total_pnl / len(closed) if closed else 0,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
        }

    def backtest_ma_crossover(self, candles, fast_period=9, slow_period=21):
        closes = [float(c["c"]) for c in candles]
        trades, position, entry_price = [], None, 0
        for i in range(slow_period, len(closes)):
            price = closes[i]
            fast_ma = self.calculate_ma(closes[: i + 1], fast_period)
            slow_ma = self.calculate_ma(closes[: i + 1], slow_period)
            if fast_ma > slow_ma and position is None:
                position, entry_price = "long", price
                trades.append({"type": "buy", "price": price, "index": i})
            elif fast_ma < slow_ma and position == "long":
                pnl = (price - entry_price) / entry_price * 100
                trades.append({"type": "sell", "price": price, "pnl": pnl, "index": i})
                position = None
        if position == "long":
            pnl = (closes[-1] - entry_price) / entry_price * 100
            trades.append({"type": "sell", "price": closes[-1], "pnl": pnl, "index": len(closes) - 1})
        return self._summarize(trades)

    def backtest_rsi_mean_reversion(self, candles, rsi_period=14, oversold=30, overbought=70):
        closes = [float(c["c"]) for c in candles]
        trades, position, entry_price = [], None, 0
        for i in range(rsi_period + 1, len(closes)):
            rsi = self.calculate_rsi(closes[: i + 1], rsi_period)
            price = closes[i]
            if rsi < oversold and position is None:
                position, entry_price = "long", price
                trades.append({"type": "buy", "price": price, "rsi": rsi})
            elif position == "long" and rsi > 50:
                pnl = (price - entry_price) / entry_price * 100
                trades.append({"type": "sell", "price": price, "pnl": pnl})
                position = None
        if position == "long":
            pnl = (closes[-1] - entry_price) / entry_price * 100
            trades.append({"type": "sell", "price": closes[-1], "pnl": pnl})
        return self._summarize(trades)

    def run_timeframe_comparison(self, symbols=("BTC", "ETH", "SOL")):
        all_results = []
        for symbol in symbols:
            logger.info(f"Testing {symbol} across all timeframes")
            for timeframe in self.timeframes:
                candles = self.fetch_data(symbol, timeframe)
                if not candles or len(candles) < 50:
                    logger.warning(f"Insufficient data for {symbol} {timeframe}")
                    continue
                ma_results = self.backtest_ma_crossover(candles)
                rsi_results = self.backtest_rsi_mean_reversion(candles)
                all_results.append(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "data_points": len(candles),
                        "ma_crossover": ma_results,
                        "rsi_mean_reversion": rsi_results,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                logger.info(
                    f"{timeframe}: MA {ma_results['total_return']:+.2f}% "
                    f"({ma_results['trades']}t) | RSI {rsi_results['total_return']:+.2f}% "
                    f"({rsi_results['trades']}t)"
                )

        best_combinations = self.find_best_combinations(all_results)

        # Half-Kelly sizing suggestion for the #1 combination (bankroll assumed $1000, informational only)
        if best_combinations:
            top = best_combinations[0]
            top["kelly_suggested_size_usd"] = kelly_size(
                win_rate=top["win_rate"] / 100,
                avg_win=top.get("avg_win", 0),
                avg_loss=top.get("avg_loss", 0),
                bankroll=1000,
                fraction=0.5,
                max_size=200,
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"multitimeframe_{timestamp}.json"
        final_output = {
            "summary": best_combinations,
            "all_results": all_results,
            "timestamp": datetime.now().isoformat(),
        }
        with open(results_file, "w") as f:
            json.dump(final_output, f, indent=2)

        logger.info("BEST PERFORMING COMBINATIONS:")
        for combo in best_combinations[:5]:
            logger.info(f"{combo['symbol']} {combo['timeframe']} - {combo['strategy']}: {combo['return']:+.2f}%")
        logger.info(f"Results saved to: {results_file}")
        return final_output

    @staticmethod
    def find_best_combinations(results):
        combinations = []
        for r in results:
            for strat_key, strat_name in [("ma_crossover", "MA Crossover"), ("rsi_mean_reversion", "RSI Mean Reversion")]:
                s = r[strat_key]
                combinations.append(
                    {
                        "symbol": r["symbol"],
                        "timeframe": r["timeframe"],
                        "strategy": strat_name,
                        "return": s["total_return"],
                        "trades": s["trades"],
                        "win_rate": s["win_rate"],
                        "avg_win": s.get("avg_win", 0),
                        "avg_loss": s.get("avg_loss", 0),
                    }
                )
        combinations.sort(key=lambda x: x["return"], reverse=True)
        return combinations

    def format_discord_summary(self, results):
        summary = results["summary"][:5]
        messages = ["## \U0001F4CA Multi-Timeframe Backtest Results\n", "**\U0001F3C6 Top 5 Performing Combinations:**\n"]
        for i, combo in enumerate(summary, 1):
            emoji = "\U0001F947" if i == 1 else "\U0001F948" if i == 2 else "\U0001F949" if i == 3 else "\U0001F4C8"
            messages.append(
                f"{emoji} **{combo['symbol']}** {combo['timeframe']} - {combo['strategy']}\n"
                f"   Return: **{combo['return']:+.2f}%** | Trades: {combo['trades']} | Win Rate: {combo['win_rate']:.1f}%\n"
            )
        if summary and "kelly_suggested_size_usd" in summary[0]:
            messages.append(f"\n\U0001F4A1 Half-Kelly suggested size on top combo (assumes $1000 bankroll): ${summary[0]['kelly_suggested_size_usd']}")
        return "\n".join(messages)


def main():
    logger.info("Starting Multi-Timeframe Backtest Analysis...")
    backtester = MultiTimeframeBacktester()
    results = backtester.run_timeframe_comparison()

    discord_msg = backtester.format_discord_summary(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    discord_file = backtester.results_dir / f"discord_multitimeframe_{timestamp}.txt"
    with open(discord_file, "w") as f:
        f.write(discord_msg)
    logger.info(f"Discord summary saved to: {discord_file}")
    logger.info("Multi-timeframe analysis complete.")
    return results, discord_msg


if __name__ == "__main__":
    main()
