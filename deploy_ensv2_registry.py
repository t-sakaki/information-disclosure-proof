"""
Deploy the ENSv2-style organization subname registry (contracts/OrgSubnameRegistryV2.sol)
to Base Sepolia.

NOTE: This deploys our own, self-hosted contract that follows ENSv2's L2 registry
pattern (a fixed parent name, with labels registered directly by their owner's
wallet). It is NOT a deployment on ENS Labs' official ENSv2 Namechain
infrastructure -- see README.md for the distinction. It exists so that
organizations (NPOs, citizen ombudsman groups, etc.) can optionally register a
public, human-readable subname; individual disclosure requesters are never
required to use it.

Usage:
    python deploy_ensv2_registry.py

After it finishes, set ENSV2_REGISTRY_ADDRESS in .env (and the matching
constant in static/index.html) to the printed contract address.
"""
import json
import os

from dotenv import load_dotenv
from solcx import compile_source, install_solc
from web3 import Web3

load_dotenv()

RPC_URL = os.environ["CHAIN_RPC_URL"]
PRIVATE_KEY = os.environ["CHAIN_PRIVATE_KEY"]

SOLC_VERSION = "0.8.24"
CONTRACT_PATH = os.path.join(os.path.dirname(__file__), "contracts", "OrgSubnameRegistryV2.sol")
ABI_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "contracts", "OrgSubnameRegistryV2.abi.json")


def compile_contract():
    install_solc(SOLC_VERSION)
    with open(CONTRACT_PATH) as f:
        source = f.read()
    compiled = compile_source(source, output_values=["abi", "bin"], solc_version=SOLC_VERSION)
    _, contract_interface = compiled.popitem()
    return contract_interface["abi"], contract_interface["bin"]


def deploy() -> str:
    abi, bytecode = compile_contract()
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = w3.eth.account.from_key(PRIVATE_KEY)
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    tx = contract.constructor().build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address, "pending"),
            "chainId": w3.eth.chain_id,
        }
    )
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    with open(ABI_OUTPUT_PATH, "w") as f:
        json.dump(abi, f, indent=2)

    print(f"tx: {receipt.transactionHash.hex()}")
    print(f"OrgSubnameRegistryV2 deployed at: {receipt.contractAddress}")
    print("Set ENSV2_REGISTRY_ADDRESS in .env, and ENSV2_REGISTRY_ADDRESS in static/index.html, to this address.")
    return receipt.contractAddress


if __name__ == "__main__":
    deploy()
