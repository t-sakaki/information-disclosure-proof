"""
Attest a Freedom-of-Information disclosure request on-chain via EAS
(Ethereum Attestation Service) on Base Sepolia.

Schema encoded into the attestation (field order matters for ABI encoding).
This is the schema shared with the civic-lens repository -- both projects
attest the same field layout so records from either one can be read the
same way; keep the two in sync if this ever changes.

    string  recordId          - caller-assigned identifier for this request
                                 (e.g. "req-ab12cd34"); does not need to be
                                 globally unique, it is only a convenience
                                 lookup key alongside the attestation UID
    string  authority         - name of the implementing agency (実施機関)
                                 the request is addressed to, e.g. "〇〇市長",
                                 "〇〇県知事", "〇〇市教育委員会"
    string  requestType       - kind of request, e.g. "行政文書開示請求"
    string  requestedDocuments - the specific documents being requested, as
                                 verbatim text copied from the request itself
                                 (not a paraphrase/summary) -- see
                                 pii_scan.py, which must be run on this text
                                 before it is published, since it is
                                 permanent and public
    bytes32 documentHash      - sha256 of the full disclosure request
                                 document (may contain the requester's name/
                                 address, which is why only its hash --
                                 never the file itself -- is recorded)
    uint256 timestamp         - unix time the request was made
    string  legalBasis        - law/ordinance the request is made under,
                                 e.g. "情報公開法" or a municipal ordinance

Register a matching schema on https://base-sepolia.easscan.org/schema/create
and set its UID as EAS_SCHEMA_UID in .env before running this.
"""
import hashlib
import os
import time

from dotenv import load_dotenv
from eth_abi import encode
from web3 import Web3

from pii_scan import (
    MAX_REQUESTED_DOCUMENTS_BYTES,
    PersonalInfoWarning,
    normalize_requested_documents,
    scan_personal_info,
)

load_dotenv()

DEFAULT_LEGAL_BASIS = "情報公開法・各自治体情報公開条例"

RPC_URL = os.environ["CHAIN_RPC_URL"]
# CHAIN_PRIVATE_KEY is only used by submit_attestation() below, a
# server-side-signing fallback for CLI/API use. The real product flow
# (static/index.html, case_page.py) signs directly with the user's own
# wallet in the browser and never touches this key, so it's read lazily
# here rather than required at import time -- a deployment that only
# serves the wallet-signed flow doesn't need this secret configured at all.
PRIVATE_KEY = os.environ.get("CHAIN_PRIVATE_KEY")
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


def build_schema_data(
    record_id: str,
    authority: str,
    request_type: str,
    requested_documents: str,
    doc_hash: bytes,
    timestamp: int,
    legal_basis: str,
) -> bytes:
    return encode(
        ["string", "string", "string", "string", "bytes32", "uint256", "string"],
        [record_id, authority, request_type, requested_documents, doc_hash, timestamp, legal_basis],
    )


def submit_attestation(
    document_bytes: bytes,
    record_id: str,
    authority: str,
    request_type: str,
    requested_documents: str = "",
    legal_basis: str = DEFAULT_LEGAL_BASIS,
    acknowledge_warnings: bool = False,
) -> dict:
    """Submits the attestation. requested_documents must be a verbatim quote
    from the request, never a paraphrase/summary -- see the schema docstring
    above. It is scanned for likely personal information before being
    published in plaintext; PersonalInfoWarning is raised unless the caller
    has confirmed with the requester and passes acknowledge_warnings=True."""
    if not PRIVATE_KEY:
        raise RuntimeError(
            "CHAIN_PRIVATE_KEY is not configured on this deployment. "
            "Use the wallet-signed flow in the browser instead (this "
            "server-signing fallback is for CLI/API use only)."
        )
    normalized_documents = normalize_requested_documents(requested_documents)
    if normalized_documents:
        if len(normalized_documents.encode("utf-8")) > MAX_REQUESTED_DOCUMENTS_BYTES:
            raise ValueError(
                f"requested_documents is too long (max {MAX_REQUESTED_DOCUMENTS_BYTES} UTF-8 bytes)."
            )
        warnings = scan_personal_info(normalized_documents)
        if warnings and not acknowledge_warnings:
            raise PersonalInfoWarning(warnings)

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = w3.eth.account.from_key(PRIVATE_KEY)
    eas = w3.eth.contract(address=EAS_CONTRACT_ADDRESS, abi=EAS_ABI)

    doc_hash = document_hash(document_bytes)
    now_ts = int(time.time())
    encoded_data = build_schema_data(
        record_id, authority, request_type, normalized_documents, doc_hash, now_ts, legal_basis
    )

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
            record_id="req-test0001",
            authority="〇〇市長",
            request_type="行政文書開示請求",
            requested_documents="test attestation",
        )
    )
