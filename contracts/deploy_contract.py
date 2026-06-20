# deploy_contract.py
#
# Run this ONCE to deploy AccordRegistry to Monad testnet.
# After it succeeds, copy the printed contract address into your .env file
# (as ACCORD_CONTRACT_ADDRESS) — you don't deploy again after that.
#
# CONFIRMED Monad testnet details (verified against docs.monad.xyz as of
# this writing — double check at https://docs.monad.xyz/guides/add-monad-to-wallet/testnet
# before using, since RPC endpoints can occasionally change):
#   RPC URL:   https://testnet-rpc.monad.xyz
#   Chain ID:  10143
#   Currency:  MON
#   Explorer:  https://testnet.monadexplorer.com
#
# What you need before running this:
#   1. A wallet private key with Monad testnet funds (get free MON from the
#      faucet at https://testnet.monad.xyz — this wallet becomes the
#      contract's "owner", the only address allowed to write records).
#   2. The RPC URL above (or your own provider's Monad testnet endpoint).
#
# Set these as environment variables before running:
#   export MONAD_RPC_URL="https://testnet-rpc.monad.xyz"
#   export DEPLOYER_PRIVATE_KEY="0x...."
#
# Then run:
#   python3 deploy_contract.py

import os
import json
from web3 import Web3


CONTRACT_DIR = os.path.dirname(__file__)

def main():
    rpc_url = os.environ.get("MONAD_RPC_URL", "")
    private_key = os.environ.get("DEPLOYER_PRIVATE_KEY", "")

    if not rpc_url:
        raise SystemExit("MONAD_RPC_URL environment variable not set.")
    if not private_key:
        raise SystemExit("DEPLOYER_PRIVATE_KEY environment variable not set.")

    # Connect to Monad testnet
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise SystemExit(f"Could not connect to RPC at {rpc_url}. Check the URL and your network settings.")

    print(f"Connected to chain ID: {w3.eth.chain_id}")

    EXPECTED_TESTNET_CHAIN_ID = 10143
    if w3.eth.chain_id != EXPECTED_TESTNET_CHAIN_ID:
        print(
            f"WARNING: connected chain ID is {w3.eth.chain_id}, but Monad "
            f"testnet is expected to be {EXPECTED_TESTNET_CHAIN_ID}. "
            f"Double-check MONAD_RPC_URL before continuing — deploying to "
            f"the wrong chain wastes gas and gives you a contract address "
            f"on a network you didn't intend."
        )
        confirm = input("Continue anyway? [y/N]: ").strip().lower()
        if confirm != "y":
            raise SystemExit("Aborted by user.")

    # Load the compiled contract artifacts (produced by compile_contract.js)
    with open(os.path.join(CONTRACT_DIR, "AccordRegistry.abi.json")) as f:
        abi = json.load(f)
    with open(os.path.join(CONTRACT_DIR, "AccordRegistry.bytecode.txt")) as f:
        bytecode = f.read().strip()

    account = w3.eth.account.from_key(private_key)
    print(f"Deploying from address: {account.address}")

    balance = w3.eth.get_balance(account.address)
    print(f"Account balance: {w3.from_wei(balance, 'ether')} (native testnet token)")
    if balance == 0:
        raise SystemExit(
            "Deployer wallet has zero balance. Get free testnet tokens from a "
            "Monad testnet faucet before deploying."
        )

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    nonce = w3.eth.get_transaction_count(account.address)

    # Build the deployment transaction.
    # NOTE: gas price strategy is intentionally simple (legacy gasPrice) for
    # clarity on a testnet. If Monad mainnet requires EIP-1559 fields
    # (maxFeePerGas / maxPriorityFeePerGas) instead, that's a small change
    # to make later — flag it to me when you're ready for mainnet.
    txn = Contract.constructor().build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 2_000_000,            # generous ceiling; unused gas is refunded
        "gasPrice": w3.eth.gas_price,
        "chainId": w3.eth.chain_id,
    })

    signed = account.sign_transaction(txn)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Deployment transaction sent: {tx_hash.hex()}")
    print("Waiting for confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    if receipt.status != 1:
        raise SystemExit(f"Deployment transaction failed. Receipt: {receipt}")

    contract_address = receipt.contractAddress
    print()
    print("=" * 60)
    print(f"CONTRACT DEPLOYED SUCCESSFULLY")
    print(f"Address: {contract_address}")
    print(f"Owner (write access): {account.address}")
    print("=" * 60)
    print()
    print("Next step: add this to your .env / environment:")
    print(f'  export ACCORD_CONTRACT_ADDRESS="{contract_address}"')


if __name__ == "__main__":
    main()