"""
Equivalent of `npm start` (node server.js).
Run with: python run.py
"""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8787"))
    print(f"Qobo voice agent backend running on http://localhost:{port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
