#!/usr/bin/env python3
"""
Draft-only social post suggestions from the day's sentiment results, via Kimi/Moonshot.

NEVER auto-publishes — writes drafts to data/social_drafts_<date>.json for human review.
If you want to actually post one, use the existing local `blotato` skill/MCP tools manually.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from model_client import chat

DATA_DIR = Path(__file__).parent.parent / "data"

PROMPT_TEMPLATE = """You are drafting social media posts about today's crypto market sentiment. Be concise, factual, no hype, no financial advice framing (no "buy now" language).

Today's sentiment snapshot (keyword: bullish%/bearish%/volume):
{snapshot}

Spike alerts (>50% mention increase vs 7-day baseline): {spikes}

Write ONE short draft for each of: twitter (<260 chars), linkedin (2-3 sentences, more analytical tone), threads (<400 chars, casual), bluesky (<280 chars).

Respond as JSON only, no markdown fences:
{{"twitter": "...", "linkedin": "...", "threads": "...", "bluesky": "..."}}"""


def build_snapshot_text(results: dict, top_n: int = 8) -> tuple[str, str]:
    sorted_kw = sorted(results.items(), key=lambda x: x[1]["volume"], reverse=True)[:top_n]
    snapshot = "\n".join(f"- {kw}: {r['bullish_pct']}% bullish / {r['bearish_pct']}% bearish, {r['volume']:,} mentions" for kw, r in sorted_kw)
    spikes = [kw for kw, r in results.items() if r.get("spike")]
    spikes_text = ", ".join(spikes) if spikes else "none"
    return snapshot, spikes_text


def generate_drafts(results: dict) -> dict:
    snapshot, spikes_text = build_snapshot_text(results)
    prompt = PROMPT_TEMPLATE.format(snapshot=snapshot, spikes=spikes_text)
    raw = chat([{"role": "user", "content": prompt}], max_tokens=600)
    try:
        drafts = json.loads(raw.strip().strip("`").removeprefix("json").strip())
    except (json.JSONDecodeError, AttributeError):
        drafts = {"error": "model did not return valid JSON", "raw": raw}

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "review_status": "pending",
        "drafts": drafts,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_file = DATA_DIR / f"social_drafts_{today}.json"
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Drafts saved to {out_file} — review before posting, nothing auto-published.")
    return output


if __name__ == "__main__":
    import sys

    print("This module expects a results dict from sentiment_analyzer.analyze_all_keywords().")
    print("Run via run_daily.py for the full pipeline.")
    sys.exit(0 if len(sys.argv) == 1 else 1)
