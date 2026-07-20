---
name: crypto-sentiment-defi
description: Daily crypto sentiment analysis (32 keywords monitored on X/Twitter locally; qualitative news-based sentiment in the cloud routine), DeFi news discovery pushed to Airtable with duplicate filtering, and an X/Twitter post — draft-only locally, auto-posted via Blotato in the cloud routine. Usage — /crypto-sentiment-defi, or "run the daily crypto sentiment report"
---

Merges ClawdBot's `crypto-sentiment-analyzer` + `airtable-defi-news` skills, cleaned up and extended per the user's request to "build on" it with an LLM backend (Kimi/Moonshot, OpenRouter as a secondary option) instead of pure keyword-counting.

## Two different workflows: local vs. cloud

This skill runs differently depending on where it executes, because the `/schedule` cloud sandbox blocks essentially all raw third-party HTTPS calls (confirmed via diagnostic: `api.moonshot.ai`, `api.telegram.org`, `discord.com`, `api.hyperliquid.xyz`, and even `api.airtable.com` directly all return 403 at the proxy/CONNECT level). Only GitHub, PyPI, npm, and MCP-connector traffic (Airtable, Gmail) get through. So:

### Local run (full pipeline, real X data)

1. **Sentiment + social drafts** (mechanical):
   ```bash
   cd ~/.claude/skills/crypto-sentiment-defi
   python3 scripts/run_daily.py
   ```
   Fetches X mentions for all 32 keywords via `bird`, scores bullish/bearish sentiment, detects spikes vs the 7-day rolling baseline (`data/sentiment-history.json`), drafts (never publishes) social posts via Kimi to `data/social_drafts_<date>.json`, and prints a Telegram-ready brief to stdout. If `X_AUTH_TOKEN`/`X_CT0` aren't set or `bird` isn't installed, `fetch_mentions.py` returns 0 mentions per keyword gracefully instead of crashing. If Moonshot is unreachable (e.g. an outage), `generate_drafts()` fails gracefully too and the run continues without social drafts — this same resilience is what makes the cloud path work (see below).
2. **DeFi news discovery** (agent step): search for 2-3 fresh items (queries: "DeFi crypto news today", "Ethereum Layer 2 news", "Solana ecosystem updates", "Bitcoin ETF institutional", "crypto regulations SEC"). For each: `topic`, `title`, `content` (<280 chars), `why` (1 sentence), `source` (URL).
3. **Push to Airtable, with dedup**: `airtable_sync.push_daily_defi_news([...])` — checks the last 7 days via Jaccard similarity (`dedup.py`, 60% threshold), skips near-duplicates.
4. **Deliver**: pipe `run_daily.py`'s stdout brief through the existing local `telegram` skill (`/telegram <brief>`) — don't rebuild Telegram integration.

### Cloud `/schedule` routine (no X data, no Moonshot, no Telegram)

Do **not** run `scripts/run_daily.py` or `scripts/sentiment_analyzer.py` in the cloud routine — they depend on `bird` (needs X cookies, deliberately excluded from cloud, see below) and Moonshot (blocked). Instead the routine prompt has the agent do everything itself:
1. WebSearch for the same DeFi news queries as above.
2. Write a **qualitative** sentiment paragraph (bullish/neutral/bearish/mixed + why) based on the news tone — replaces the numeric X-keyword scoring, which would otherwise always show a misleading 0%/0% in the cloud (no X data there).
3. Push to Airtable via the **Airtable MCP connector** directly (not `airtable_sync.py`'s REST client — that hits the blocked `api.airtable.com` host; the MCP connector is a separate, working code path).
4. Draft a single X/Twitter post itself (it's already an LLM — no need to call Moonshot for this), then **auto-post it via the Blotato MCP connector** — `blotato_list_accounts` (platform=twitter) to find the mydefilife account, then `blotato_create_post`. See "Auto-posting to X" below — this is a deliberate policy change from the earlier draft-only design.
5. Deliver a summary email via the **`send_email` tool on the "Routines" MCP connector** (a custom n8n workflow — Gmail's `create_draft` was the original approach but only produces an unsent draft; n8n makes a real SMTP send since n8n's network isn't sandboxed. See `hyperliquid-backtest/n8n/README.md` for how that connector works).

**X session cookies (`X_AUTH_TOKEN`/`X_CT0`) are never embedded in the `/schedule` routine regardless of the network block** — they grant full account access if ever leaked from a stored cloud prompt, unlike the other credentials here. This was a deliberate security decision, not a technical limitation like the others.

## Auto-posting to X

**Only the cloud routine auto-posts, and only to X/Twitter (mydefilife account), and only that one platform.** This is a deliberate, explicit exception to the general "never auto-publish" default used elsewhere in these skills:
- **Local runs** (`scripts/social_suggestions.py`, called by `run_daily.py`): still strictly draft-only, writes to `data/social_drafts_<date>.json`, never calls Blotato itself. Post manually via the local `blotato` skill if you want to.
- **Cloud routine**: drafts the X post itself and calls `blotato_create_post` directly — no human-in-the-loop review step. This was an explicit user decision (not a default this skill should default new platforms/routines into) — if extending this pattern to another skill or platform, confirm with the user first rather than assuming the same auto-post policy applies.

## Env vars

See `.env.example`. `AIRTABLE_API_KEY`, `MOONSHOT_API_KEY`/`OPENROUTER_API_KEY`, `X_AUTH_TOKEN`/`X_CT0`.

## Scheduling

Daily via a `/schedule` cloud routine (not `/loop`) — see the "Cloud `/schedule` routine" workflow above. The routine has `Bash`/`WebSearch` tools plus the Airtable, Blotato, and "Routines" (n8n) MCP connectors attached; it does not need `bird` installed since X monitoring is skipped entirely in the cloud path.

## Provenance / what changed from the ClawdBot original

- `scripts/sentiment_analyzer.py`, `scripts/fetch_mentions.py` — same keyword lexicon, same bird-CLI approach, same spike math, refactored into importable functions instead of a single monolithic script.
- `scripts/dedup.py`, `scripts/airtable_sync.py` — same Jaccard dedup + Airtable schema as the original `airtable_defi_news.py`, **except the Airtable token is now `AIRTABLE_API_KEY` (env var), not hardcoded in plaintext** — the VPS original had `AIRTABLE_TOKEN = "patb2BPz..."` literally in the source file. Don't repeat that mistake if you ever edit this.
- `scripts/social_suggestions.py` — replaced the original's long template-based post generator with a single Kimi/Moonshot call (`model_client.py`). Originally drafted all 4 platform variants (twitter/linkedin/threads/bluesky); simplified to X/Twitter-only per user request ("we only really need the X version"). Local runs stay draft-only; the cloud routine auto-posts (see "Auto-posting to X" above).
- News discovery moved from a Brave-Search-API Python client to an agent-driven web search step (see step 3) — no new API key needed, and better judgment on relevance than keyword-matched queries.
- `model_client.py` is new — a small OpenAI-completions-compatible client that switches between Moonshot (default, per the user's preference) and OpenRouter (secondary, for cost/model flexibility) via `MODEL_BACKEND`.
