"""
Port of backend/routes/chat.js

POST /api/chat { transcript: string }
"""

import logging
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from groq import AsyncGroq
from pydantic import BaseModel

from ..data_store import get_relevant_context
from ..guard import classify_relevance
from ..system_prompt import build_system_prompt

logger = logging.getLogger("qobo.chat")

router = APIRouter()

groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

REFUSAL = "I can only help with questions about Qobo. What would you like to know about our services?"


class ChatRequest(BaseModel):
    transcript: str | None = None


@router.post("")
async def chat(body: ChatRequest):
    transcript = body.transcript

    if not transcript or not isinstance(transcript, str):
        return JSONResponse(status_code=400, content={"error": "transcript is required."})

    # Cheap pre-filter for clearly off-topic questions
    guard_verdict = classify_relevance(transcript)

    if guard_verdict == "off_topic":
        return {"answer": REFUSAL, "source": "refused"}

    try:
        # Retrieve only the most relevant Qobo information
        relevant_context = get_relevant_context(transcript, 3)

        # Build a small system prompt using the retrieved context
        system_prompt = build_system_prompt(relevant_context)

        logger.info("Retrieved context characters: %d", len(relevant_context))
        logger.info("Approx context tokens: %d", -(-len(relevant_context) // 4))

        # groq/compound has built-in web search: it decides on its own whether
        # a search is needed (e.g. dataset didn't cover the question) and
        # only pays the per-search cost when it actually searches.
        completion = await groq_client.chat.completions.create(
            model="groq/compound",
            temperature=0.3,
            max_tokens=300,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript},
            ],
        )

        message = completion.choices[0].message if completion.choices else None
        raw_answer = message.content if message else None
        answer = raw_answer.strip() if raw_answer else REFUSAL

        used_web_search = bool(getattr(message, "executed_tools", None)) if message else False

        if answer == REFUSAL:
            source = "refused"
        elif used_web_search:
            source = "web_search"
        else:
            source = "company_data"

        return {"answer": answer, "source": source}

    except Exception:  # noqa: BLE001
        logger.exception("Chat error")
        return JSONResponse(status_code=500, content={"error": "Failed to generate an answer."})