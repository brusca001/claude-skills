#!/usr/bin/env python3
"""Self-contained Telegram send (doesn't depend on the local `telegram` skill being present)."""

import json
import os
import ssl
import sys
import urllib.request


def send(message: str, bot_token: str = None, chat_id: str = None) -> bool:
    bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set — printing instead:")
        print(message)
        return False

    if not message.startswith("@MrJoben_bot"):
        message = f"@MrJoben_bot {message}"

    payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "HTML"}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl.create_default_context()) as resp:
            result = json.loads(resp.read().decode())
            return result.get("ok", False)
    except Exception as e:
        print(f"Telegram send failed: {e}")
        print(message)
        return False


if __name__ == "__main__":
    text = sys.stdin.read() if not sys.stdin.isatty() else (sys.argv[1] if len(sys.argv) > 1 else "")
    if not text:
        print("Usage: echo 'message' | python send_telegram.py")
        sys.exit(1)
    ok = send(text)
    print("Sent" if ok else "Failed / printed above")
