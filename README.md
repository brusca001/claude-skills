# claude-skills

Skills that run as `/schedule` cloud routines (each routine clones this repo fresh on every run — see each skill's SKILL.md "Scheduling" section for the routine prompt and cron cadence).

Local copies of the same skills live at `~/.claude/skills/<name>/` for manual/interactive use; this repo exists purely so the cloud sandbox has something to clone.

## Skills

- **hyperliquid-backtest** — daily multi-timeframe backtest (MA crossover + RSI mean reversion) against Hyperliquid public testnet data, reports to Discord.
- **crypto-sentiment-defi** — daily X/Twitter sentiment analysis (32 keywords) + DeFi news pushed to Airtable + draft-only social post suggestions.
- **youtube-crypto-digest** — daily digest of 5 recent crypto/DeFi/Solana-meme YouTube videos, sent to Telegram.

Ported from ClawdBot (VPS 31.97.49.240) — see each skill's SKILL.md "Provenance" section for what changed.

Env vars are never committed — see each skill's `.env.example`. `/schedule` routines get credentials from the routine's own env config, not from this repo.
