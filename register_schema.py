"""
Register a new EAS schema on Base Sepolia via the SchemaRegistry contract,
without going through the web UI. Usage:

    python register_schema.py "string recordId,string authority,string requestType,string requestedDocuments,bytes32 documentHash,uint256 timestamp,string legalBasis"
"""
import os
import sys

from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL = os.environ["CHAIN_RPC_URL"]
PRIVATE_KEY = os.environ["CHAIN_PRIVATE_KEY"]
SCHEMA_REGISTRY_ADDRESS = Web3.to_checksum_address(
    os.environ.get("SCHEMA_REGISTRY_ADDRESS", "0x4200000000000000000000000000000000000020")
)

SCHEMA_REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "schema", "type": "string"},
            {"internalType": "address", "name": "resolver", "type": "address"},
            {"internalType": "bool", "name": "revocable", "type": "bool"},
        ],
        "name": "register",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def register_schema(schema: str) -> str:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = w3.eth.account.from_key(PRIVATE_KEY)
    registry = w3.eth.contract(address=SCHEMA_REGISTRY_ADDRESS, abi=SCHEMA_REGISTRY_ABI)

    tx = registry.functions.register(schema, ZERO_ADDRESS, True).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address, "pending"),
            "chainId": w3.eth.chain_id,
        }
    )
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    schema_uid = Web3.solidity_keccak(
        ["string", "address", "bool"], [schema, ZERO_ADDRESS, True]
    )
    print(f"tx: {receipt.transactionHash.hex()}")
    return "0x" + schema_uid.hex().removeprefix("0x")


if __name__ == "__main__":
    schema = sys.argv[1]
    print(f"schema_uid: {register_schema(schema)}")
