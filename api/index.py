"""
Vercel entrypoint. Vercel's Python runtime looks for an ASGI/WSGI `app`
object in files under api/. The actual FastAPI app and all its routes live
in app.py at the repo root; this file only re-exports it so the same
codebase runs identically locally (`uvicorn app:app`) and on Vercel.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app  # noqa: E402
