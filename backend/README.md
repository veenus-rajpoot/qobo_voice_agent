# Qobo Voice Agent — FastAPI Backend

This is a 1:1 port of the original Express.js backend to FastAPI. The API
routes, request/response shapes, and behavior are unchanged, so **your
existing React frontend works against this backend with no changes** — it
still expects `http://localhost:8787` with the same `/api/health`,
`/api/stt`, and `/api/chat` endpoints.

## What changed vs. the Express version

| Express (Node)                     | FastAPI (Python)                     |
|-------------------------------------|----------------------------------------|
| `server.js`                         | `app/main.py`                          |
| `routes/stt.js`                     | `app/routes/stt.py`                    |
| `routes/chat.js`                    | `app/routes/chat.py`                   |
| `dataStore.js`                      | `app/data_store.py`                    |
| `guard.js`                          | `app/guard.py`                         |
| `systemPrompt.js`                   | `app/system_prompt.py`                 |
| `groq-sdk` (JS)                     | `groq` (Python, `AsyncGroq`)           |
| `multer` (temp file on disk)        | `UploadFile` (in-memory bytes, no temp file needed) |
| `express.json()` body parsing       | Pydantic model (`ChatRequest`) — also gives free request validation |
| `cors()`                            | `CORSMiddleware`                        |

The TF-IDF retrieval, the off-topic keyword guard, and the system prompt
text are logically identical to the original — only the syntax changed.

## Setup

```bash
cd backend-fastapi
cp .env.example .env      # add your GROQ_API_KEY
pip install -r requirements.txt
python run.py             # runs on http://localhost:8787
```

Or with uvicorn directly (auto-reload for development):

```bash
uvicorn app.main:app --reload --port 8787
```

Interactive API docs are available for free at `http://localhost:8787/docs`
(Swagger UI) and `http://localhost:8787/redoc` — FastAPI generates these
automatically from the route/type definitions, something the Express version
didn't have.

## Endpoints

- `GET /api/health` → `{ "ok": true }`
- `POST /api/stt` — multipart form, field name `audio` → `{ "transcript": "..." }`
- `POST /api/chat` — JSON body `{ "transcript": "..." }` → `{ "answer": "...", "source": "..." }`

## Notes

- `CORSMiddleware` is currently wide open (`allow_origins=["*"]`), matching
  the original `cors()` default. Restrict this to your frontend's origin
  before deploying to production.
- The Supabase auth/history flow is untouched — that logic lives entirely in
  the frontend (`frontend/src/supabaseClient.js`), so nothing here needs to
  change for it to keep working.
- `data/qobo_data.json` is copied over unchanged; the TF-IDF index is built
  once at import time, same as the JS version building it once at server
  start.
