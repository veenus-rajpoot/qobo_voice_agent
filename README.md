# Qobo Voice Agent

A voice-in, voice-out assistant for Qobo. Users ask a question by speaking, the
agent answers from your scraped website data (falling back to general
knowledge for genuine-but-uncovered business questions, and refusing anything
unrelated), and every exchange is saved to the signed-in user's history via
Supabase.

## How it works

```
Browser mic → MediaRecorder → POST /api/stt (Groq Whisper) → transcript
                                        │
                                        ▼
                         POST /api/chat (relevance guard + Groq Llama 3.3 70B,
                         answering only from qobo_data.json, or refusing)
                                        │
                                        ▼
                    Browser SpeechSynthesis speaks the answer out loud
                                        │
                                        ▼
                 Row saved to Supabase `messages` table (RLS: own rows only)
```

Your scraped 13-page dataset (`backend/app/data/qobo_data.json`) is small
enough (~40KB) to inject directly into the system prompt on every call — no
vector DB needed yet. If you scrape more pages later and it stops fitting
comfortably, that's the point to move to embeddings + Supabase pgvector.

Domain restriction is enforced two ways ("belt and suspenders"):
1. A cheap keyword-overlap guard (`backend/app/guard.py`) catches obviously
   off-topic or jailbreak-shaped text before it reaches the LLM.
2. The system prompt (`backend/app/system_prompt.py`) gives the model the
   full rule set — answer from data, flag general-knowledge fallback, or
   refuse.

> **Backend note:** the backend is a FastAPI (Python) app — see
> `backend/README.md` for details on the port from the original Express
> version. Interactive API docs are auto-generated at `/docs` once it's
> running.

## Setup

### 1. Get free API keys
- **Groq** (STT + LLM, generous free tier): https://console.groq.com/keys
- **Supabase** (auth + history, free tier): https://supabase.com — create a
  project, then run `supabase/schema.sql` in the SQL Editor.
- Enable Google sign-in: Supabase Dashboard → Authentication → Providers →
  Google (you'll need a Google OAuth client ID/secret from Google Cloud
  Console). Add `http://localhost:5173` under Authentication → URL
  Configuration → Redirect URLs.

### 2. Backend
```bash
cd backend
cp .env.example .env      # add your GROQ_API_KEY
pip install -r requirements.txt
python run.py              # runs on http://localhost:8787
```

### 3. Frontend
```bash
cd frontend
cp .env.example .env      # add your Supabase URL + anon key
npm install
npm run dev                # runs on http://localhost:5173
```

Open http://localhost:5173, sign in with Google, tap the mic, and ask a
question about Qobo.

## Notes on the free stack
- **TTS** uses the browser's built-in `speechSynthesis` — zero cost, no API
  key, works everywhere except very old browsers. Swap in ElevenLabs later
  (`frontend/src/components/MicRecorder.jsx`, `speak()`) once you have paying
  users who justify the ~10 min/month free-tier limit.
- **STT + LLM** both run on Groq's free tier, which is rate-limited (not
  unlimited) but effectively free at low-to-moderate traffic.
- Recording uses `MediaRecorder`, which needs HTTPS or `localhost` — it won't
  work over plain HTTP on a real domain.

## Where to go next
- Swap browser TTS for ElevenLabs/Cartesia if you want a more natural voice.
- If the site grows past ~50-100 pages, chunk `qobo_data.json` and move to
  Supabase pgvector for retrieval instead of stuffing everything into the
  prompt.
- Add a `conversations` table if you want to group messages into sessions
  rather than one flat list.
