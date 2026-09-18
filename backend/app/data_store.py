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


def _tokenize(text: str) -> List[str]:
    """Tokenize text for simple TF-IDF retrieval."""
    return [w for w in _split(text) if len(w) > 2]


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


def _score_document(query_tokens: List[str], document: Dict) -> float:
    term_frequency: Dict[str, int] = {}
    for token in document["tokens"]:
        term_frequency[token] = term_frequency.get(token, 0) + 1

    score = 0.0
    for query_token in query_tokens:
        tf = term_frequency.get(query_token)
        if not tf:
            continue

        df = _document_frequency.get(query_token, 0)
        idf = math.log((len(_DOCUMENTS) + 1) / (df + 1)) + 1
        score += tf * idf

    return score


def search_company_context(query: str, top_k: int = 3) -> List[Dict]:
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


def get_relevant_context(query: str, top_k: int = 3) -> str:
    """Format retrieved pages for the LLM."""
    pages = search_company_context(query, top_k)

    if not pages:
        return "No relevant official Qobo information was found."

    return "\n\n---\n\n".join(
        f"### PAGE: {p['type']} ({p['source']})\n{p['title']}\n{p['content']}"
        for p in pages
    )
