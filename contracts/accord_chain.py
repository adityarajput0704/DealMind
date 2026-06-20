# accord_chain.py
#
# Thin wrapper around Web3.py for talking to the AccordRegistry contract on
# Monad testnet. Kept in its own file (not inside main.py or settlement.py)
# so the chain-specific code is easy to find, test, and swap out later if
# you move providers or networks.
#
# What this module does NOT do: retries, queuing, or background jobs. Every
# call here is synchronous and will block until the transaction is mined (or
# raise an exception). That's a deliberate, simple starting point — given
# the design choice that "/settle succeeds only if the chain write succeeds",
# blocking is correct: the caller needs to know the real outcome before
# deciding whether to commit the DB row.

import os
import json
import hashlib
from web3 import Web3
from web3.exceptions import ContractLogicError

CONTRACT_DIR = os.path.join(os.path.dirname(__file__))


class AccordChainError(Exception):
    """Raised for any chain-related failure: bad config, RPC down, tx reverted, etc."""
    pass


def _load_abi() -> list:
    with open(os.path.join(CONTRACT_DIR, "AccordRegistry.abi.json")) as f:
        return json.load(f)


def _get_web3_and_contract():
    """
    Build a connected Web3 instance + contract object from environment
    variables. Raises AccordChainError with a clear message if anything
    required is missing or unreachable — callers should NOT have to guess
    why this failed.
    """
    rpc_url = os.environ.get("MONAD_RPC_URL", "")
    private_key = os.environ.get("BACKEND_PRIVATE_KEY", "")
    contract_address = os.environ.get("ACCORD_CONTRACT_ADDRESS", "")

    if not rpc_url:
        raise AccordChainError("MONAD_RPC_URL environment variable not set.")
    if not private_key:
        raise AccordChainError("BACKEND_PRIVATE_KEY environment variable not set.")
    if not contract_address:
        raise AccordChainError("ACCORD_CONTRACT_ADDRESS environment variable not set.")

    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 20}))
    if not w3.is_connected():
        raise AccordChainError(f"Could not connect to Monad RPC at {rpc_url}.")

    abi = _load_abi()
    contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
    account = w3.eth.account.from_key(private_key)

    return w3, contract, account


def compute_agreement_hash(deal_id: int, contract_type: str, final_price_cents: int, timestamp: int) -> bytes:
    """
    keccak256 hash of the four plain fields, matching what the Solidity
    contract expects in recordAgreement(). Using Solidity's own ABI-encoding
    rules (via Web3's solidity_keccak) so the hash computed here will always
    match a hash independently recomputed on-chain or by any other client
    that encodes the same way.
    """
    return Web3.solidity_keccak(
        ["uint256", "string", "uint256", "uint256"],
        [deal_id, contract_type, final_price_cents, timestamp],
    )


def record_agreement_on_chain(
    deal_id: int,
    contract_type: str,
    final_price: float,
    timestamp: int,
) -> dict:
    """
    Write one settled agreement to AccordRegistry on Monad testnet.
    BLOCKS until the transaction is mined or fails.

    Returns a dict with the transaction hash and block number on success.
    Raises AccordChainError on ANY failure (bad config, RPC unreachable,
    insufficient funds, already-recorded dealId, transaction reverted, or
    timeout waiting for confirmation) — callers are expected to treat this
    as "the write did not happen" and act accordingly (e.g. roll back a
    DB transaction).
    """
    w3, contract, account = _get_web3_and_contract()

    final_price_cents = round(final_price * 100)  # Solidity has no float type
    agreement_hash = compute_agreement_hash(deal_id, contract_type, final_price_cents, timestamp)

    try:
        nonce = w3.eth.get_transaction_count(account.address)

        txn = contract.functions.recordAgreement(
            deal_id,
            contract_type,
            final_price_cents,
            timestamp,
            agreement_hash,
        ).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": 300_000,
            "gasPrice": w3.eth.gas_price,
            "chainId": w3.eth.chain_id,
        })

        signed = account.sign_transaction(txn)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt.status != 1:
            raise AccordChainError(
                f"Transaction for deal {deal_id} was mined but reverted "
                f"(status=0). Receipt: {dict(receipt)}"
            )

        return {
            "tx_hash": tx_hash.hex(),
            "block_number": receipt.blockNumber,
            "agreement_hash": agreement_hash.hex(),
            "final_price_cents": final_price_cents,
        }

    except ContractLogicError as e:
        # e.g. "AccordRegistry: deal already recorded" or "not the owner"
        raise AccordChainError(f"Contract rejected the write for deal {deal_id}: {e}")
    except AccordChainError:
        raise
    except Exception as e:
        # Catches RPC timeouts, connection errors, insufficient funds, etc.
        raise AccordChainError(f"Chain write failed for deal {deal_id}: {e}")


def get_agreement_from_chain(deal_id: int) -> dict | None:
    """
    Read back a recorded agreement. Returns None if nothing was recorded for
    this dealId (does not raise — "not found" is a normal, expected case for
    reads, unlike writes).
    """
    w3, contract, _account = _get_web3_and_contract()

    is_recorded = contract.functions.isRecorded(deal_id).call()
    if not is_recorded:
        return None

    contract_type, final_price_cents, timestamp, agreement_hash = (
        contract.functions.getAgreement(deal_id).call()
    )

    return {
        "deal_id": deal_id,
        "contract_type": contract_type,
        "final_price": final_price_cents / 100,
        "timestamp": timestamp,
        "agreement_hash": agreement_hash.hex(),
    }