#!/usr/bin/env python3
"""Jaccard-similarity duplicate detection, ported from ClawdBot's airtable_defi_news.py."""

STOP_WORDS = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were"}


def is_similar_topic(new_topic: str, existing_topic: str, threshold: float = 0.6) -> bool:
    if new_topic.lower().strip() == existing_topic.lower().strip():
        return True
    if new_topic.lower().strip()[:50] == existing_topic.lower().strip()[:50]:
        return True

    new_words = set(new_topic.lower().split()) - STOP_WORDS
    existing_words = set(existing_topic.lower().split()) - STOP_WORDS
    if not new_words or not existing_words:
        return False

    intersection = len(new_words & existing_words)
    union = len(new_words | existing_words)
    return (intersection / union if union > 0 else 0) >= threshold


def filter_duplicates(new_records: list[dict], existing_records: list[dict], topic_key: str = "topic") -> list[dict]:
    """existing_records: list of dicts with at least topic_key. Returns new_records minus near-duplicates."""
    filtered = []
    for new_record in new_records:
        new_topic = new_record.get(topic_key, "")
        if any(is_similar_topic(new_topic, existing.get(topic_key, "")) for existing in existing_records):
            print(f"Skipping duplicate: '{new_topic[:50]}...'")
            continue
        filtered.append(new_record)
    return filtered
