"""
"投げ銭" (tip) a Freedom-of-Information disclosure request: send ETH to the
requester's wallet on Base Sepolia and record a linked EAS attestation
(referencing the original request's attestation via refUID) so the amount,
sender, and message of support are verifiable on-chain.

Schema:
    address referrer  - wallet of whoever referred this tipper (zero address if none)
    uint256 amountWei - amount of the tip, in wei
    string  comment   - optional message of support/praise

Register this schema with:
    python register_schema.py "address referrer,uint256 amountWei,string comment"
and set the result as TIP_SCHEMA_UID in .env.
"""
import os

from dotenv import load_dotenv
from eth_abi import encode
from web3 import Web3

from attest import EAS_ABI, ZERO_ADDRESS

load_dotenv()

RPC_URL = os.environ["CHAIN_RPC_URL"]
PRIVATE_KEY = os.environ["CHAIN_PRIVATE_KEY"]
EAS_CONTRACT_ADDRESS = Web3.to_checksum_address(os.environ["EAS_CONTRACT_ADDRESS"])
TIP_SCHEMA_UID = os.environ["TIP_SCHEMA_UID"]


def send_tip(
    recipient_address: str,
    ref_attestation_uid: str,
    amount_wei: int,
    comment: str,
    referrer_address: str = ZERO_ADDRESS,
) -> dict:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = w3.eth.account.from_key(PRIVATE_KEY)
    recipient = Web3.to_checksum_address(recipient_address)
    referrer = Web3.to_checksum_address(referrer_address)

    # 1. Send the tip itself.
    transfer_tx = {
        "from": account.address,
        "to": recipient,
        "value": amount_wei,
        "nonce": w3.eth.get_transaction_count(account.address, "pending"),
        "chainId": w3.eth.chain_id,
        "gasPrice": w3.eth.gas_price,
    }
    transfer_tx["gas"] = w3.eth.estimate_gas(transfer_tx)
    signed_transfer = account.sign_transaction(transfer_tx)
    transfer_hash = w3.eth.send_raw_transaction(signed_transfer.raw_transaction)
    w3.eth.wait_for_transaction_receipt(transfer_hash)

    # 2. Record the tip as an attestation linked to the original request.
    eas = w3.eth.contract(address=EAS_CONTRACT_ADDRESS, abi=EAS_ABI)
    encoded_data = encode(
        ["address", "uint256", "string"], [referrer, amount_wei, comment]
    )

    request = (
        Web3.to_bytes(hexstr=TIP_SCHEMA_UID),
        (
            recipient,
            0,
            True,
            Web3.to_bytes(hexstr=ref_attestation_uid),
            encoded_data,
            0,
        ),
    )
    attest_tx = eas.functions.attest(request).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address, "pending"),
            "chainId": w3.eth.chain_id,
        }
    )
    signed_attest = account.sign_transaction(attest_tx)
    attest_hash = w3.eth.send_raw_transaction(signed_attest.raw_transaction)
    attest_receipt = w3.eth.wait_for_transaction_receipt(attest_hash)
    attested_events = eas.events.Attested().process_receipt(attest_receipt)
    tip_attestation_uid = attested_events[0]["args"]["uid"]

    return {
        "transfer_tx_hash": transfer_hash.hex(),
        "attestation_tx_hash": attest_hash.hex(),
        "tip_attestation_uid": tip_attestation_uid.hex(),
    }


if __name__ == "__main__":
    print(
        send_tip(
            recipient_address=ZERO_ADDRESS,
            ref_attestation_uid="0x" + "0" * 64,
            amount_wei=0,
            comment="test tip",
        )
    )
