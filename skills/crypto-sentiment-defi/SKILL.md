---
name: crypto-sentiment-defi
description: Daily crypto sentiment analysis (27 keywords monitored on X/Twitter, bullish/bearish scoring, spike detection) plus DeFi news discovery pushed to Airtable with duplicate filtering, and draft-only social post suggestions via Kimi. Usage — /crypto-sentiment-defi, or "run the daily crypto sentiment report"
---

Merges ClawdBot's `crypto-sentiment-analyzer` + `airtable-defi-news` skills, cleaned up and extended per the user's request to "build on" it with an LLM backend (Kimi/Moonshot, OpenRouter as a secondary option) instead of pure keyword-counting.

## Daily workflow

Run these in order. Steps 1-3 and 6 are mechanical (Python scripts, deterministic). Steps 4-5 need an agent's own search/reasoning and are described as instructions, not scripts — this is not accidental: news relevance judgment and Airtable field-writing are things you (the agent) do directly, better than a bespoke scraper would.

1. **Sentiment + social drafts** (mechanical):
   ```bash
   cd ~/.claude/skills/crypto-sentiment-defi
   python3 scripts/run_daily.py
   ```
   This fetches X mentions for all 27 keywords via `bird`, scores bullish/bearish sentiment, detects spikes vs the 7-day rolling baseline (`data/sentiment-history.json`), drafts (never publishes) social posts via Kimi to `data/social_drafts_<date>.json`, and prints a Telegram-ready brief to stdout.

2. **If `X_AUTH_TOKEN`/`X_CT0` aren't set or `bird` isn't installed**, `fetch_mentions.py` returns 0 mentions per keyword gracefully (no crash) — sentiment scoring still runs, just on no data. Install with `npm install -g @steipete/bird` and set the cookies in `.env` (reused from the same X account ClawdBot used — test with a plain `bird search Bitcoin --auth-token ... --ct0 ...` first, since cookies can be IP/device-bound).

3. **DeFi news discovery** (agent step, not a script): search for 2-3 fresh DeFi/crypto news items from the last 24h (topics: "DeFi crypto news today", "Ethereum Layer 2 news", "Solana ecosystem updates", "Bitcoin ETF institutional", "crypto regulations SEC" — ported from the original query list). Use whatever web search tool is available in this session (Firecrawl locally, WebSearch in a cloud `/schedule` routine). For each item, produce:
   - `topic`: headline
   - `title`: same as topic or a cleaner version
   - `content`: <280 char factual summary
   - `why`: 1 sentence on why it matters
   - `source`: the URL

4. **Push to Airtable, with dedup**:
   ```python
   import sys; sys.path.insert(0, "scripts")
   from airtable_sync import push_daily_defi_news
   push_daily_defi_news([{...}, {...}, {...}])  # the 2-3 records from step 3
   ```
   This checks the last 7 days of Airtable records via Jaccard similarity (`dedup.py`, 60% threshold) and skips anything too similar to what's already posted — same logic as the original, just no more hardcoded API token (`AIRTABLE_API_KEY` env var now).

5. **One Twitter-thread-style record**, same call with `table_type="threads"` — same fields, goes to the Twitter Threads table instead.

6. **Deliver the brief**: send `run_daily.py`'s stdout brief via the existing local `telegram` skill (`/telegram <brief>`, remembering the mandatory `@MrJoben_bot` prefix) — don't rebuild Telegram integration.

## Never do this

- Never call a Blotato/publish endpoint from this skill — `social_suggestions.py` only writes drafts to `data/social_drafts_<date>.json` for human review. If you want to actually post one, do it manually via the existing local `blotato` skill.

## Env vars

See `.env.example`. `AIRTABLE_API_KEY`, `MOONSHOT_API_KEY`/`OPENROUTER_API_KEY`, `X_AUTH_TOKEN`/`X_CT0`.

## Scheduling

Daily via a `/schedule` cloud routine (not `/loop`). The routine prompt should: clone this skill's repo, `npm install -g @steipete/bird`, `pip install -r requirements.txt`, then walk through the 6 steps above itself (it's a real Claude agent, not a script runner — it can do the search/Airtable-write steps directly).

## Provenance / what changed from the ClawdBot original

- `scripts/sentiment_analyzer.py`, `scripts/fetch_mentions.py` — same keyword lexicon, same bird-CLI approach, same spike math, refactored into importable functions instead of a single monolithic script.
- `scripts/dedup.py`, `scripts/airtable_sync.py` — same Jaccard dedup + Airtable schema as the original `airtable_defi_news.py`, **except the Airtable token is now `AIRTABLE_API_KEY` (env var), not hardcoded in plaintext** — the VPS original had `AIRTABLE_TOKEN = "patb2BPz..."` literally in the source file. Don't repeat that mistake if you ever edit this.
- `scripts/social_suggestions.py` — replaced the original's long template-based post generator with a single Kimi/Moonshot call (`model_client.py`) that drafts all 4 platform variants at once. Still strictly draft-only.
- News discovery moved from a Brave-Search-API Python client to an agent-driven web search step (see step 3) — no new API key needed, and better judgment on relevance than keyword-matched queries.
- `model_client.py` is new — a small OpenAI-completions-compatible client that switches between Moonshot (default, per the user's preference) and OpenRouter (secondary, for cost/model flexibility) via `MODEL_BACKEND`.
