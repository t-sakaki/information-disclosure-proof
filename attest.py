"""
Attest a Freedom-of-Information disclosure request on-chain via EAS
(Ethereum Attestation Service) on Base Sepolia.

Schema encoded into the attestation (field order matters for ABI encoding):
    string  targetAuthority - name of the implementing agency (実施機関) the
                               request is addressed to, e.g. "〇〇市長",
                               "〇〇県知事", "〇〇市教育委員会"
    string  requestType     - kind of request, e.g. "行政文書開示請求"
    bytes32 documentHash    - sha256 of the disclosure request document
    string  summary         - short human-readable description of the request

Register a matching schema on https://base-sepolia.easscan.org/schema/create
and set its UID as EAS_SCHEMA_UID in .env before running this.
"""
import hashlib
import os

from dotenv import load_dotenv
from eth_abi import encode
from web3 import Web3

load_dotenv()

RPC_URL = os.environ["CHAIN_RPC_URL"]
PRIVATE_KEY = os.environ["CHAIN_PRIVATE_KEY"]
EAS_CONTRACT_ADDRESS = Web3.to_checksum_address(os.environ["EAS_CONTRACT_ADDRESS"])
EAS_SCHEMA_UID = os.environ["EAS_SCHEMA_UID"]

EAS_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "bytes32", "name": "schema", "type": "bytes32"},
                    {
                        "components": [
                            {"internalType": "address", "name": "recipient", "type": "address"},
                            {"internalType": "uint64", "name": "expirationTime", "type": "uint64"},
                            {"internalType": "bool", "name": "revocable", "type": "bool"},
                            {"internalType": "bytes32", "name": "refUID", "type": "bytes32"},
                            {"internalType": "bytes", "name": "data", "type": "bytes"},
                            {"internalType": "uint256", "name": "value", "type": "uint256"},
                        ],
                        "internalType": "struct AttestationRequestData",
                        "name": "data",
                        "type": "tuple",
                    },
                ],
                "internalType": "struct AttestationRequest",
                "name": "request",
                "type": "tuple",
            }
        ],
        "name": "attest",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "recipient", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "attester", "type": "address"},
            {"indexed": False, "internalType": "bytes32", "name": "uid", "type": "bytes32"},
            {"indexed": True, "internalType": "bytes32", "name": "schemaUID", "type": "bytes32"},
        ],
        "name": "Attested",
        "type": "event",
    },
]

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ZERO_BYTES32 = b"\x00" * 32


def document_hash(document_bytes: bytes) -> bytes:
    return hashlib.sha256(document_bytes).digest()


def build_schema_data(target_authority: str, request_type: str, doc_hash: bytes, summary: str) -> bytes:
    return encode(
        ["string", "string", "bytes32", "string"],
        [target_authority, request_type, doc_hash, summary],
    )


def submit_attestation(
    document_bytes: bytes, target_authority: str, request_type: str, summary: str
) -> dict:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = w3.eth.account.from_key(PRIVATE_KEY)
    eas = w3.eth.contract(address=EAS_CONTRACT_ADDRESS, abi=EAS_ABI)

    doc_hash = document_hash(document_bytes)
    encoded_data = build_schema_data(target_authority, request_type, doc_hash, summary)

    request = (
        Web3.to_bytes(hexstr=EAS_SCHEMA_UID),
        (
            ZERO_ADDRESS,
            0,
            True,
            ZERO_BYTES32,
            encoded_data,
            0,
        ),
    )

    tx = eas.functions.attest(request).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address, "pending"),
            "chainId": w3.eth.chain_id,
        }
    )
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    attested_events = eas.events.Attested().process_receipt(receipt)
    attestation_uid = attested_events[0]["args"]["uid"]
    return {
        "tx_hash": receipt.transactionHash.hex(),
        "attestation_uid": attestation_uid.hex(),
    }


if __name__ == "__main__":
    sample = b"sample disclosure request document"
    print(
        submit_attestation(
            sample,
            target_authority="〇〇市長",
            request_type="行政文書開示請求",
            summary="test attestation",
        )
    )
