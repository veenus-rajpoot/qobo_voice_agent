"""
Port of backend/server.js
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import chat, stt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qobo.server")

app = FastAPI(title="Qobo Voice Agent Backend")

# Mirrors `app.use(cors())` in the Express app (open CORS).
# Tighten `allow_origins` to your frontend's URL before shipping to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"ok": True}


app.include_router(stt.router, prefix="/api/stt", tags=["stt"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.on_event("startup")
async def on_startup():
    if not os.getenv("GROQ_API_KEY"):
        logger.warning(
            "WARNING: GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
        )
