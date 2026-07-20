# YouTube Digest Reply → mydefilife Article workflow

Import `youtube-digest-reply-pipeline.json` into n8n. Reply-to-article pipeline: you reply to a "YouTube Crypto Digest" email with a number, this watches for it, pulls the video info out of the quoted original message (no Airtable, no separate lookup — the reply email already contains everything needed), fetches the transcript, drafts an article, and creates it as a WordPress draft.

**If you imported an earlier version of this file and it errored/behaved oddly**: that version had two real bugs, both fixed now — see "What was actually broken" below before re-importing.

## What it does, node by node

1. **Email Trigger (IMAP)** — watches an inbox for new mail matching `["UNSEEN", ["SUBJECT", "YouTube Crypto Digest"]]` (IMAP-level pre-filter — only digest-related emails trigger the workflow at all, not every email in the inbox).
2. **Parse Reply & Select Video** (Code node) — parses the reply body for a digit 1-5; parses the quoted original message (everything after the "On ... wrote:" / `>`-quoted boundary) for the numbered video list, matching it against `format_digest.py`'s output shape (`N. Title (Channel)` then a URL on the next line); resolves the selected number to a title + URL. Always returns a valid item — sets `isDigestReply: false` with a `reason` field when the subject doesn't match or a video can't be resolved, rather than trying to bail out from inside the Code node (see bug #1 below).
3. **Is Valid Digest Reply?** (If node) — routes on `isDigestReply`. True → continues to transcript fetch. False → dropped, pipeline ends cleanly here.
4. **Fetch Transcript (yt-dlp)** (Execute Command) — runs `yt-dlp --write-auto-sub` on the video URL. Falls back to printing `NO_TRANSCRIPT_AVAILABLE` instead of failing the node if the video has no auto-captions (see bug #2 below).
5. **Clean Transcript** (Code node) — strips VTT timing/markup down to plain text, or passes through a placeholder note if no transcript was available.
6. **Generate Article (Moonshot)** (HTTP Request) — calls `api.moonshot.ai` (same Kimi key already used elsewhere) to write an 800-1200 word article as JSON `{title, content}`.
7. **Parse Article JSON** (Code node) — extracts title/content, with a fallback if the model didn't return clean JSON.
8. **Create WordPress Draft** (HTTP Request) — `POST /wp-json/wp/v2/posts` with `status: draft` — lands as a draft for review, never auto-publishes live, per your explicit choice.

## What was actually broken (fixed in this version)

1. **The Code node tried to `return null` to skip non-matching emails.** n8n's Code node in "Run Once for Each Item" mode does not support this — `typeof null === 'object'` passes the initial check, but the value then fails item validation and n8n throws a `ValidationError` ("A 'json' property isn't an object") instead of gracefully skipping. Since the original IMAP trigger had no subject filter, this meant **every single email arriving at the watched inbox** crashed the workflow. Fixed by always returning a valid object with an `isDigestReply` flag, and adding a real **If node** to gate the pipeline (verified against n8n's source: two named outputs, `true`/`false`, index 0/1 — the false branch is intentionally left unconnected, which is the correct way to drop non-matching items).
2. **The transcript-fetch shell command used `&&` chaining and a fixed filename.** Any video without auto-captions (a normal, common case) meant `yt-dlp` produced no file, the subsequent `cat` failed, and — since `Execute Command` throws on non-zero exit code by design — the entire node errored out and killed the run. Fixed with an `if/then/else` fallback so the command always exits 0, emitting `NO_TRANSCRIPT_AVAILABLE` instead of failing; downstream nodes handle that case by producing a shorter, clearly-flagged draft rather than crashing.

## Setup steps

1. **Import the workflow.**
2. **Email Trigger (IMAP) node** — set up an IMAP credential for `mdl@mydefilife.com` (host/port/username/password for whatever mail provider hosts that address) and select it. Since the digest is currently emailed to `blvck@brucelevick.com` (see note below), you'll want this listening on `mdl@mydefilife.com`'s inbox — meaning the digest itself needs to be sent there instead. Flagging this explicitly: **I changed the `youtube-crypto-digest` cloud routine to send the digest to `mdl@mydefilife.com` instead of `blvck@brucelevick.com`, so replies land in the mailbox this workflow watches.** Let me know if that's not what you wanted.
3. **Fetch Transcript (yt-dlp) node** — requires `yt-dlp` installed on the n8n host (`pip install yt-dlp` or equivalent) and the Execute Command node enabled (should be, for a self-hosted instance, but some hardened setups disable it — if this node errors immediately with a permissions/disabled-node message, that's why).
4. **Create WordPress Draft node** — set **Authentication → Generic Credential Type → Basic Auth**, credential = your mydefilife.com WordPress Application Password (username + the generated app password, not your normal login password).
5. Activate the workflow.

## Known risk / most likely thing to need adjusting

**The reply-parsing regex** (`Parse Reply & Select Video` node) is built and tested against a standard Gmail-style reply (verified locally with a realistic sample — number on its own line, then `On [date] ... wrote:` followed by `>`-quoted original text). If `mdl@mydefilife.com`'s actual mail client formats replies differently (different quote-boundary marker, different quoting style), this will need adjusting. The node's error output includes `rawTextPlain` (the full original email text) specifically so you can see the actual format and tell me what to fix if it doesn't parse correctly on a real reply.

## Notes

- Node types verified against current n8n source (`n8n-io/n8n` on GitHub) as of this file's creation, same rigor as the other MCP tools workflow.
- The Moonshot API key is embedded directly in the HTTP Request node's headers (not a separate credential) for simplicity — n8n's own builder guidance recommends a proper header-auth credential instead for security; move it there if you'd prefer, it's the same key already used elsewhere in these workflows.
- This is a *separate* workflow from `claude-mcp-tools.json` — it isn't an MCP server, it's triggered by an actual email arriving, not by Claude calling a tool.
