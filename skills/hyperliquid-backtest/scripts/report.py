#!/usr/bin/env python3
"""Posts a backtest summary to Discord via webhook. Pure stdlib, no requests dependency."""

import json
import os
import sys
import urllib.request


def post_to_discord(message: str, webhook_url: str = None) -> bool:
    webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL not set — skipping Discord post, printing instead:")
        print(message)
        return False

    payload = json.dumps({"content": message[:2000]}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"Discord post failed: {e}")
        print(message)
        return False


if __name__ == "__main__":
    text = sys.stdin.read() if not sys.stdin.isatty() else (sys.argv[1] if len(sys.argv) > 1 else "")
    if not text:
        print("Usage: echo 'message' | python report.py   OR   python report.py 'message'")
        sys.exit(1)
    post_to_discord(text)
