"""
Read-only ETH -> USDC price reference via Uniswap V3's on-chain Quoter, on
Base mainnet (where Uniswap has real deployments and real liquidity --
unlike Base Sepolia, where this app's tipping/attestation flow actually
runs; see the README for why we didn't move tipping itself to a chain
with a "real" Uniswap deployment).

quoteExactInputSingle is called via eth_call (a simulated, read-only
call) exactly the way Uniswap's own frontend gets a quote before a swap --
this never signs anything, costs no gas, and never executes a swap. It's
shown on the Case page next to the ETH tip amount as "~$X (via Uniswap)"
so supporters unfamiliar with ETH pricing have a sense of a tip's real
value; this app never custodies funds or swaps anything itself.

Contract addresses (Uniswap V3 QuoterV2 + WETH on Base mainnet, and
Circle's native USDC on Base mainnet) are verified against Uniswap's own
sdk-core address registry and Circle's official docs, not guessed.
"""
from __future__ import annotations

import time
from typing import Optional

from web3 import Web3

BASE_MAINNET_RPC = "https://mainnet.base.org"
QUOTER_V2_ADDRESS = Web3.to_checksum_address("0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a")
WETH_BASE = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")
USDC_BASE = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
POOL_FEE = 500  # 0.05% -- the deep, actively-traded USDC/WETH pool on Base

QUOTER_V2_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
                "internalType": "struct IQuoterV2.QuoteExactInputSingleParams",
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
            {"internalType": "uint160", "name": "sqrtPriceX96After", "type": "uint160"},
            {"internalType": "uint32", "name": "initializedTicksCrossed", "type": "uint32"},
            {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

_CACHE_TTL_SECONDS = 30
_cache: dict[str, float | None] = {"at": 0.0, "usd_per_eth": None}


def get_eth_usd_price() -> Optional[float]:
    """How many USDC 1 ETH quotes for on Uniswap V3 (Base mainnet), or
    None if the read-only RPC call fails -- this is a display convenience
    the rest of the app never depends on, so it degrades silently."""
    if _cache["usd_per_eth"] is not None and time.time() - _cache["at"] < _CACHE_TTL_SECONDS:
        return _cache["usd_per_eth"]
    try:
        w3 = Web3(Web3.HTTPProvider(BASE_MAINNET_RPC))
        quoter = w3.eth.contract(address=QUOTER_V2_ADDRESS, abi=QUOTER_V2_ABI)
        one_eth = 10**18
        params = (WETH_BASE, USDC_BASE, one_eth, POOL_FEE, 0)
        amount_out, *_ = quoter.functions.quoteExactInputSingle(params).call()
        usd_per_eth = amount_out / 10**6  # USDC has 6 decimals
        _cache.update(at=time.time(), usd_per_eth=usd_per_eth)
        return usd_per_eth
    except Exception:
        return None
