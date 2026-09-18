"""
Port of backend/dataStore.js

Loads the scraped Qobo dataset once at import time, builds a tiny
TF-IDF index over it, and exposes helpers to:
- fetch all company context (debug only, never send this whole blob to the LLM)
- build a keyword set used by the relevance guard
- retrieve the top-K most relevant pages for a given query
"""

import json
import math
import re
from pathlib import Path
from typing import List, Dict, Set

DATA_PATH = Path(__file__).parent / "data" / "qobo_data.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    _RAW = json.load(f)

# Keep the useful fields from each page.
PAGES: List[Dict] = [
    {
        "id": index,
        "type": p.get("type", ""),
        "source": p.get("source", ""),
        "title": p.get("title", ""),
        "headings": p.get("headings", []) or [],
        "content": p.get("content", ""),
    }
    for index, p in enumerate(_RAW)
]

_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _split(text: str) -> List[str]:
    return [w for w in _TOKEN_RE.split(text.lower()) if w]


def get_company_context() -> str:
    """
    Return all company data.
    Kept for debugging / inspection.
    DO NOT send this entire result to the LLM.
    """
    return "\n\n---\n\n".join(
        f"### PAGE: {p['type']} ({p['source']})\n{p['title']}\n{p['content']}"
        for p in PAGES
    )


def get_keyword_index() -> Set[str]:
    """Very small keyword index used by the relevance guard."""
    words: Set[str] = set()

    for p in PAGES:
        text = f"{p['title']} {' '.join(p['headings'])} {p['content']}"
        for w in _split(text):
            if len(w) > 3:
                words.add(w)

    words.add("qobo")
    return words


def _stem(word: str) -> str:
    """
    Very lightweight plural stemming: "subscriptions" -> "subscription",
    "plans" -> "plan". Applied identically when indexing documents and
    when tokenizing a query, so a singular/plural mismatch between a
    question and the source page no longer causes a miss.
    """
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _tokenize(text: str) -> List[str]:
    """Tokenize text for simple TF-IDF retrieval."""
    return [_stem(w) for w in _split(text) if len(w) > 2]


# Build TF-IDF index once at import time.
_DOCUMENTS = [
    {
        "page": page,
        "tokens": _tokenize(f"{page['title']} {' '.join(page['headings'])} {page['content']}"),
    }
    for page in PAGES
]

_document_frequency: Dict[str, int] = {}
for doc in _DOCUMENTS:
    for word in set(doc["tokens"]):
        _document_frequency[word] = _document_frequency.get(word, 0) + 1


def _idf(term: str) -> float:
    df = _document_frequency.get(term, 0)
    return math.log((len(_DOCUMENTS) + 1) / (df + 1)) + 1


def _build_document_vector(tokens: List[str]) -> Dict[str, float]:
    """
    Log-scaled TF-IDF, L2-normalized.

    Log-scaling the term frequency (1 + log(count)) instead of using the
    raw count stops a word repeated many times (e.g. "qobo" on the
    homepage) from dominating just by sheer repetition. L2-normalizing
    each document's vector then stops long/word-heavy pages from
    outscoring short, specific pages purely because they have more words
    overall. Together, these make a page's score reflect how *focused*
    it is on the query terms, not just how long or repetitive it is.
    """
    term_frequency: Dict[str, int] = {}
    for token in tokens:
        term_frequency[token] = term_frequency.get(token, 0) + 1

    weights = {
        term: (1 + math.log(count)) * _idf(term)
        for term, count in term_frequency.items()
    }

    norm = math.sqrt(sum(w * w for w in weights.values())) or 1.0
    return {term: w / norm for term, w in weights.items()}


for doc in _DOCUMENTS:
    doc["vector"] = _build_document_vector(doc["tokens"])


def _score_document(query_tokens: List[str], document: Dict) -> float:
    vector = document["vector"]
    score = 0.0
    for query_token in set(query_tokens):
        score += vector.get(query_token, 0.0) * _idf(query_token)
    return score


def _truncate(text: str, max_chars: int) -> str:
    """Cut text to max_chars, breaking on a word boundary, with an ellipsis."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last_space = cut.rfind(" ")
    if last_space > 0:
        cut = cut[:last_space]
    return cut + "…"


def search_company_context(query: str, top_k: int = 2) -> List[Dict]:
    """Retrieve the most relevant Qobo pages for a user question."""
    query_tokens = _tokenize(query)

    if not query_tokens:
        return []

    results = [
        {"page": doc["page"], "score": _score_document(query_tokens, doc)}
        for doc in _DOCUMENTS
    ]
    results = [r for r in results if r["score"] > 0]
    results.sort(key=lambda r: r["score"], reverse=True)

    return [r["page"] for r in results[:top_k]]


def get_relevant_context(query: str, top_k: int = 2, max_chars_per_page: int = 900) -> str:
    """
    Format retrieved pages for the LLM.

    Trims each page's content to max_chars_per_page. Groq's free tier
    rate-limits the underlying models behind groq/compound tightly enough
    that a handful of full pages can trip a (misleadingly-labeled) 413
    error — keeping each call's context small avoids that.
    """
    pages = search_company_context(query, top_k)

    if not pages:
        return "No relevant official Qobo information was found."

    return "\n\n---\n\n".join(
        f"### PAGE: {p['type']} ({p['source']})\n{p['title']}\n"
        f"{_truncate(p['content'], max_chars_per_page)}"
        for p in pages
    )