#!/usr/bin/env python3
"""
Thin OpenAI-completions-compatible chat client. Switches base URL/key by MODEL_BACKEND.
Pure stdlib (urllib) — no openai/requests package needed, keeps the /schedule bootstrap simple.
"""

import json
import os
import ssl
import urllib.request

try:
    import certifi

    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = None

BACKENDS = {
    "moonshot": {
        "base_url": "https://api.moonshot.ai/v1",
        "default_model": "kimi-k2.5",
        "key_env": "MOONSHOT_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "anthropic/claude-haiku-4.5",
        "key_env": "OPENROUTER_API_KEY",
    },
}


def chat(messages, backend: str = None, model: str = None, max_tokens: int = 3000, temperature: float = 1.0) -> str:
    # kimi-k2.5 only accepts temperature=1 ("invalid temperature: only 1 is allowed for this model")
    # kimi-k2.5 is a reasoning model — it spends tokens on hidden reasoning_content before the
    # visible "content" field, so max_tokens needs real headroom or content comes back empty.
    """Returns the assistant's text reply. Raises on failure — caller decides fallback behavior."""
    backend = backend or os.environ.get("MODEL_BACKEND", "moonshot")
    cfg = BACKENDS[backend]
    api_key = os.environ.get(cfg["key_env"])
    if not api_key:
        raise RuntimeError(f"{cfg['key_env']} not set (backend={backend})")

    payload = {
        "model": model or cfg["default_model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        f"{cfg['base_url']}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60, context=_SSL_CONTEXT) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


if __name__ == "__main__":
    import sys

    prompt = sys.argv[1] if len(sys.argv) > 1 else "Say hi in 5 words."
    print(chat([{"role": "user", "content": prompt}]))
