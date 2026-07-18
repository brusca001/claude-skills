#!/usr/bin/env python3
"""
Fetch X/Twitter mentions for a keyword via the `bird` CLI (npm i -g @steipete/bird),
using reused session cookies. Ported from ClawdBot's search_keyword_on_x, cleaned up.

`bird` is a standalone global npm package, not ClawdBot-specific — install it wherever
this runs (laptop or /schedule cloud sandbox).
"""

import os
import subprocess


def search_keyword(keyword: str, count: int = 50, timeout: int = 20) -> tuple[int, str]:
    """Returns (approx_mention_count, raw_text_for_sentiment_scan). Empty text if bird unavailable."""
    auth_token = os.environ.get("X_AUTH_TOKEN")
    ct0 = os.environ.get("X_CT0")

    if not auth_token or not ct0:
        print(f"X_AUTH_TOKEN/X_CT0 not set — skipping live search for '{keyword}'")
        return 0, ""

    try:
        result = subprocess.run(
            ["bird", "search", keyword, "-n", str(count), "--auth-token", auth_token, "--ct0", ct0],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0 or not result.stdout.strip():
            print(f"bird search failed for '{keyword}': {result.stderr[:200]}")
            return 0, ""
        output = result.stdout
        tweet_blocks = [b for b in output.split("\n\n") if b.strip()]
        return max(1, len(tweet_blocks)), output
    except subprocess.TimeoutExpired:
        print(f"bird search timed out for '{keyword}'")
        return 0, ""
    except FileNotFoundError:
        print("bird CLI not found — run: npm install -g @steipete/bird")
        return 0, ""


if __name__ == "__main__":
    import sys

    kw = sys.argv[1] if len(sys.argv) > 1 else "Bitcoin"
    count, text = search_keyword(kw)
    print(f"{kw}: {count} mentions, {len(text)} chars of text")
