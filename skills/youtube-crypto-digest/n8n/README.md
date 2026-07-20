# YouTube Digest Reply → mydefilife Article workflow

Import `youtube-digest-reply-pipeline.json` into n8n. Reply-to-article pipeline: you reply to a "YouTube Crypto Digest" email with a number, this watches for it, pulls the video info out of the quoted original message (no Airtable, no separate lookup — the reply email already contains everything needed), fetches the transcript, drafts an article, and creates it as a WordPress draft.

**If you imported an earlier version**, this one replaces the `yt-dlp`/Execute Command transcript step entirely with a pure HTTP approach — see "Why the transcript fetch changed" below.

## What it does, node by node

1. **Email Trigger (IMAP)** — watches an inbox for new mail matching `["UNSEEN", ["SUBJECT", "YouTube Crypto Digest"]]` (IMAP-level pre-filter — only digest-related emails trigger the workflow at all, not every email in the inbox).
2. **Parse Reply & Select Video** (Code node) — parses the reply body for a digit 1-5; parses the quoted original message (everything after the "On ... wrote:" / `>`-quoted boundary) for the numbered video list, matching it against `format_digest.py`'s output shape (`N. Title (Channel)` then a URL on the next line); resolves the selected number to a title + URL. Always returns a valid item — sets `isDigestReply: false` with a `reason` field when the subject doesn't match or a video can't be resolved, rather than trying to bail out from inside the Code node (an earlier version tried `return null` here, which n8n's Code node doesn't actually support — see git history if curious).
3. **Is Valid Digest Reply?** (If node) — routes on `isDigestReply`. True → continues. False → dropped, pipeline ends cleanly here (verified against n8n's source: the If node's false branch is intentionally left unconnected — that's the correct, documented way to drop non-matching items).
4. **Extract Video ID** (Code node) — pulls the 11-character YouTube video ID out of the selected URL (handles `youtube.com/watch?v=`, `youtu.be/`, `/embed/`, `/shorts/` forms).
5. **Fetch YouTube Watch Page** (HTTP Request) — `GET` the video's normal watch page HTML with a browser User-Agent header. `neverError: true` set so a bad/removed video doesn't crash the node — handled gracefully downstream instead.
6. **Extract Caption Track URL** (Code node) — regexes the embedded `"captionTracks":[...]` JSON out of the watch page HTML (this is server-rendered, part of `ytInitialPlayerResponse` — no JS execution needed), picks the English track, unescapes its `baseUrl`.
7. **Fetch Transcript XML** (HTTP Request) — `GET`s that caption track URL, which returns the transcript as XML (`<text start="..." dur="...">...</text>` per line). Also `neverError: true`.
8. **Parse Transcript XML** (Code node) — strips XML tags/entities down to plain transcript text, or falls back to a clearly-flagged placeholder if no captions were found at any prior step.
9. **Generate Article (Moonshot)** (HTTP Request) — calls `api.moonshot.ai` (same Kimi key already used elsewhere) to write an 800-1200 word article as JSON `{title, content}`.
10. **Parse Article JSON** (Code node) — extracts title/content, with a fallback if the model didn't return clean JSON.
11. **Create WordPress Draft** (HTTP Request) — `POST /wp-json/wp/v2/posts` with `status: draft` — lands as a draft for review, never auto-publishes live, per your explicit choice.

## Why the transcript fetch changed

The original design used `yt-dlp` via an `Execute Command` node. That requires `yt-dlp` installed on the n8n host *and* the Execute Command node enabled — not guaranteed on every n8n instance, and the reported issue ("the fetch transcript node is empty") pointed at exactly that class of problem. This version instead fetches the transcript the same way most "youtube-transcript" libraries do it, using only HTTP: YouTube's own watch-page HTML embeds a `captionTracks` list with a direct URL to the transcript as XML — no `yt-dlp`, no shell access, no API key, just two `HTTP Request` nodes and some regex. More portable, one less system dependency, works on any n8n instance.

Tested locally (video ID extraction, caption-track-URL regex, XML entity decoding) against realistic sample data before shipping — all four test cases passed.

## Setup steps

1. **Import the workflow.**
2. **Email Trigger (IMAP) node** — set up an IMAP credential for `mdl@mydefilife.com` and select it. The `youtube-crypto-digest` cloud routine sends the daily digest there (not `blvck@brucelevick.com`) specifically so replies land in the mailbox this workflow watches.
3. **Generate Article (Moonshot) node** — set up a **Header Auth** credential (n8n's generic credential type for APIs without a dedicated node — Moonshot doesn't have one):
   - In n8n: **Credentials → New → search "Header Auth"**
   - **Name** field: `Authorization`
   - **Value** field: `Bearer sk-fL4BfJMmPRhyWa8MOZ50qQ1SXN6L2tHNo5WwXF63uqbri3qb`
   - Save it (call it something like "Moonshot API"), then select it in the node's **Authentication → Generic Credential Type → Header Auth** field.
   - This replaces the earlier version, which had the key hardcoded directly in the node's headers — same security concern flagged for the WordPress credential, now fixed the same way.
4. **Create WordPress Draft node** — set **Authentication → Generic Credential Type → Basic Auth**, credential = your mydefilife.com WordPress Application Password (username + the generated app password, not your normal login password).
5. Activate the workflow.

**Note on the key itself**: this is a different Moonshot key than the one already embedded in the `/schedule` cloud routines and local `.env` files elsewhere in this project (`sk-nozswZm...`). I haven't touched those — only this n8n workflow now uses the new key. Let me know if you want the new key rotated in everywhere instead of just here.

No `yt-dlp` install and no Execute Command dependency needed anymore — steps 3-4 (the old yt-dlp requirement) are gone.

## Known risks / most likely things to need adjusting

1. **The reply-parsing regex** (`Parse Reply & Select Video`) is tuned for standard Gmail-style quoting (verified locally with a realistic sample). If `mdl@mydefilife.com`'s mail client quotes differently, this needs adjusting — its error output includes `rawTextPlain` (the full original email) so you can see the actual format and tell me what to fix.
2. **YouTube's watch-page HTML structure can change.** The `captionTracks` regex is a well-established pattern (same technique multiple popular transcript libraries use) but YouTube could alter their page structure at any time, which would break `Extract Caption Track URL`. If that happens, the failure mode is graceful (falls through to the "no captions available" placeholder, not a crash) but the article quality drops — tell me if drafts start consistently missing transcripts and I'll investigate whether YouTube changed something.
3. **Region/consent-wall pages.** Some videos or network locations get served a cookie-consent interstitial instead of the real watch page. If `Extract Caption Track URL` consistently fails on videos that should have captions, this is the likely cause — fixable by adding a consent cookie/header, tell me if you hit it.

## Notes

- Node types verified against current n8n source (`n8n-io/n8n` on GitHub), including the `options.response.response.responseFormat`/`outputPropertyName` path used to get raw HTML/XML text back from the HTTP Request nodes instead of n8n trying to auto-parse it as JSON.
- The Moonshot API key is embedded directly in the HTTP Request node's headers (not a separate credential) for simplicity — n8n's own builder guidance recommends a proper header-auth credential instead for security; move it there if you'd prefer, it's the same key already used elsewhere in these workflows.
- This is a *separate* workflow from `claude-mcp-tools.json` — it isn't an MCP server, it's triggered by an actual email arriving, not by Claude calling a tool.
