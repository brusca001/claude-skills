#!/usr/bin/env python3
"""
Orchestrates the mechanical half of the daily pipeline:
  1. Fetch X mentions for all 27 keywords (bird CLI)
  2. Score sentiment + spike detection, update rolling baseline
  3. Draft social post suggestions (Kimi/Moonshot) — never publishes
  4. Print a Telegram-ready brief to stdout

DeFi news discovery (needs live web search) and the Airtable push are deliberately
NOT done here — see SKILL.md. Those need an agent's search tool, not a bespoke
Python HTTP client, and are more reliable done that way.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


_load_env()

from fetch_mentions import search_keyword
from sentiment_analyzer import analyze_all_keywords
from social_suggestions import generate_drafts


def format_telegram_brief(results: dict) -> str:
    sorted_kw = sorted(results.items(), key=lambda x: x[1]["volume"], reverse=True)
    avg_bullish = sum(r["bullish_pct"] for r in results.values()) / len(results)
    avg_bearish = sum(r["bearish_pct"] for r in results.values()) / len(results)

    lines = [
        "\U0001F4CA Crypto Sentiment Brief\n",
        f"\U0001F7E2 Bullish: {avg_bullish:.0f}%  \U0001F534 Bearish: {avg_bearish:.0f}%\n",
        "Top 3 Trending:",
    ]
    for i, (kw, r) in enumerate(sorted_kw[:3], 1):
        lines.append(f"{i}. {kw} ({r['volume']:,} mentions, {r['bullish_pct']}% bullish)")

    spikes = [(kw, r) for kw, r in results.items() if r["spike"]]
    if spikes:
        lines.append("\n\U0001F525 Spikes:")
        for kw, r in sorted(spikes, key=lambda x: x[1]["spike_pct"], reverse=True)[:3]:
            lines.append(f"• {kw}: +{r['spike_pct']:.0%}")

    return "\n".join(lines)


def main():
    print("Fetching X mentions for 27 keywords...", file=sys.stderr)
    results = analyze_all_keywords(search_keyword)

    print("Generating social post drafts (draft only, no publish)...", file=sys.stderr)
    generate_drafts(results)

    brief = format_telegram_brief(results)
    print(brief)  # stdout: pipe this to the telegram skill's send step
    return results


if __name__ == "__main__":
    main()
