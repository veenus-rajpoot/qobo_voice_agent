"""
Port of backend/guard.js

Fast pre-filter, not the final decision — the LLM still applies the full
instruction set. It just makes it harder for a jailbreak attempt in the
transcript to talk the model out of the refusal rule.
"""

import re
from .data_store import get_keyword_index

KEYWORDS = get_keyword_index()

# Obvious off-topic requests that a jailbreak-y transcript likes to hide behind.
OBVIOUS_OFF_TOPIC = [
    re.compile(r"weather", re.I),
    re.compile(r"\bjoke\b", re.I),
    re.compile(r"cricket|football|ipl score", re.I),
    re.compile(r"who is the (prime minister|president)", re.I),
    re.compile(r"write (a )?(poem|song|story)", re.I),
    re.compile(r"ignore (your|all) (previous|prior) instructions", re.I),
    re.compile(r"you are now", re.I),
    re.compile(r"pretend (you|to) are", re.I),
    re.compile(r"system prompt", re.I),
]

_SPLIT_RE = re.compile(r"[^a-z0-9]+")


def classify_relevance(transcript: str) -> str:
    """Returns one of: "on_topic", "maybe", "off_topic" """
    text = transcript.lower()

    if any(pattern.search(text) for pattern in OBVIOUS_OFF_TOPIC):
        return "off_topic"

    words = [w for w in _SPLIT_RE.split(text) if len(w) > 3]
    if not words:
        return "maybe"

    hits = sum(1 for w in words if w in KEYWORDS)
    ratio = hits / len(words)

    if ratio >= 0.15 or hits >= 2:
        return "on_topic"
    return "maybe"
