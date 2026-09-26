"""
Generalized on-chain ledger reader for information-disclosure-proof.

This is the single place that knows how to decode EAS attestations and
group them into a "case". Reads go straight to the EAS GraphQL indexer for
Base Sepolia -- there is no separate database -- so anything this module
returns is exactly what is on-chain, not something this server could have
edited.

Previously this decoding logic (schema field layout, token symbol lookup,
GraphQL queries) was duplicated between leaderboard.py and trending.py.
Both now import it from here, so there is one definition of "what a
disclosure-request attestation looks like" and "what a tip attestation
looks like".

A "case" today is a disclosure-request attestation (schema: EAS_SCHEMA_UID)
plus every tip/reaction attestation (schema: TIP_SCHEMA_UID) that
references it via refUID. If later stages of the same case are added --
the implementing agency's decision, an administrative appeal, the advisory
council's opinion, the final ruling -- each would register its own EAS
schema and plug into get_case() as another keyed list (e.g. case["decision"],
case["appeal"]), grouped by the same referenced UID. Readers of get_case()
would not need to change how they walk the result.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import requests
from dotenv import load_dotenv
from eth_abi import decode
from web3 import Web3

load_dotenv()

EAS_SCHEMA_UID = os.environ["EAS_SCHEMA_UID"]
TIP_SCHEMA_UID = os.environ["TIP_SCHEMA_UID"]
EASSCAN_GRAPHQL_URL = os.environ.get(
    "EASSCAN_GRAPHQL_URL", "https://base-sepolia.easscan.org/graphql"
)

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

KNOWN_TOKENS = {ZERO_ADDRESS: ("ETH", 18)}
_usdc = os.environ.get("USDC_CONTRACT_ADDRESS")
if _usdc:
    KNOWN_TOKENS[Web3.to_checksum_address(_usdc)] = ("USDC", 6)


def short_addr(addr: str) -> str:
    return addr[:6] + "..." + addr[-4:]


def format_amount(amount: float) -> str:
    """Format a token amount without scientific notation (e.g. a 0.000001 ETH
    tip must read "0.000001", not the "1e-06" that Python's :g gives it)."""
    text = f"{amount:.8f}".rstrip("0").rstrip(".")
    return text or "0"


def token_info(token_address: str) -> tuple[str, int]:
    checksummed = Web3.to_checksum_address(token_address)
    return KNOWN_TOKENS.get(checksummed, (short_addr(checksummed), 18))


def decode_request_data(data_hex: str) -> dict[str, Any]:
    raw = bytes.fromhex(data_hex[2:] if data_hex.startswith("0x") else data_hex)
    target_authority, request_type, doc_hash, summary = decode(
        ["string", "string", "bytes32", "string"], raw
    )
    return {
        "target_authority": target_authority,
        "request_type": request_type,
        "document_hash": "0x" + doc_hash.hex(),
        "summary": summary,
    }


def decode_tip_data(data_hex: str) -> dict[str, Any]:
    raw = bytes.fromhex(data_hex[2:] if data_hex.startswith("0x") else data_hex)
    token, referrer, amount, comment = decode(
        ["address", "address", "uint256", "string"], raw
    )
    return {"token": token, "referrer": referrer, "amount": amount, "comment": comment}


def _graphql(query: str, variables: dict) -> dict:
    response = requests.post(
        EASSCAN_GRAPHQL_URL, json={"query": query, "variables": variables}, timeout=15
    )
    response.raise_for_status()
    body = response.json()
    if body.get("errors"):
        raise RuntimeError(f"EAS GraphQL error: {body['errors']}")
    return body["data"]


REQUEST_BY_ID_QUERY = """
query RequestByUid($id: String!) {
  attestations(where: { id: { equals: $id } }) {
    id attester recipient time revoked data
  }
}
"""

REQUESTS_QUERY = """
query Requests($schemaId: String!) {
  attestations(where: { schemaId: { equals: $schemaId } }, orderBy: { time: desc }) {
    id attester recipient time revoked data
  }
}
"""

REQUESTS_BY_IDS_QUERY = """
query RequestsByIds($ids: [String!]!) {
  attestations(where: { id: { in: $ids } }) {
    id attester recipient time revoked data
  }
}
"""

TIPS_FOR_REQUEST_QUERY = """
query TipsForRequest($schemaId: String!, $refUID: String!) {
  attestations(
    where: { schemaId: { equals: $schemaId }, refUID: { equals: $refUID } }
    orderBy: { time: desc }
  ) {
    id attester refUID data time
  }
}
"""

ALL_TIPS_QUERY = """
query TipAttestations($schemaId: String!) {
  attestations(where: { schemaId: { equals: $schemaId } }, orderBy: { time: desc }) {
    attester refUID data time
  }
}
"""

RECENT_TIPS_QUERY = """
query RecentTips($schemaId: String!, $since: Int!) {
  attestations(
    where: { schemaId: { equals: $schemaId }, time: { gte: $since } }
    orderBy: { time: desc }
  ) {
    attester refUID data time
  }
}
"""


def _request_from_attestation(a: dict) -> dict[str, Any]:
    fields = decode_request_data(a["data"])
    return {
        "uid": a["id"],
        "requester": Web3.to_checksum_address(a["attester"]),
        "recorded_at": a["time"],
        **fields,
    }


def _tip_from_attestation(a: dict) -> dict[str, Any]:
    fields = decode_tip_data(a["data"])
    symbol, decimals = token_info(fields["token"])
    return {
        "uid": a.get("id"),
        "tipper": Web3.to_checksum_address(a["attester"]),
        "ref_uid": a.get("refUID"),
        "recorded_at": a["time"],
        "currency": symbol,
        "amount": fields["amount"] / (10**decimals),
        "referrer": Web3.to_checksum_address(fields["referrer"]),
        "comment": fields["comment"],
    }


def get_request(uid: str) -> Optional[dict[str, Any]]:
    data = _graphql(REQUEST_BY_ID_QUERY, {"id": uid})
    atts = data["attestations"]
    if not atts or atts[0].get("revoked"):
        return None
    return _request_from_attestation(atts[0])


def fetch_requests() -> list[dict[str, Any]]:
    data = _graphql(REQUESTS_QUERY, {"schemaId": EAS_SCHEMA_UID})
    return [
        _request_from_attestation(a) for a in data["attestations"] if not a.get("revoked")
    ]


def fetch_requests_by_ids(ids: list[str]) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}
    data = _graphql(REQUESTS_BY_IDS_QUERY, {"ids": ids})
    return {a["id"]: _request_from_attestation(a) for a in data["attestations"]}


