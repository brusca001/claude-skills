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
7. **Has Caption URL?** (If node) — routes on `captionUrl` being non-empty. True → fetches the official transcript. False → falls back to the TranscriptAPI service instead of giving up (see "TranscriptAPI fallback" below).
8. **Fetch Transcript XML** (HTTP Request) — `GET`s the caption track URL, which returns the transcript as XML (`<text start="..." dur="...">...</text>` per line). `neverError: true`.
9. **Parse Transcript XML** (Code node) — strips XML tags/entities down to plain transcript text, or falls back to a clearly-flagged placeholder if the XML is somehow empty/malformed.
10. **Fetch Transcript (TranscriptAPI)** (HTTP Request, false branch of step 7) — calls the [transcriptapi.com](https://transcriptapi.com) commercial transcript API (`GET /api/v2/youtube/transcript?video_url=...`, Header Auth credential), which resolves transcripts YouTube's own watch-page HTML didn't expose. `neverError: true`, 30s timeout.
11. **Format TranscriptAPI Transcript** (Code node) — joins the returned `transcript[].text` segments into plain text, normalizing to the same shape `Parse Transcript XML` produces, so both paths converge cleanly.
12. **Generate Article (Claude)** (HTTP Request) — calls `api.anthropic.com/v1/messages` (n8n's built-in **Predefined Credential Type → Anthropic**, model `claude-sonnet-5`) to write an 800-1200 word article as JSON `{title, content}`. Reached from both transcript paths. Originally used Moonshot/Kimi — switched to Claude; see "Why Claude instead of Moonshot" below.
13. **Parse Article JSON** (Code node) — extracts title/content, with a fallback if the model didn't return clean JSON.
14. **Create WordPress Draft** (HTTP Request) — `POST /wp-json/wp/v2/posts` with `status: draft` — lands as a draft for review, never auto-publishes live, per your explicit choice.

## Why the transcript fetch changed

The original design used `yt-dlp` via an `Execute Command` node. That requires `yt-dlp` installed on the n8n host *and* the Execute Command node enabled — not guaranteed on every n8n instance, and the reported issue ("the fetch transcript node is empty") pointed at exactly that class of problem. This version instead fetches the transcript the same way most "youtube-transcript" libraries do it, using only HTTP: YouTube's own watch-page HTML embeds a `captionTracks` list with a direct URL to the transcript as XML — no `yt-dlp`, no shell access, no API key, just two `HTTP Request` nodes and some regex. More portable, one less system dependency, works on any n8n instance.

Tested locally (video ID extraction, caption-track-URL regex, XML entity decoding) against realistic sample data before shipping — all four test cases passed.

## Setup steps

1. **Import the workflow.**
2. **Email Trigger (IMAP) node** — set up an IMAP credential for `mdl@mydefilife.com` and select it. The `youtube-crypto-digest` cloud routine sends the daily digest there (not `blvck@brucelevick.com`) specifically so replies land in the mailbox this workflow watches.
3. **Generate Article (Claude) node** — n8n ships a dedicated Anthropic credential type, so this is simpler than the old Moonshot setup:
   - In n8n: **Credentials → New → search "Anthropic"**
   - **API Key** field: your Anthropic API key
   - Save it, then on the node select **Authentication → Predefined Credential Type → Credential Type: Anthropic** → your saved credential.
   - n8n's Anthropic credential auto-injects the `x-api-key` header, but **not** `anthropic-version` — that header is added manually in the node's Headers (`anthropic-version: 2023-06-01`), since Anthropic's API rejects requests without it. (Verified directly against n8n's `AnthropicApi.credentials.ts` source — its `authenticate()` only sets `x-api-key`.)
4. **Create WordPress Draft node** — set **Authentication → Generic Credential Type → Basic Auth**, credential = your mydefilife.com WordPress Application Password (username + the generated app password, not your normal login password).
5. **Fetch Transcript (TranscriptAPI) node** — set up a **Header Auth** credential the same way as Moonshot:
   - In n8n: **Credentials → New → search "Header Auth"**
   - **Name** field: `Authorization`
   - **Value** field: `Bearer <your transcriptapi.com API key>`
   - Sign up at [transcriptapi.com](https://transcriptapi.com) — 100 free credits to start, no card required, then $5/mo for 1,000 credits if you outgrow the free tier (see "TranscriptAPI fallback" below for why this replaced the Whisper VPS approach).
   - Save it, then select it in the node's **Authentication → Generic Credential Type → Header Auth** field.
6. Activate the workflow.

No `yt-dlp` install and no Execute Command dependency needed anymore — steps 3-4 (the old yt-dlp requirement) are gone.

## Why Claude instead of Moonshot

This node originally called Moonshot/Kimi (`kimi-k2.5`), same as the `/schedule` cloud routines and local `.env` files elsewhere in this project still do — those are untouched, this change is scoped to this one workflow's article-generation node only. Switched to Claude (`claude-sonnet-5` via `api.anthropic.com/v1/messages`) per your request. Two response-shape differences from the Moonshot/OpenAI-style setup that had to be accounted for:

- **Auth**: Anthropic uses `x-api-key` (n8n's built-in Anthropic credential handles this) instead of `Authorization: Bearer`, plus a required `anthropic-version` header not covered by the credential.
- **Response body**: Claude returns `{"content": [{"type": "text", "text": "..."}]}`, not `{"choices": [{"message": {"content": "..."}}]}` — `Parse Article JSON` reads `$json.content[0].text` now instead of `$json.choices[0].message.content`.
- No `temperature: 1` requirement — that was a Moonshot-specific constraint (it rejected any other value); Claude doesn't need it, so it was dropped from the request body.

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

So an empty `captionUrl` would have thrown and crashed the run on the very next execution, independent of `neverError`. Fixed by adding the **Has Caption URL?** If node — originally just routed the false branch straight to a "no captions" placeholder, now it routes to the TranscriptAPI fallback instead (see below), which is strictly better: a real transcript when possible instead of giving up.

## TranscriptAPI fallback (replaced the Whisper VPS approach)

**Why this exists:** the HTML-scrape approach (`Extract Caption Track URL`) can only find transcripts YouTube already generated and exposes in the watch-page HTML. For videos with zero official captions, there was previously no way to get real transcript content — the article would be title-only.

**What was tried first, and why it was abandoned:** the original fallback ran a self-hosted `yt-dlp` + `faster-whisper` pipeline on the Hostinger VPS (`whisper_transcript_api.py`, still saved in this folder for reference/potential future use, but no longer wired into this workflow). It worked in isolated CLI testing (cookies + `--js-runtimes node` for the n-challenge), but hit persistent `"Sign in to confirm you're not a bot"` errors in real n8n-triggered usage — even after fixing a real bug where `yt-dlp` was silently corrupting its own cookie jar on every run (`--cookies FILE` is both input *and* output; fixed with a disposable per-request copy, verified via checksum). The bot-detection persisted with genuinely fresh, uncorrupted cookies, which points to the VPS's datacenter IP reputation rather than anything fixable in code — YouTube scrutinizes datacenter IPs far more aggressively than residential ones regardless of cookie validity.

**What replaced it:** [transcriptapi.com](https://transcriptapi.com), a commercial YouTube transcript API — chosen as the cheapest current option after comparing it against Supadata.ai, youtube-transcript.io, and SerpApi-style alternatives:

| Service | Entry pricing | Notes |
|---|---|---|
| **TranscriptAPI.com (chosen)** | 100 free credits (no card, no expiry noted), then **$5/mo for 1,000 credits** ($0.005/request) | Cheapest verified paid tier; median ~49ms response time; failed/rate-limited requests cost 0 credits |
| Supadata.ai | $5-19/mo for 1,000 credits | Same ballpark at low volume, pricier at scale |
| youtube-transcript.io | Token-based, harder to compare directly | |
| Apify (transcript actors) | ~$0.001-0.012/video pay-as-you-go | Cheaper at high volume but adds Apify as another platform dependency |

For "a few dozen requests/month" the free tier alone likely covers this indefinitely; the $5/mo paid tier (1,000 credits) is wildly more headroom than needed if/when the free credits run out.

**How it's wired**: `Fetch Transcript (TranscriptAPI)` — `GET https://transcriptapi.com/api/v2/youtube/transcript?video_url={{ $json.videoUrl }}&format=json`, Header Auth credential (`Authorization: Bearer <key>`), `neverError: true`, 30s timeout (this is a real API, not a multi-minute audio download, so no need for the old 10-minute Whisper timeout). Response shape is `{"transcript": [{"text": "...", "start": 0.0, "duration": ...}, ...], ...}`. `Format TranscriptAPI Transcript` joins the `text` fields into plain text and normalizes to the same `{transcript, videoTitle, videoUrl, hasTranscript}` shape `Parse Transcript XML` produces, so both paths converge into `Generate Article (Claude)` identically.

**Cost of this fallback**: near-instant (no audio download/transcription wait), and only fires for the minority of videos with no official captions — so credit usage stays low even well past a few dozen digest replies a month.

## Known risks / most likely things to need adjusting

1. **YouTube's watch-page HTML structure can change.** The `captionTracks` regex is a well-established pattern (same technique multiple popular transcript libraries use) but YouTube could alter their page structure at any time, which would break `Extract Caption Track URL`. Failure mode is graceful (falls through to the TranscriptAPI fallback, not a crash).
2. **Region/consent-wall pages.** Some videos or network locations get served a cookie-consent interstitial instead of the real watch page. If `Extract Caption Track URL` consistently fails on videos that should have captions, this is the likely cause — TranscriptAPI still covers these since it doesn't depend on the watch-page HTML.
3. **TranscriptAPI free-tier credits will eventually run out** for high-reply-volume months — if `Format TranscriptAPI Transcript` starts returning the "no transcript" placeholder for videos that clearly have captions, check the TranscriptAPI dashboard for a 402/quota error before assuming the video itself has no transcript.
4. **transcriptapi.com itself could also occasionally fail to find a transcript** (deleted/private videos, non-English-only videos without a matching language track) — same graceful degrade-to-title-only behavior as before, not a crash.

## Notes

- Node types verified against current n8n source (`n8n-io/n8n` on GitHub), including the `options.response.response.responseFormat`/`outputPropertyName` path used to get raw HTML/XML text back from the HTTP Request nodes instead of n8n trying to auto-parse it as JSON.
- This is a *separate* workflow from `claude-mcp-tools.json` — it isn't an MCP server, it's triggered by an actual email arriving, not by Claude calling a tool.
- The old Whisper VPS service (`whisper_transcript_api.py`) is left deployed on the Hostinger VPS (`pm2` process `whisper-transcript-api`, port 3600) but is no longer called by this workflow — it's dormant infrastructure, not deleted, in case a future need for real audio transcription (as opposed to a commercial transcript lookup) comes up.
