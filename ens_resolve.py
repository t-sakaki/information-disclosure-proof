"""
Resolve wallet addresses to their ENS (Ethereum Name Service) names, so the
leaderboard can show human-readable names like "peikun.eth" instead of raw
0x addresses.

ENS records live on Ethereum mainnet, not Base Sepolia, so this connects to
a separate public mainnet RPC purely for read-only reverse lookups -- no
transactions, no private key needed here.
"""
import os
from functools import lru_cache

from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

ENS_RPC_URL = os.environ.get("ENS_RPC_URL", "https://ethereum-rpc.publicnode.com")

_w3 = Web3(Web3.HTTPProvider(ENS_RPC_URL))


@lru_cache(maxsize=256)
def resolve_ens_name(address: str) -> str | None:
    """Best-effort reverse ENS lookup. Returns None if unresolvable."""
    try:
        return _w3.ens.name(Web3.to_checksum_address(address))
    except Exception:
        return None


if __name__ == "__main__":
    import sys

    print(resolve_ens_name(sys.argv[1]))
