#!/usr/bin/env python3
"""
Push DeFi news / Twitter thread records to Airtable. Ported from ClawdBot's
airtable_defi_news.py, with the API token moved from a hardcoded literal to
AIRTABLE_API_KEY (the VPS version had it hardcoded in plaintext — do not repeat that).

Table IDs are fixed/known, not secret: reused as-is from the original.
"""

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

try:
    import certifi

    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = ssl.create_default_context()

BASE_ID = "appXtAYqbgcSO7gZx"
TABLE_ID_DEFI = "tblldosOWguFH7Wvc"
TABLE_ID_THREADS = "tblJSyznMQ19ciaiD"


class AirtableDeFiNews:
    def __init__(self, table_type: str = "defi"):
        table_id = TABLE_ID_THREADS if table_type == "threads" else TABLE_ID_DEFI
        self.base_url = f"https://api.airtable.com/v0/{BASE_ID}/{table_id}"
        api_key = os.environ.get("AIRTABLE_API_KEY")
        if not api_key:
            raise RuntimeError("AIRTABLE_API_KEY not set")
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def _request(self, data: dict = None, url: str = None, method: str = "POST") -> dict:
        req = urllib.request.Request(
            url or self.base_url,
            data=json.dumps(data).encode("utf-8") if data else None,
            headers=self.headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, context=_SSL_CONTEXT, timeout=30) as resp:
                return {"success": True, "data": json.loads(resp.read().decode())}
        except urllib.error.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.code}: {e.read().decode()}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_records(self, records: list[dict], channel: str = "Defi") -> dict:
        """records: list of {topic, title, content, why, source}."""
        if not records:
            return {"success": False, "error": "No records provided"}
        date_sent = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        payload = {
            "records": [
                {
                    "fields": {
                        "channel": r.get("channel", channel),
                        "topic": r["topic"],
                        "title": r["title"],
                        "content": r["content"],
                        "why": r["why"],
                        "source": r["source"],
                        "date_sent": date_sent,
                        "Channels": ["Telegram"],
                    }
                }
                for r in records
            ]
        }
        return self._request(data=payload)

    def get_recent_records(self, days: int = 7, max_records: int = 50) -> list[dict]:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        formula = f"IS_AFTER({{date_sent}}, '{cutoff}')"
        url = f"{self.base_url}?filterByFormula={urllib.parse.quote(formula)}&maxRecords={max_records}"
        result = self._request(url=url, method="GET")
        if not result["success"]:
            print(f"Warning: could not fetch recent records: {result['error']}")
            return []
        return [
            {
                "topic": r.get("fields", {}).get("topic", ""),
                "date_sent": r.get("fields", {}).get("date_sent", ""),
                "content": r.get("fields", {}).get("content", ""),
            }
            for r in result["data"].get("records", [])
        ]


def push_daily_defi_news(trend_data: list[dict], table_type: str = "defi", check_duplicates: bool = True) -> dict:
    from dedup import filter_duplicates

    airtable = AirtableDeFiNews(table_type=table_type)
    if check_duplicates:
        recent = airtable.get_recent_records(days=7)
        trend_data = filter_duplicates(trend_data, recent)
    if not trend_data:
        print("No unique topics to post after dedup filtering")
        return {"success": True, "data": {"records": []}, "filtered": True}
    result = airtable.create_records(trend_data)
    if result["success"]:
        print(f"Created {len(result['data'].get('records', []))} Airtable records")
    else:
        print(f"Failed to create records: {result['error']}")
    return result


if __name__ == "__main__":
    print("Import this module and call push_daily_defi_news([...]) with real records.")
    print("Requires AIRTABLE_API_KEY env var.")
