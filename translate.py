"""
Best-effort machine translation of on-chain Japanese fields (target
authority, request type, summary) into English, for the Case preview
page's "Request details" card.

The actual content requesters attest on-chain is in Japanese, since
Japanese Freedom-of-Information requests are addressed to Japanese
authorities. For an English-speaking audience (ETHGlobal judges,
international supporters), the Case page shows this machine translation
alongside the original text -- it is not a substitute for the original,
and the UI always labels it as machine-translated.

Uses the Gemini API (gemini-flash-lite, chosen for translation being a
short/cheap/latency-sensitive task) when GEMINI_API_KEY is configured,
since it noticeably outperforms generic MT on Japanese administrative/
legal phrasing (agency names, request-type terminology). Falls back to
MyMemory's free, keyless translation API when no key is set or the Gemini
call fails, so the feature still works without any configuration. Either
way this is a display-only convenience the product doesn't depend on: if
both are unavailable, the page still works and just shows the Japanese
original without a translation. Results are cached in-memory per process
since on-chain attestation content never changes once recorded.
"""
from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-flash-lite-latest"
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

MYMEMORY_ENDPOINT = "https://api.mymemory.translated.net/get"

_cache: dict[str, str | None] = {}

_PROMPT_PREFIX = (
    "Translate this Japanese text from a Freedom-of-Information disclosure "
    "request into natural, concise English. It may be an agency name, a "
    "request-type label, or a summary of requested documents. Reply with "
    "ONLY the translation, no preamble, no quotes.\n\n"
)


def _translate_with_gemini(text: str) -> str | None:
    if not GEMINI_API_KEY:
        return None
    try:
        resp = requests.post(
            GEMINI_ENDPOINT,
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": _PROMPT_PREFIX + text}]}]},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        candidate = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return candidate or None
    except Exception:
        return None


def _translate_with_mymemory(text: str) -> str | None:
    if len(text) > 500:
        return None
    try:
        resp = requests.get(
            MYMEMORY_ENDPOINT,
            params={"q": text, "langpair": "ja|en"},
            timeout=6,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("responseStatus") != 200:
            return None
        candidate = data.get("responseData", {}).get("translatedText", "").strip()
        # MyMemory returns the input back unchanged (or an error string
        # prefixed like "MYMEMORY WARNING") when it can't translate --
        # treat those as "no translation" rather than showing junk.
        if candidate and candidate != text and "MYMEMORY WARNING" not in candidate.upper():
            return candidate
        return None
    except Exception:
        return None


def translate_to_english(text: str) -> str | None:
    """Returns an English translation of `text` (Gemini if configured,
    else MyMemory), or None if translation is unavailable (network error,
    rate limit, empty input). Never raises."""
    if not text or not text.strip():
        return None
    if text in _cache:
        return _cache[text]

    translated = _translate_with_gemini(text) or _translate_with_mymemory(text)
    _cache[text] = translated
    return translated
