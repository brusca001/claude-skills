#!/usr/bin/env python3
"""
Thin OpenAI-completions-compatible chat client (Moonshot/Kimi primary).
Self-contained duplicate of crypto-sentiment-defi's model_client.py — kept
per-skill rather than shared, so each skill's git-bootstrap in /schedule
stays independent (no cross-skill import path to manage).
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
        "default_model": "moonshot/kimi-k2.5",
        "key_env": "MOONSHOT_API_KEY",
    },
}


def chat(messages, backend: str = "moonshot", model: str = None, max_tokens: int = 800, temperature: float = 0.3) -> str:
    cfg = BACKENDS[backend]
    api_key = os.environ.get(cfg["key_env"])
    if not api_key:
        raise RuntimeError(f"{cfg['key_env']} not set")

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
