"""
Whisper doesn't know "Qobo" is a real word, so it guesses at
similarly-sounding real words instead. This fixes up the transcript
after STT, on top of biasing Whisper itself via the `prompt` field.

If you notice new mis-hearings in your chat history, just add them to
MISHEARD_AS below — no other code needs to change.
"""

import re

MISHEARD_AS = [
    "cabo",
    "cubo",
    "qwo",
    "kiwo",
    "thibbo",
    "kobo",
    "coo",
    "quo",
    "cobo",
    "koboh",
    "qoboh",
    "kobow",
    "qo",
]

# Longest-first so "koboh" is tried before "kobo" would partially match it.
_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(MISHEARD_AS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def fix_brand_name(transcript: str) -> str:
    """Replace known Qobo mis-hearings with the correct spelling."""
    return _PATTERN.sub("Qobo", transcript)