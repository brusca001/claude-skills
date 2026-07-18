---
name: youtube-crypto-digest
description: Finds 5 recent crypto/DeFi/Solana-meme YouTube videos daily, sends a digest to Telegram, and summarizes on request via Kimi. Usage — /youtube-crypto-digest, or "run today's youtube crypto digest", or "summarize video 3"
---

Ported from ClawdBot's `youtube-crypto-digest` skill. The original used the Brave Search API; this version drops that dependency entirely and uses whatever web search tool is already available in the session (Firecrawl locally, WebSearch in a `/schedule` cloud routine) — no new API key needed for discovery.

## Daily digest workflow

1. **Discover videos** (agent step, not a script): search for 5 recent (last 7 days) YouTube videos on crypto/DeFi/Solana-meme-token topics. Query terms modeled on the original: `crypto`, `DeFi`, `Solana meme tokens`, `Solana`, `meme coins`, `altcoins` — scope to `site:youtube.com`. Pick genuinely recent, substantive videos (skip clickbait/low-view spam if apparent). For each, capture `title`, `url`, and `channel` if visible.

2. **Format and send the digest**:
   ```bash
   cd ~/.claude/skills/youtube-crypto-digest
   echo '[{"title": "...", "url": "...", "channel": "..."}, ...]' | python3 scripts/format_digest.py | python3 scripts/send_telegram.py
   ```
   (Locally, you can use the existing `/telegram` skill instead of `send_telegram.py` — same bot, same result. `send_telegram.py` exists because the cloud `/schedule` routine won't have the local `telegram` skill directory available, so it needs a self-contained sender.)

3. **End the routine here.** `/schedule` runs are one-shot/non-interactive — don't wait for a reply. Summarization (step 4) happens as a separate, manually-triggered local invocation later.

## On-demand summarization ("summarize video N")

```bash
cd ~/.claude/skills/youtube-crypto-digest
python3 scripts/transcript_fetch.py "<video_url>"   # yt-dlp auto-captions
python3 scripts/summarize.py "<title>" <<< "<transcript text>"
```

If `transcript_fetch.py` returns nothing (no auto-captions, or `yt-dlp` not installed — `pip install yt-dlp` first), fall back to summarizing the video's title + description directly (fetch via your web search/scrape tool), noting lower fidelity than a real transcript.

## Env vars

See `.env.example`: `MOONSHOT_API_KEY` for summarization, `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` (reuse the existing local `telegram` skill's values) for delivery.

## Scheduling

Daily via a `/schedule` cloud routine (not `/loop`). Routine prompt: `pip install yt-dlp` (only needed if summarization will run in the same routine — the daily digest send itself doesn't need it), then do steps 1-2 above, then end.

## Provenance / what changed from the ClawdBot original

- Discovery: Brave Search API → agent-driven web search (no new API key).
- Delivery: reuses the existing local `telegram` skill's bot/chat ID instead of rebuilding Telegram integration from scratch.
- Transcript fetch: kept `yt-dlp` as the primary method (same as original); dropped the Apify fallback (extra paid dependency, original iteration notes suggested it was experimental) in favor of a title/description fallback via whatever search tool is already in use.
- Summarization: Kimi/Moonshot (`model_client.py`) instead of `@steipete/summarize` — same idea, one fewer global npm dependency to install in the cloud sandbox.
- Interactive "pick a video" step from the original is now explicitly two-phase: the scheduled routine only sends the digest; summarization is a separate manual step, since `/schedule` runs can't block on a reply.
