#!/usr/bin/env python3
"""Formats a list of discovered videos into a Telegram-ready digest message."""

import json
from datetime import datetime, timezone


def format_digest(videos: list[dict]) -> str:
    """videos: list of {title, url, channel (optional), published (optional)}, max 5."""
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    lines = [f"\U0001F4FA Daily Crypto Video Digest — {today}\n"]
    for i, v in enumerate(videos[:5], 1):
        channel = f" ({v['channel']})" if v.get("channel") else ""
        lines.append(f"{i}. {v['title']}{channel}\n   {v['url']}")
    lines.append("\nReply with a number to get a full summary of that video.")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    data = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else json.loads(sys.argv[1])
    print(format_digest(data))
