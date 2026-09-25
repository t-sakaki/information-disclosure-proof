"""
Aggregate on-chain tip attestations into leaderboards:
    - top tippers (by total ETH tipped)
    - top referrers (by total ETH tipped through their referral)

Data is read directly from the EAS GraphQL indexer for Base Sepolia, so no
separate database is needed -- the chain itself is the source of truth.
"""
import os
from collections import defaultdict

import requests
from dotenv import load_dotenv
from eth_abi import decode
from web3 import Web3

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


def _decode_tip_data(data_hex: str) -> tuple[str, int, str]:
    raw = bytes.fromhex(data_hex[2:] if data_hex.startswith("0x") else data_hex)
    referrer, amount_wei, comment = decode(["address", "uint256", "string"], raw)
    return referrer, amount_wei, comment


def fetch_tip_attestations() -> list[dict]:
    response = requests.post(
        EASSCAN_GRAPHQL_URL,
        json={"query": QUERY, "variables": {"schemaId": TIP_SCHEMA_UID}},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["data"]["attestations"]


def build_leaderboard() -> dict:
    attestations = fetch_tip_attestations()

    tipper_totals: dict[str, int] = defaultdict(int)
    tipper_counts: dict[str, int] = defaultdict(int)
    referrer_totals: dict[str, int] = defaultdict(int)
    referrer_counts: dict[str, int] = defaultdict(int)

    for a in attestations:
        referrer, amount_wei, _comment = _decode_tip_data(a["data"])
        tipper = Web3.to_checksum_address(a["attester"])
        tipper_totals[tipper] += amount_wei
        tipper_counts[tipper] += 1
        if referrer.lower() != ZERO_ADDRESS:
            referrer = Web3.to_checksum_address(referrer)
            referrer_totals[referrer] += amount_wei
            referrer_counts[referrer] += 1

    top_tippers = sorted(tipper_totals.items(), key=lambda kv: kv[1], reverse=True)
    top_referrers = sorted(referrer_totals.items(), key=lambda kv: kv[1], reverse=True)

    return {
        "top_tippers": [
            {
                "address": addr,
                "total_wei": total,
                "total_eth": float(Web3.from_wei(total, "ether")),
                "tip_count": tipper_counts[addr],
            }
            for addr, total in top_tippers
        ],
        "top_referrers": [
            {
                "address": addr,
                "referred_total_wei": total,
                "referred_total_eth": float(Web3.from_wei(total, "ether")),
                "referral_count": referrer_counts[addr],
            }
            for addr, total in top_referrers
        ],
    }


if __name__ == "__main__":
    import json

    print(json.dumps(build_leaderboard(), indent=2, ensure_ascii=False))