def fetch_tips_for(ref_uid: str) -> list[dict[str, Any]]:
    data = _graphql(TIPS_FOR_REQUEST_QUERY, {"schemaId": TIP_SCHEMA_UID, "refUID": ref_uid})
    return [_tip_from_attestation(a) for a in data["attestations"]]


def fetch_all_tips() -> list[dict[str, Any]]:
    data = _graphql(ALL_TIPS_QUERY, {"schemaId": TIP_SCHEMA_UID})
    return [_tip_from_attestation(a) for a in data["attestations"]]


def fetch_recent_tips(since_unix: int) -> list[dict[str, Any]]:
    data = _graphql(RECENT_TIPS_QUERY, {"schemaId": TIP_SCHEMA_UID, "since": since_unix})
    return [_tip_from_attestation(a) for a in data["attestations"]]


def get_case(uid: str) -> Optional[dict[str, Any]]:
    """A case: the disclosure-request attestation plus every tip/reaction
    attestation that references it, read straight from the chain."""
    request = get_request(uid)
    if not request:
        return None
    tips = fetch_tips_for(uid)
    totals: dict[str, float] = {}
    for t in tips:
        totals[t["currency"]] = totals.get(t["currency"], 0) + t["amount"]
    return {
        "request": request,
        "tips": tips,
        "tip_count": len(tips),
        "totals": [{"currency": c, "amount": a} for c, a in totals.items()],
    }
