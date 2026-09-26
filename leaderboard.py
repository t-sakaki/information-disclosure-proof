"""
Aggregate on-chain tip attestations into leaderboards:
    - top tippers (by number of tips, broken down by currency)
    - top referrers (by number of referred tips, broken down by currency)

Tips can be in native ETH or an ERC-20 token (e.g. USDC), so totals are
kept separate per currency rather than summed together.

Reading and decoding of attestations is shared with the rest of the app via
ledger.py, so there is one definition of "what a tip attestation looks
like" instead of a copy per file.

Each entry also carries an optional "org_subname": an ENSv2-style name that
an organization (NPO, citizen ombudsman group, etc.) may have opted into via
the self-hosted OrgSubnameRegistryV2 (see ensv2_org.py). Individuals are
never required to register one, and entries without it fall back to
"ens_name" (legacy mainnet ENS reverse resolution) or the raw address.
"""
from collections import defaultdict

from ens_resolve import resolve_ens_name
from ensv2_org import resolve_org_name
from ledger import ZERO_ADDRESS, fetch_all_tips


def _empty_breakdown():
    return defaultdict(lambda: {"total_amount": 0.0, "count": 0})


def build_leaderboard() -> dict:
    tips = fetch_all_tips()

    tipper_breakdown: dict[str, dict] = defaultdict(_empty_breakdown)
    referrer_breakdown: dict[str, dict] = defaultdict(_empty_breakdown)
    tipper_tip_count: dict[str, int] = defaultdict(int)
    referrer_tip_count: dict[str, int] = defaultdict(int)

    for t in tips:
        tipper = t["tipper"]
        tipper_breakdown[tipper][t["currency"]]["total_amount"] += t["amount"]
        tipper_breakdown[tipper][t["currency"]]["count"] += 1
        tipper_tip_count[tipper] += 1

        if t["referrer"].lower() != ZERO_ADDRESS:
            referrer = t["referrer"]
            referrer_breakdown[referrer][t["currency"]]["total_amount"] += t["amount"]
            referrer_breakdown[referrer][t["currency"]]["count"] += 1
            referrer_tip_count[referrer] += 1

    def _to_list(breakdown_by_addr, count_by_addr, count_label):
        ranked = sorted(count_by_addr.items(), key=lambda kv: kv[1], reverse=True)
        result = []
        for addr, _n in ranked:
            breakdown = [
                {"currency": symbol, "amount": stats["total_amount"], "count": stats["count"]}
                for symbol, stats in breakdown_by_addr[addr].items()
            ]
            result.append(
                {
                    "address": addr,
                    "ens_name": resolve_ens_name(addr),
                    "org_subname": resolve_org_name(addr),
                    count_label: count_by_addr[addr],
                    "breakdown": breakdown,
                }
            )
        return result

    return {
        "top_tippers": _to_list(tipper_breakdown, tipper_tip_count, "tip_count"),
        "top_referrers": _to_list(referrer_breakdown, referrer_tip_count, "referral_count"),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(build_leaderboard(), indent=2, ensure_ascii=False))
