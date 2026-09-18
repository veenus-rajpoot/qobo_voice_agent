"""
Port of backend/routes/chat.js

POST /api/chat { transcript: string }
"""

import asyncio
import logging
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from groq import APIStatusError, AsyncGroq
from pydantic import BaseModel

from ..data_store import get_relevant_context
from ..guard import classify_relevance
from ..system_prompt import build_system_prompt

logger = logging.getLogger("qobo.chat")

router = APIRouter()

groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

REFUSAL = "I can only help with questions about Qobo. What would you like to know about our services?"

# Groq's free tier rate-limits the models behind groq/compound tightly
# enough that it can surface as a 413 (mislabeled — it's really a rate
# limit, not a payload-size issue). One short retry usually clears it.
RETRY_DELAY_SECONDS = 2


class ChatRequest(BaseModel):
    transcript: str | None = None


async def _create_completion(system_prompt: str, transcript: str):
    for attempt in range(2):
        try:
            return await groq_client.chat.completions.create(
                model="groq/compound",
                temperature=0.3,
                max_tokens=300,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript},
                ],
            )
        except APIStatusError as err:
            if err.status_code == 413 and attempt == 0:
                logger.warning(
                    "Groq returned 413 (likely a free-tier rate limit), retrying once in %ss",
                    RETRY_DELAY_SECONDS,
                )
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                continue
            raise


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
        # Retrieve only the most relevant Qobo information, trimmed to
        # keep each call comfortably under Groq's free-tier limits.
        relevant_context = get_relevant_context(transcript, top_k=2)

        # Build a small system prompt using the retrieved context
        system_prompt = build_system_prompt(relevant_context)

        logger.info("Retrieved context characters: %d", len(relevant_context))
        logger.info("Approx context tokens: %d", -(-len(relevant_context) // 4))

        # groq/compound has built-in web search: it decides on its own whether
        # a search is needed (e.g. dataset didn't cover the question) and
        # only pays the per-search cost when it actually searches.
        completion = await _create_completion(system_prompt, transcript)

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