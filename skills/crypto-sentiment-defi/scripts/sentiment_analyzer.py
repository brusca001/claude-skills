#!/usr/bin/env python3
"""
Keyword-based sentiment scoring + 7-day rolling spike detection.
Ported from ClawdBot's sentiment_analyzer.py — same lexicon, same spike threshold (50%),
same history-file rolling-baseline approach, cleaned up into importable functions.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

KEYWORDS = {
    "Layer 1": ["Ethereum", "Binance", "Solana", "Ripple", "Cardano", "Avalanche", "Polkadot"],
    "DeFi": ["Uniswap", "Aave", "Curve Finance", "Compound", "Chainlink"],
    "Meme/Community": ["Dogecoin", "Shiba Inu", "Floki Inu", "Pepe", "Pump.fun"],
    "Emerging": ["Arbitrum", "Optimism", "Polygon", "Raydium", "AI Tokens", "Base", "Hyperliquid", "Restaking"],
    "Macro": ["Bull Market", "Crypto Regulation", "Bitcoin", "Cryptocurrency", "Altcoin", "Airdrop", "ETF"],
}

BULLISH_KEYWORDS = {
    "moon", "pump", "breakout", "hodl", "gainer", "rally", "surge", "soar", "bull", "bounce",
    "green", "strong", "momentum", "bullish", "opportunities", "bullrun", "accumulate", "buy",
    "support", "reversal", "hope", "confidence", "loading", "position", "breakthrough",
    "explosive", "skyrocket", "gain",
}
BEARISH_KEYWORDS = {
    "crash", "dump", "risk", "decline", "margin call", "liquidation", "bearish", "red",
    "weakness", "sell", "panic", "fear", "loss", "drop", "collapse", "fall", "down", "short",
    "resistance", "avoid", "caution", "warning", "concern", "struggle", "pressure",
}
NEUTRAL_KEYWORDS = {
    "update", "proposal", "integration", "partnership", "adoption", "development", "analysis",
    "trading", "volume", "price", "level", "range", "technical", "chart", "news",
    "announcement", "data", "report", "release",
}

SPIKE_THRESHOLD = 0.50
HISTORY_FILE = Path(__file__).parent.parent / "data" / "sentiment-history.json"


def analyze_sentiment(text: str) -> tuple[int, int, int]:
    text = text.lower()
    bullish = sum(1 for w in BULLISH_KEYWORDS if w in text)
    bearish = sum(1 for w in BEARISH_KEYWORDS if w in text)
    neutral = sum(1 for w in NEUTRAL_KEYWORDS if w in text)
    if bullish + bearish + neutral == 0:
        neutral = 1
    return bullish, bearish, neutral


def sentiment_pct(bullish: int, bearish: int, neutral: int) -> tuple[int, int, int]:
    total = bullish + bearish + neutral
    if total == 0:
        return 0, 0, 100
    return round(100 * bullish / total), round(100 * bearish / total), round(100 * neutral / total)


def load_history() -> dict:
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {"daily": {}, "baselines": {}}


def save_history(history: dict) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_baseline(history: dict, keyword: str, default: int = 5000) -> float:
    return history.get("baselines", {}).get(keyword, default)


def detect_spike(current: float, baseline: float, threshold: float = SPIKE_THRESHOLD) -> tuple[bool, float]:
    if baseline == 0:
        return False, 0.0
    increase = (current - baseline) / baseline
    return increase >= threshold, increase


def update_baselines(history: dict, today_results: dict) -> dict:
    """Roll today's volumes into a 7-day rolling average baseline per keyword."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    history["daily"][today] = {
        kw: {"volume": r["volume"], "bullish": r["bullish_pct"], "bearish": r["bearish_pct"], "spike": r["spike"]}
        for kw, r in today_results.items()
    }
    for keyword in today_results:
        recent = [
            history["daily"][d][keyword]["volume"]
            for d in sorted(history["daily"].keys())[-7:]
            if keyword in history["daily"][d]
        ]
        if recent:
            history.setdefault("baselines", {})[keyword] = sum(recent) / len(recent)
    return history


def analyze_all_keywords(mention_fetcher) -> dict:
    """
    mention_fetcher(keyword) -> (volume, text), e.g. fetch_mentions.search_keyword.
    Returns {keyword: {category, volume, baseline, bullish_pct, bearish_pct, neutral_pct, spike, spike_pct}}.
    """
    history = load_history()
    results = {}
    for category, keywords in KEYWORDS.items():
        for keyword in keywords:
            volume, text = mention_fetcher(keyword)
            bullish, bearish, neutral = analyze_sentiment(text)
            bullish_pct, bearish_pct, neutral_pct = sentiment_pct(bullish, bearish, neutral)
            baseline = get_baseline(history, keyword)
            is_spike, spike_pct = detect_spike(volume, baseline)
            results[keyword] = {
                "category": category,
                "volume": volume,
                "baseline": baseline,
                "bullish_pct": bullish_pct,
                "bearish_pct": bearish_pct,
                "neutral_pct": neutral_pct,
                "spike": is_spike,
                "spike_pct": spike_pct,
            }
    save_history(update_baselines(history, results))
    return results
