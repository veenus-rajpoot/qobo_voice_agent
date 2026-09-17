"""
Port of backend/routes/stt.js

POST /api/stt
multipart/form-data, field name: "audio"
"""

import logging
import os

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from groq import AsyncGroq

logger = logging.getLogger("qobo.stt")

router = APIRouter()

groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))


@router.post("")
async def transcribe_audio(audio: UploadFile | None = File(None)):
    if audio is None:
        return JSONResponse(status_code=400, content={"error": "No audio file received."})

    original_name = audio.filename or "audio.webm"
    content_type = audio.content_type

    logger.info(
        "Received audio: originalName=%s mimeType=%s",
        original_name,
        content_type,
    )

    try:
        audio_bytes = await audio.read()

        transcription = await groq_client.audio.transcriptions.create(
            file=(original_name, audio_bytes),
            model="whisper-large-v3-turbo",
            response_format="json",
        )

        return {"transcript": transcription.text}

    except Exception as err:  # noqa: BLE001
        logger.exception("STT error")
        return JSONResponse(
            status_code=500,
            content={"error": "Transcription failed.", "details": str(err)},
        )
