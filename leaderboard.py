"""
Aggregate on-chain tip attestations into leaderboards:
    - top tippers (by number of tips, broken down by currency)
    - top referrers (by number of referred tips, broken down by currency)

Tips can be in native ETH or an ERC-20 token (e.g. USDC), so totals are
kept separate per currency rather than summed together.

Data is read directly from the EAS GraphQL indexer for Base Sepolia, so no
separate database is needed -- the chain itself is the source of truth.
"""
import os
from collections import defaultdict

import requests
from dotenv import load_dotenv
from eth_abi import decode
from web3 import Web3

from ens_resolve import resolve_ens_name

load_dotenv()

TIP_SCHEMA_UID = os.environ["TIP_SCHEMA_UID"]
EASSCAN_GRAPHQL_URL = os.environ.get(
    "EASSCAN_GRAPHQL_URL", "https://base-sepolia.easscan.org/graphql"
)

QUERY = """
query TipAttestations($schemaId: String!) {
  attestations(where: { schemaId: { equals: $schemaId } }, orderBy: { time: desc }) {
    attester
    data
    time
  }
}
"""

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

KNOWN_TOKENS = {ZERO_ADDRESS: ("ETH", 18)}
_usdc = os.environ.get("USDC_CONTRACT_ADDRESS")
if _usdc:
    KNOWN_TOKENS[Web3.to_checksum_address(_usdc)] = ("USDC", 6)


def short_addr(addr: str) -> str:
    return addr[:6] + "..." + addr[-4:]


def _token_info(token_address: str) -> tuple[str, int]:
    checksummed = Web3.to_checksum_address(token_address)
    return KNOWN_TOKENS.get(checksummed, (short_addr(checksummed), 18))


def _decode_tip_data(data_hex: str) -> tuple[str, str, int, str]:
    raw = bytes.fromhex(data_hex[2:] if data_hex.startswith("0x") else data_hex)
    token, referrer, amount, comment = decode(
        ["address", "address", "uint256", "string"], raw
    )
    return token, referrer, amount, comment


def fetch_tip_attestations() -> list[dict]:
    response = requests.post(
        EASSCAN_GRAPHQL_URL,
        json={"query": QUERY, "variables": {"schemaId": TIP_SCHEMA_UID}},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["data"]["attestations"]


def _empty_breakdown():
    return defaultdict(lambda: {"total_amount": 0, "count": 0})


def build_leaderboard() -> dict:
    attestations = fetch_tip_attestations()

    tipper_breakdown: dict[str, dict] = defaultdict(_empty_breakdown)
    referrer_breakdown: dict[str, dict] = defaultdict(_empty_breakdown)
    tipper_tip_count: dict[str, int] = defaultdict(int)
    referrer_tip_count: dict[str, int] = defaultdict(int)

    for a in attestations:
        token, referrer, amount, _comment = _decode_tip_data(a["data"])
        symbol, decimals = _token_info(token)

        tipper = Web3.to_checksum_address(a["attester"])
        tipper_breakdown[tipper][symbol]["total_amount"] += amount
        tipper_breakdown[tipper][symbol]["count"] += 1
        tipper_breakdown[tipper][symbol]["decimals"] = decimals
        tipper_tip_count[tipper] += 1

        if referrer.lower() != ZERO_ADDRESS:
            referrer = Web3.to_checksum_address(referrer)
            referrer_breakdown[referrer][symbol]["total_amount"] += amount
            referrer_breakdown[referrer][symbol]["count"] += 1
            referrer_breakdown[referrer][symbol]["decimals"] = decimals
            referrer_tip_count[referrer] += 1

    def _to_list(breakdown_by_addr, count_by_addr, count_label):
        ranked = sorted(count_by_addr.items(), key=lambda kv: kv[1], reverse=True)
        result = []
        for addr, _n in ranked:
            breakdown = [
                {
                    "currency": symbol,
                    "amount": stats["total_amount"] / (10 ** stats["decimals"]),
                    "count": stats["count"],
                }
                for symbol, stats in breakdown_by_addr[addr].items()
            ]
            result.append(
                {
                    "address": addr,
                    "ens_name": resolve_ens_name(addr),
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
