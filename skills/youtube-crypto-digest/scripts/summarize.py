#!/usr/bin/env python3
"""Summarize a fetched transcript (or title+description fallback) via Kimi/Moonshot."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from model_client import chat

PROMPT = """Summarize this crypto/DeFi YouTube video in 3-4 concise bullet points. \
Focus on concrete claims, price levels, project names, and any actionable takeaways. \
No fluff, no "in this video the creator discusses" framing — just the substance.

Title: {title}

Content:
{content}"""


def summarize_video(title: str, content: str) -> str:
    if not content.strip():
        return "(no transcript available — description too short to summarize)"
    prompt = PROMPT.format(title=title, content=content[:8000])
    return chat([{"role": "user", "content": prompt}])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python summarize.py <title> [content_file]")
        sys.exit(1)
    title = sys.argv[1]
    content = Path(sys.argv[2]).read_text() if len(sys.argv) > 2 else sys.stdin.read()
    print(summarize_video(title, content))
