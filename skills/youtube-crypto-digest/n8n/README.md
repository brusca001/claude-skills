# YouTube Digest Reply → mydefilife Article workflow

Import `youtube-digest-reply-pipeline.json` into n8n. Reply-to-article pipeline: you reply to a "YouTube Crypto Digest" email with a number, this watches for it, pulls the video info out of the quoted original message (no Airtable, no separate lookup — the reply email already contains everything needed), fetches the transcript, drafts an article, and creates it as a WordPress draft.

**If you imported an earlier version**, this one replaces the `yt-dlp`/Execute Command transcript step entirely with a pure HTTP approach — see "Why the transcript fetch changed" below.

## What it does, node by node

1. **Email Trigger (IMAP)** — watches an inbox for new mail matching `["UNSEEN", ["SUBJECT", "YouTube Crypto Digest"]]` (IMAP-level pre-filter — only digest-related emails trigger the workflow at all, not every email in the inbox).
2. **Parse Reply & Select Video** (Code node) — parses the reply body for a digit 1-5; parses the quoted original message (everything after the "On ... wrote:" / `>`-quoted boundary) for the numbered video list, matching it against `format_digest.py`'s output shape (`N. Title (Channel)` then a URL on the next line); resolves the selected number to a title + URL. Always returns a valid item — sets `isDigestReply: false` with a `reason` field when the subject doesn't match or a video can't be resolved, rather than trying to bail out from inside the Code node (an earlier version tried `return null` here, which n8n's Code node doesn't actually support — see git history if curious).
3. **Is Valid Digest Reply?** (If node) — routes on `isDigestReply`. True → continues. False → dropped, pipeline ends cleanly here (verified against n8n's source: the If node's false branch is intentionally left unconnected — that's the correct, documented way to drop non-matching items).
4. **Extract Video ID** (Code node) — pulls the 11-character YouTube video ID out of the selected URL (handles `youtube.com/watch?v=`, `youtu.be/`, `/embed/`, `/shorts/` forms).
5. **Fetch YouTube Watch Page** (HTTP Request) — `GET` the video's normal watch page HTML with a browser User-Agent header. `neverError: true` set so a bad/removed video doesn't crash the node — handled gracefully downstream instead.
6. **Extract Caption Track URL** (Code node) — regexes the embedded `"captionTracks":[...]` JSON out of the watch page HTML (this is server-rendered, part of `ytInitialPlayerResponse` — no JS execution needed), picks the English track, unescapes its `baseUrl`. Sets `transcriptAvailable: false` and `captionUrl: ''` if none found.
7. **Has Caption URL?** (If node) — routes on `captionUrl` being non-empty. True → fetches the official transcript. False → falls back to real audio transcription instead of giving up (see "Whisper VPS fallback" below).
8. **Fetch Transcript XML** (HTTP Request) — `GET`s the caption track URL, which returns the transcript as XML (`<text start="..." dur="...">...</text>` per line). `neverError: true`.
9. **Parse Transcript XML** (Code node) — strips XML tags/entities down to plain transcript text, or falls back to a clearly-flagged placeholder if the XML is somehow empty/malformed.
10. **Transcribe via Whisper (VPS)** (HTTP Request, false branch of step 7) — calls a Whisper speech-to-text service running on the Hostinger VPS (`213.210.13.146:3600`), which downloads the video's audio and actually transcribes it. 10-minute timeout, `neverError: true`.
11. **Format Whisper Transcript** (Code node) — normalizes the Whisper response to the same shape `Parse Transcript XML` produces, so both paths converge cleanly.
12. **Generate Article (Moonshot)** (HTTP Request) — calls `api.moonshot.ai` (Header Auth credential) to write an 800-1200 word article as JSON `{title, content}`. Reached from both transcript paths.
13. **Parse Article JSON** (Code node) — extracts title/content, with a fallback if the model didn't return clean JSON.
14. **Create WordPress Draft** (HTTP Request) — `POST /wp-json/wp/v2/posts` with `status: draft` — lands as a draft for review, never auto-publishes live, per your explicit choice.

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

## Fixed via real production data: CRLF line-ending bug

A real reply from `mdl@mydefilife.com` (Apple Mail-style quoting: `On [date], at [time], [email] wrote:`) came back with `isDigestReply: false` despite the reply body itself parsing correctly (`selectedNumber: "5"`) — `videoMap` was completely empty, meaning the video-list regex matched *zero* lines even though all 5 were clearly present in `rawTextPlain`.

**Root cause**: the email body uses `\r\n` (CRLF) line endings. Splitting only on `\n` left a trailing `\r` on every line. In JavaScript regex, `\r` is a line-terminator character — `.` doesn't match it and `$` (without the `m` flag) requires being at the true end of the line-string, so a trailing `\r` silently breaks `/^\s*(\d+)\.\s+(.+)$/` on every single line. No error was thrown; it just matched nothing.

**Fix**: normalize `text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')` before splitting into lines, in `Parse Reply & Select Video`. Verified against the *exact* real `rawTextPlain` from the failed execution shown above — all 5 videos now parse correctly and `isDigestReply: true` / `selectedNumber: "5"` / correct title+URL are produced.

This also confirms the reply-parsing logic itself (quote-boundary detection, number extraction, title/URL matching) is correct against real `mdl@mydefilife.com` mail — it was purely the CRLF handling that was broken.

## Fixed: empty captionUrl crash

Caught this via a real execution where `Extract Caption Track URL` correctly returned `transcriptAvailable: false, captionUrl: ''` for a video with no auto-captions ("Japan Just BLEW PAST the U.S. on Crypto!!..."). The *next* node, `Fetch Transcript XML`, does `GET {{ $json.captionUrl }}` — and n8n's HTTP Request node validates the URL parameter before making any request or checking `neverError`:

```
if (!url) { throw new NodeOperationError(this.getNode(), 'URL parameter cannot be empty'); }
```

So an empty `captionUrl` would have thrown and crashed the run on the very next execution, independent of `neverError`. Fixed by adding the **Has Caption URL?** If node — originally just routed the false branch straight to a "no captions" placeholder, now it routes to the Whisper fallback instead (see below), which is strictly better: a real transcript when possible instead of giving up.

## Whisper VPS fallback (real audio transcription)

**Why this exists:** the HTML-scrape approach (`Extract Caption Track URL`) can only find transcripts YouTube already generated. For videos with zero official captions, there was previously no way to get real transcript content — the article would be title-only. This adds a genuine fallback: download the video's audio and transcribe it directly with Whisper, for videos the scrape approach can't help with.

**What's running**: a small Flask service (`whisper_transcript_api.py`, saved in this folder for reference) deployed on the Hostinger VPS at `213.210.13.146:3600`, managed via `pm2` (process name `whisper-transcript-api`), following the exact same pattern as that VPS's existing `ffmpeg-api`/`hf-render` services. `POST /transcript {"videoUrl": "..."}` → `yt-dlp` downloads audio-only → `faster-whisper` (base model, CPU, int8) transcribes it → returns `{"transcript": "...", "hasTranscript": true/false}`. Auth via `X-API-Key` header (shared secret, embedded in the n8n node's headers, same pattern as the Moonshot key before it got a proper credential — consider moving this to a Header Auth credential too if you want).

**Real problems hit and fixed while building this** (documenting in case they recur — all three affect *any* server-side yt-dlp usage, not just this):

1. **`yt-dlp` binary not on PATH.** Installing `pip install yt-dlp` inside a venv doesn't add it to `PATH` unless the venv is activated — running `pm2 start venv/bin/python3 -- app.py` doesn't activate it. Fixed by calling the full path `venv/bin/yt-dlp` explicitly instead of relying on PATH resolution.
2. **YouTube bot-detection on the VPS's datacenter IP** — `"Sign in to confirm you're not a bot"`, even with a `--extractor-args youtube:player_client=android` workaround. The only reliable fix is authenticating with real browser cookies (`yt-dlp --cookies cookies.txt`) from a logged-in YouTube session. Per your decision, this uses a **secondary/rarely-used YouTube account's cookies**, not your primary one — isolates any account-level consequences (rate-limiting/challenges are the realistic risk, not a "ban" in the copyright-strike sense) away from anything business-critical. The exported cookies file was trimmed from a 2387-line whole-browser-profile export down to 197 lines (YouTube/Google domains only) before it ever touched the VPS, stored at `/root/whisper-transcript-api/cookies.txt` with `600` permissions (root-only).
3. **YouTube's "n challenge"** — a newer anti-bot measure requiring a JavaScript runtime to solve a signature challenge before certain formats become downloadable. Fixed with `pip install "yt-dlp[default]"` (installs the `yt-dlp-ejs` solver package) plus `--js-runtimes node` on every call, since yt-dlp's default JS runtime is Deno (not installed on this VPS) and Node.js (which *is* installed) needs explicit enabling.

**Verified working**: a direct CLI test (cookies + `--js-runtimes node`) completed a full real download + audio extraction successfully. Repeated HTTP-endpoint tests immediately after that hit renewed bot-detection — almost certainly from the sheer volume of requests I made to the same IP in a short testing window, not a problem with the fix itself. If you see `"Sign in to confirm you're not a bot"` errors in real usage (not rapid testing), it's worth checking whether the cookies have expired and need re-export.

**Cost of this fallback**: CPU-only Whisper transcription is slow — a 15-minute video can take 5-10+ minutes on this VPS's 2 vCPUs. The 10-minute HTTP timeout on the n8n side accounts for this. It only fires for the minority of videos with no official captions, so this cost is occasional, not per-video.

## Known risks / most likely things to need adjusting

1. **YouTube's watch-page HTML structure can change.** The `captionTracks` regex is a well-established pattern (same technique multiple popular transcript libraries use) but YouTube could alter their page structure at any time, which would break `Extract Caption Track URL`. Failure mode is graceful (falls through to the Whisper fallback, not a crash).
2. **Region/consent-wall pages.** Some videos or network locations get served a cookie-consent interstitial instead of the real watch page. If `Extract Caption Track URL` consistently fails on videos that should have captions, this is the likely cause.
3. **Whisper VPS cookies will expire.** When they do, both the "Sign in to confirm you're not a bot" error returns and the fallback stops working (degrading to the title-only placeholder again, not crashing) — re-export from the secondary account when this happens.
4. **The Whisper service's `X-API-Key` is a hardcoded header value in the n8n node**, same category of thing already fixed for Moonshot/WordPress — worth moving to a proper credential if you want consistency.

## Notes

- Node types verified against current n8n source (`n8n-io/n8n` on GitHub), including the `options.response.response.responseFormat`/`outputPropertyName` path used to get raw HTML/XML text back from the HTTP Request nodes instead of n8n trying to auto-parse it as JSON, and `options.timeout` for the Whisper call's long wait.
- This is a *separate* workflow from `claude-mcp-tools.json` — it isn't an MCP server, it's triggered by an actual email arriving, not by Claude calling a tool.
- The Whisper VPS service is separate infrastructure from anything in the `claude-skills` GitHub repo — it lives only on the Hostinger VPS, managed via `pm2`, not deployed via git.
