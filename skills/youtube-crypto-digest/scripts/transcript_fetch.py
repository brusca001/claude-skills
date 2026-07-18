#!/usr/bin/env python3
"""
Fetch a YouTube video's auto-caption transcript via yt-dlp.
Primary path only — if yt-dlp fails/isn't installed, the caller (SKILL.md
workflow) falls back to summarizing the video's description/title via
whatever web search tool is available instead.
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path


def fetch_transcript(video_url: str, timeout: int = 60) -> str:
    """Returns the transcript text, or '' if unavailable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_template = str(Path(tmpdir) / "%(id)s.%(ext)s")
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--skip-download",
                    "--write-auto-sub",
                    "--sub-lang",
                    "en",
                    "--sub-format",
                    "vtt",
                    "-o",
                    out_template,
                    video_url,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                print(f"yt-dlp failed: {result.stderr[:300]}")
                return ""

            vtt_files = list(Path(tmpdir).glob("*.vtt"))
            if not vtt_files:
                print("No subtitle file produced (video may lack auto-captions)")
                return ""

            return _clean_vtt(vtt_files[0].read_text(errors="ignore"))
        except FileNotFoundError:
            print("yt-dlp not found — install with: pip install yt-dlp")
            return ""
        except subprocess.TimeoutExpired:
            print(f"yt-dlp timed out fetching transcript for {video_url}")
            return ""


def _clean_vtt(vtt_text: str) -> str:
    """Strip VTT timing/markup down to plain spoken text."""
    lines = vtt_text.splitlines()
    text_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith(("WEBVTT", "Kind:", "Language:")) or "-->" in line or line.isdigit():
            continue
        line = re.sub(r"<[^>]+>", "", line)
        text_lines.append(line)
    # dedupe consecutive repeated lines (common artifact of auto-caption rolling text)
    deduped = []
    for line in text_lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return " ".join(deduped)


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not url:
        print("Usage: python transcript_fetch.py <youtube_url>")
        sys.exit(1)
    print(fetch_transcript(url)[:500])
