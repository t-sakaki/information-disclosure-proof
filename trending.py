"""
"急上昇" (trending) disclosure requests: rank requests by how much tip
support they've received recently, not by lifetime totals, so a request
that suddenly gets a wave of support surfaces immediately (TikTok-style
recency-weighted ranking instead of a static all-time leaderboard).

This reads tip attestations (refUID -> the disclosure-request attestation
they support) and the disclosure-request attestations themselves, both
from the EAS GraphQL indexer, and joins them client-side.
"""
import os
import time
from collections import defaultdict

import requests
from dotenv import load_dotenv
from eth_abi import decode
from web3 import Web3

from leaderboard import _token_info

load_dotenv()

EAS_SCHEMA_UID = os.environ["EAS_SCHEMA_UID"]
TIP_SCHEMA_UID = os.environ["TIP_SCHEMA_UID"]
EASSCAN_GRAPHQL_URL = os.environ.get(
    "EASSCAN_GRAPHQL_URL", "https://base-sepolia.easscan.org/graphql"
)

TIPS_QUERY = """
query RecentTips($schemaId: String!, $since: Int!) {
  attestations(
    where: { schemaId: { equals: $schemaId }, time: { gte: $since } }
    orderBy: { time: desc }
  ) {
    attester
    refUID
    data
    time
  }
}
"""

REQUESTS_QUERY = """
query RequestsByUid($ids: [String!]!) {
  attestations(where: { id: { in: $ids } }) {
    id
    attester
    data
    time
  }
}
"""


def _decode_tip_data(data_hex: str):
    raw = bytes.fromhex(data_hex[2:] if data_hex.startswith("0x") else data_hex)
    token, referrer, amount, comment = decode(
        ["address", "address", "uint256", "string"], raw
    )
    return token, referrer, amount, comment


def _decode_request_data(data_hex: str):
    raw = bytes.fromhex(data_hex[2:] if data_hex.startswith("0x") else data_hex)
    target_authority, request_type, doc_hash, summary = decode(
        ["string", "string", "bytes32", "string"], raw
    )
    return target_authority, request_type, summary


def _graphql(query: str, variables: dict) -> dict:
    response = requests.post(
        EASSCAN_GRAPHQL_URL, json={"query": query, "variables": variables}, timeout=15
    )
    response.raise_for_status()
    return response.json()["data"]


def trending_requests(window_hours: int = 24, limit: int = 10) -> list[dict]:
    since = int(time.time()) - window_hours * 3600
    tips = _graphql(TIPS_QUERY, {"schemaId": TIP_SCHEMA_UID, "since": since})[
        "attestations"
    ]

    scores: dict[str, dict] = defaultdict(
        lambda: {"tip_count": 0, "breakdown": defaultdict(float)}
    )
    for t in tips:
        ref_uid = t["refUID"]
        if not ref_uid or ref_uid == "0x" + "0" * 64:
            continue
        token, _referrer, amount, _comment = _decode_tip_data(t["data"])
        symbol, decimals = _token_info(token)
        scores[ref_uid]["tip_count"] += 1
        scores[ref_uid]["breakdown"][symbol] += amount / (10**decimals)

    if not scores:
        return []

    ranked_uids = sorted(
        scores.keys(), key=lambda uid: scores[uid]["tip_count"], reverse=True
    )[:limit]

    requests_data = _graphql(REQUESTS_QUERY, {"ids": ranked_uids})["attestations"]
    requests_by_id = {r["id"]: r for r in requests_data}

    results = []
    for uid in ranked_uids:
        req = requests_by_id.get(uid)
        if not req:
            continue
        target_authority, request_type, summary = _decode_request_data(req["data"])
        results.append(
            {
                "attestation_uid": uid,
                "requester": Web3.to_checksum_address(req["attester"]),
                "target_authority": target_authority,
                "request_type": request_type,
                "summary": summary,
                "tip_count": scores[uid]["tip_count"],
                "breakdown": [
                    {"currency": symbol, "amount": amount}
                    for symbol, amount in scores[uid]["breakdown"].items()
                ],
            }
        )
    return results


if __name__ == "__main__":
    import json

    print(json.dumps(trending_requests(), indent=2, ensure_ascii=False))
