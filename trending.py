"""
"急上昇" (trending) disclosure requests: rank requests by how much tip
support they've received recently, not by lifetime totals, so a request
that suddenly gets a wave of support surfaces immediately (TikTok-style
recency-weighted ranking instead of a static all-time leaderboard).

This reads tip attestations (refUID -> the disclosure-request attestation
they support) and the disclosure-request attestations themselves, both via
ledger.py, which is the single place decoding on-chain data for the whole
app (see ledger.py for why).
"""
import time
from collections import defaultdict

from ledger import ZERO_ADDRESS, fetch_recent_tips, fetch_requests_by_ids

ZERO_BYTES32 = "0x" + "0" * 64


def trending_requests(window_hours: int = 24, limit: int = 10) -> list[dict]:
    since = int(time.time()) - window_hours * 3600
    tips = fetch_recent_tips(since)

    scores: dict[str, dict] = defaultdict(
        lambda: {"tip_count": 0, "breakdown": defaultdict(float)}
    )
    for t in tips:
        ref_uid = t["ref_uid"]
        if not ref_uid or ref_uid == ZERO_BYTES32:
            continue
        scores[ref_uid]["tip_count"] += 1
        scores[ref_uid]["breakdown"][t["currency"]] += t["amount"]

    if not scores:
        return []

    ranked_uids = sorted(
        scores.keys(), key=lambda uid: scores[uid]["tip_count"], reverse=True
    )[:limit]

    requests_by_id = fetch_requests_by_ids(ranked_uids)

    results = []
    for uid in ranked_uids:
        req = requests_by_id.get(uid)
        if not req:
            continue
        results.append(
            {
                "attestation_uid": uid,
                "requester": req["requester"],
                "target_authority": req["target_authority"],
                "request_type": req["request_type"],
                "requested_documents": req["requested_documents"],
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
