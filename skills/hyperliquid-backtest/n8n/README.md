# Claude MCP Tools workflow for n8n

Two files to import — **in this order**:

1. **`send-email-subworkflow.json`** — a plain, ordinary workflow: Execute Workflow Trigger → Send Email node. This is a *real* node on a *real* canvas, so you can click it and pick your SMTP credential normally.
2. **`claude-mcp-tools.json`** — the MCP Server workflow with two tools: `get_hyperliquid_candles` and `send_email` (which calls workflow #1).

**If you already imported an earlier version and got "No recipients defined" errors**: the fix is in `send-email-subworkflow.json`'s trigger node — see "Known issue, fixed" below. Update just that one node rather than re-importing/re-linking everything.

## Setup steps

1. **Import `send-email-subworkflow.json` first**. Open its "Send Email" node:
   - Set **From Email** to your actual sending address (placeholder: `REPLACE_WITH_YOUR_SMTP_FROM_ADDRESS@example.com`).
   - Set **Credential** to your existing SMTP credential.
   - Also check the **"When Executed by Another Workflow"** trigger node: **Input data mode** should be **"Define using fields below"** (not "Accept all data"), with three fields defined: `to` (String), `subject` (String), `body` (String). This is what makes the fields visible/mappable to the calling tool — "Accept all data" mode has no defined schema, so nothing gets through regardless of what the caller sends.
   - Save/activate this workflow.
2. **Import `claude-mcp-tools.json`**. Open its `send_email` node:
   - **Workflow** field is empty — click it and select "Send Email via SMTP" (the workflow you just imported in step 1) from the dropdown.
   - A **Workflow Inputs** section appears showing `to`/`subject`/`body` (loaded from the sub-workflow's defined schema). For each field, click the **✨ button** next to it to let the AI/model provide the value per call — this is the step that's easy to miss, and without it the tool has literally no parameters to work with.
3. **Activate `claude-mcp-tools.json`**, copy the production MCP URL from the "MCP Server Trigger" node (test vs. production toggle — use production).
4. **Add it as a custom connector**: `https://claude.ai/customize/connectors` → Add connector → paste the MCP URL.
5. Tell Claude once connected — it'll wire the `/schedule` routines to use `send_email`/`get_hyperliquid_candles`.

## Known issue, fixed

**Symptom**: `send_email` fails every time with `"No recipients defined"`, no matter what parameter names the caller tries (`to`, `recipient`, `toEmail`, etc.).

**Cause**: the sub-workflow's Execute Workflow Trigger was left on `inputSource: passthrough` ("Accept all data"). n8n's own UI explains this directly if you open the `send_email` node in `claude-mcp-tools.json`: *"This sub-workflow is set up to receive all input data, without specific inputs the Agent will not be able to pass data to this tool."* Passthrough mode has no defined field schema, so the parent tool node has nothing to map — the AI is calling a tool with zero real parameters, regardless of what key names it guesses.

**Fix** (already applied in this repo's `send-email-subworkflow.json`, current as of this file's last update): switch the trigger to `inputSource: workflowInputs` with three explicitly defined String fields — `to`, `subject`, `body`. Once defined, the parent `send_email` node's "Workflow Inputs" section can load and map them, and marking each with the ✨ "let AI fill this in" option actually exposes them to the calling model.

## What's in each workflow

**`send-email-subworkflow.json`** ("Send Email via SMTP"):
- Execute Workflow Trigger — `inputSource: workflowInputs`, three defined fields: `to`, `subject`, `body` (all String)
- Send Email node, reading them via `{{ $json.to }}` / `{{ $json.subject }}` / `{{ $json.body }}`

**`claude-mcp-tools.json`** ("Claude MCP Tools"):
- **MCP Server Trigger** (`path: claude-tools`) — the entry point, no auth by default
- **`get_hyperliquid_candles`** (HTTP Request Tool) — calls `https://api.hyperliquid-testnet.xyz/info` directly with `coin`/`interval`/`startTime`/`endTime` as model-fillable placeholders. No credential needed (public endpoint).
- **`send_email`** (Workflow Tool, `source: database`) — references workflow #1 by ID, which you select manually after both are imported (workflow IDs aren't portable across n8n instances, so this can't be pre-filled)

## Notes

- Node versions used were verified against the current n8n source (`n8n-io/n8n` on GitHub) as of this skill's creation — if your n8n version is old enough not to have `mcpTrigger` (added in a relatively recent release), the import may fail; update n8n first if so.
