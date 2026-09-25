"""
Read-only resolver for the ENSv2-style organization subname registry
(contracts/OrgSubnameRegistryV2.sol, deployed via deploy_ensv2_registry.py
on Base Sepolia).

団体（NPO・市民オンブズマン団体等）が任意で登録したサブネーム（例:
"sample-npo.npo.disclosureproof.eth"）をアドレスから逆引きする。個人の
開示請求者はこの登録を行う必要はなく、未登録でもリーダーボードには
アドレス省略表記で表示される。
"""
import json
import os

from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL = os.environ["CHAIN_RPC_URL"]
ENSV2_REGISTRY_ADDRESS = os.environ.get("ENSV2_REGISTRY_ADDRESS")

ABI_PATH = os.path.join(os.path.dirname(__file__), "contracts", "OrgSubnameRegistryV2.abi.json")

_w3 = Web3(Web3.HTTPProvider(RPC_URL))
_contract = None

if ENSV2_REGISTRY_ADDRESS and os.path.exists(ABI_PATH):
    with open(ABI_PATH) as f:
        _abi = json.load(f)
    _contract = _w3.eth.contract(address=Web3.to_checksum_address(ENSV2_REGISTRY_ADDRESS), abi=_abi)


def resolve_org_name(address: str) -> str | None:
    """団体が登録したENSv2サブネームを返す。未登録・未デプロイならNone。"""
    if _contract is None:
        return None
    try:
        name = _contract.functions.fullName(Web3.to_checksum_address(address)).call()
        return name or None
    except Exception:
        return None


if __name__ == "__main__":
    import sys

    print(resolve_org_name(sys.argv[1]))
