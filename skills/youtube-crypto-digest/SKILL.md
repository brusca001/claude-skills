---
name: youtube-crypto-digest
description: Finds 5 recent crypto/DeFi/Solana-meme YouTube videos daily, sends a digest (Telegram locally, real email to mdl@mydefilife.com in the cloud routine), and — via a separate n8n workflow watching for replies — curates a WordPress draft article from whichever video number you reply with. Usage — /youtube-crypto-digest, or "run today's youtube crypto digest", or "summarize video 3"
---

Ported from ClawdBot's `youtube-crypto-digest` skill. The original used the Brave Search API; this version drops that dependency entirely and uses whatever web search tool is already available in the session (Firecrawl locally, WebSearch in a `/schedule` cloud routine) — no new API key needed for discovery.

## Daily digest workflow

1. **Discover videos** (agent step, not a script): search for 5 recent (last 7 days) YouTube videos on crypto/DeFi/Solana-meme-token topics. Query terms modeled on the original: `crypto`, `DeFi`, `Solana meme tokens`, `Solana`, `meme coins`, `altcoins` — scope to `site:youtube.com`. Pick genuinely recent, substantive videos (skip clickbait/low-view spam if apparent). For each, capture `title`, `url`, and `channel` if visible.

2. **Format and send the digest — local run**:
   ```bash
   cd ~/.claude/skills/youtube-crypto-digest
   echo '[{"title": "...", "url": "...", "channel": "..."}, ...]' | python3 scripts/format_digest.py | python3 scripts/send_telegram.py
   ```
   (Or use the existing `/telegram` skill instead of `send_telegram.py` — same bot, same result.)

   **Cloud `/schedule` routine**: `api.telegram.org` is blocked by this sandbox's network egress policy (confirmed via diagnostic — only GitHub/PyPI/npm and MCP-connector traffic get through), so `send_telegram.py` will fail there. Use the **`send_email` tool on the "Routines" MCP connector** (n8n) instead, addressed to **`mdl@mydefilife.com`** (not blvck@brucelevick.com — that mailbox is what the reply-to-article n8n workflow below watches, so the digest has to land there for reply-threading to work). The digest body must follow the exact numbered format `format_digest.py` produces (`N. Title (Channel)` then a URL line) — a downstream n8n workflow parses replies against this exact shape.

3. **End the routine here.** `/schedule` runs are one-shot/non-interactive — don't wait for a reply.

## Reply-to-article pipeline (separate n8n workflow, not part of the cloud routine)

Reply to a digest email with a number (e.g. "1") and a separate n8n workflow — `n8n/youtube-digest-reply-pipeline.json`, watching `mdl@mydefilife.com` via IMAP — picks it up, extracts that video's info directly from the quoted original message (no Airtable lookup needed), fetches its transcript via `yt-dlp`, drafts an article via Moonshot, and creates it as a **WordPress draft** (not published live) on mydefilife.com for review. See `n8n/README.md` for full setup steps, credentials needed, and a known risk (the reply-parsing regex is tuned for standard Gmail-style quoting — may need adjusting for `mdl@mydefilife.com`'s actual mail client).

This replaces the originally-planned local on-demand summarization flow below for the "pick a video" use case — that still works for manual/local use, but the primary path now is reply-by-email.

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
