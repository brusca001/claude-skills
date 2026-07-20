#!/usr/bin/env python3
"""
Aggregate analysis across all historical multitimeframe_*.json backtest results.

A single day's top-5 is noisy — this looks at every recorded run to find which
symbol/timeframe/strategy combos are PERSISTENTLY good (frequently top-5, high
average return, low variance) vs. combos that only won once on a lucky day.

Usage:
    python3 analyze_history.py [--top N]
"""

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "backtests"


def load_all_runs():
    runs = []
    for f in sorted(DATA_DIR.glob("multitimeframe_*.json")):
        try:
            with open(f) as fh:
                data = json.load(fh)
            if "all_results" in data:
                runs.append((f.name, data))
        except (json.JSONDecodeError, KeyError):
            continue
    return runs


def aggregate(runs):
    """combo_key -> list of (return, win_rate, trades, was_top5, run_file)"""
    combos = defaultdict(list)
    for fname, data in runs:
        top5_keys = set()
        for combo in data.get("summary", [])[:5]:
            top5_keys.add((combo["symbol"], combo["timeframe"], combo["strategy"]))

        for r in data.get("all_results", []):
            for strat_field, strat_name in [("ma_crossover", "MA Crossover"), ("rsi_mean_reversion", "RSI Mean Reversion")]:
                s = r.get(strat_field)
                if not s:
                    continue
                key = (r["symbol"], r["timeframe"], strat_name)
                combos[key].append(
                    {
                        "return": s["total_return"],
                        "win_rate": s["win_rate"],
                        "trades": s["trades"],
                        "top5": key in top5_keys,
                        "run": fname,
                    }
                )
    return combos


def summarize(combos, min_appearances=5):
    rows = []
    for (symbol, timeframe, strategy), records in combos.items():
        if len(records) < min_appearances:
            continue
        returns = [r["return"] for r in records]
        top5_count = sum(1 for r in records if r["top5"])
        rows.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "strategy": strategy,
                "runs": len(records),
                "avg_return": statistics.mean(returns),
                "median_return": statistics.median(returns),
                "stdev_return": statistics.stdev(returns) if len(returns) > 1 else 0,
                "positive_rate": sum(1 for r in returns if r > 0) / len(returns) * 100,
                "top5_rate": top5_count / len(records) * 100,
                "avg_trades": statistics.mean(r["trades"] for r in records),
            }
        )
    return rows


def print_report(rows, top_n=10):
    print(f"Analyzed {len(rows)} symbol/timeframe/strategy combos with enough history.\n")

    print("=" * 100)
    print(f"TOP {top_n} BY AVERAGE RETURN")
    print("=" * 100)
    by_avg = sorted(rows, key=lambda r: r["avg_return"], reverse=True)[:top_n]
    for r in by_avg:
        print(
            f"{r['symbol']:5s} {r['timeframe']:4s} {r['strategy']:20s} "
            f"avg={r['avg_return']:+7.2f}% median={r['median_return']:+7.2f}% "
            f"stdev={r['stdev_return']:6.2f} pos_rate={r['positive_rate']:5.1f}% "
            f"top5_rate={r['top5_rate']:5.1f}% (n={r['runs']})"
        )

    print()
    print("=" * 100)
    print(f"TOP {top_n} BY CONSISTENCY (top5_rate, min avg_return > 0)")
    print("=" * 100)
    by_consistency = sorted(
        [r for r in rows if r["avg_return"] > 0], key=lambda r: r["top5_rate"], reverse=True
    )[:top_n]
    for r in by_consistency:
        print(
            f"{r['symbol']:5s} {r['timeframe']:4s} {r['strategy']:20s} "
            f"top5_rate={r['top5_rate']:5.1f}% avg={r['avg_return']:+7.2f}% "
            f"pos_rate={r['positive_rate']:5.1f}% stdev={r['stdev_return']:6.2f} (n={r['runs']})"
        )

    print()
    print("=" * 100)
    print(f"TOP {top_n} BY RISK-ADJUSTED (avg_return / stdev, min 10 runs, avg_return > 0)")
    print("=" * 100)
    by_sharpe_like = sorted(
        [r for r in rows if r["avg_return"] > 0 and r["stdev_return"] > 0 and r["runs"] >= 10],
        key=lambda r: r["avg_return"] / r["stdev_return"],
        reverse=True,
    )[:top_n]
    for r in by_sharpe_like:
        ratio = r["avg_return"] / r["stdev_return"]
        print(
            f"{r['symbol']:5s} {r['timeframe']:4s} {r['strategy']:20s} "
            f"ratio={ratio:5.2f} avg={r['avg_return']:+7.2f}% stdev={r['stdev_return']:6.2f} "
            f"pos_rate={r['positive_rate']:5.1f}% (n={r['runs']})"
        )


def main():
    top_n = 10
    if "--top" in sys.argv:
        top_n = int(sys.argv[sys.argv.index("--top") + 1])

    runs = load_all_runs()
    if not runs:
        print(f"No multitimeframe_*.json files found in {DATA_DIR}")
        sys.exit(1)

    combos = aggregate(runs)
    rows = summarize(combos)
    if not rows:
        print("No combo has enough historical runs yet (need 5+ appearances). Run the backtest more days first.")
        sys.exit(0)

    print_report(rows, top_n)


if __name__ == "__main__":
    main()
