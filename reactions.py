"""
Off-chain reaction counts for a Case: three fixed, action-oriented
reactions (not free-text, to avoid this becoming a target for abuse),
modeled on Civic Lens's ledger_reactions.py:

    watch          - 見守る            - watching how the authority responds
    want_to_know   - 私も知りたい       - also interested in this document
    fork_local     - 自分の自治体でも   - want to file the same request elsewhere

Unlike tips, reactions are not recorded as EAS attestations: requiring a
real transaction (even a cheap testnet one) for a single emoji click is
bad UX and doesn't need blockchain-level permanence for a soft signal like
this. Instead, the wallet signs a free off-chain message (personal_sign,
no gas, no transaction) that proves address ownership for this specific
action; the server verifies that signature and stores a dedupe/toggle
entry in Upstash Redis (REST API -- no persistent connection needed,
which fits Vercel's serverless functions). This is the same
signature-based-auth-plus-off-chain-storage pattern Snapshot uses for
gasless DAO voting.

Requires UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN. If unset, the
feature degrades to "no reactions yet, can't react" rather than breaking
the rest of the app -- consistent with how CHAIN_PRIVATE_KEY and
GEMINI_API_KEY are treated elsewhere in this project.
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

import requests
from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct

load_dotenv()

UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "").rstrip("/")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

REACTION_TYPES = ["watch", "want_to_know", "fork_local"]
REACTION_LABELS = {
    "watch": {"emoji": "\U0001F440", "label_en": "Watching", "label_ja": "見守る"},
    "want_to_know": {"emoji": "\U0001F64B", "label_en": "I want to know too", "label_ja": "私も知りたい"},
    "fork_local": {"emoji": "\U0001F501", "label_en": "In my area too", "label_ja": "自分の自治体でも"},
}

# Signed messages expire quickly so a captured signature can't be replayed
# long after the fact (there's no transaction/nonce to invalidate it with,
# since this never touches the chain).
MESSAGE_MAX_AGE_SECONDS = 300


class ReactionsNotConfigured(RuntimeError):
    pass


def reactions_available() -> bool:
    return bool(UPSTASH_URL and UPSTASH_TOKEN)


def _redis(*command: str) -> Any:
    if not reactions_available():
        raise ReactionsNotConfigured(
            "UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN is not configured."
        )
    path = "/".join(requests.utils.quote(str(c), safe="") for c in command)
    resp = requests.post(
        f"{UPSTASH_URL}/{path}",
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
        timeout=8,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("error"):
        raise RuntimeError(f"Upstash error: {body['error']}")
    return body.get("result")


def build_message(uid: str, reaction: str, timestamp: int) -> str:
    """Must match exactly what the browser signs in case_page.py's JS --
    any drift here breaks signature verification."""
    return (
        "Civic Disclosure Tip reaction (no gas, not a transaction)\n"
        f"case: {uid.lower()}\n"
        f"reaction: {reaction}\n"
        f"timestamp: {timestamp}"
    )


def _set_key(uid: str, reaction: str) -> str:
    return f"reactors:{uid.lower()}:{reaction}"


def get_reactions(uid: str, address: Optional[str] = None) -> dict[str, dict]:
    if not reactions_available():
        return {t: {**REACTION_LABELS[t], "count": 0, "mine": False} for t in REACTION_TYPES}
    result = {}
    for t in REACTION_TYPES:
        key = _set_key(uid, t)
        count = _redis("SCARD", key) or 0
        mine = bool(address) and bool(_redis("SISMEMBER", key, address.lower()))
        result[t] = {**REACTION_LABELS[t], "count": int(count), "mine": mine}
    return result


def toggle_reaction(uid: str, reaction: str, address: str, timestamp: int, signature: str) -> dict[str, dict]:
    if reaction not in REACTION_TYPES:
        raise ValueError(f"Unsupported reaction: {reaction}")
    if abs(time.time() - timestamp) > MESSAGE_MAX_AGE_SECONDS:
        raise ValueError("Signed message has expired -- please try again.")

    message = build_message(uid, reaction, timestamp)
    recovered = Account.recover_message(encode_defunct(text=message), signature=signature)
    if recovered.lower() != address.lower():
        raise ValueError("Signature does not match the given address.")

    key = _set_key(uid, reaction)
    already = _redis("SISMEMBER", key, address.lower())
    if already:
        _redis("SREM", key, address.lower())
    else:
        _redis("SADD", key, address.lower())

    return get_reactions(uid, address)
