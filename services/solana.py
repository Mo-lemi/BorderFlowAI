"""Solana devnet memo ledger for recording clearance decisions."""

import base64
import json
import time

import httpx
import streamlit as st

SOLANA_RPC = st.secrets.get("SOLANA_RPC_URL", "https://api.devnet.solana.com")
SOLANA_KEY = st.secrets.get("SOLANA_PRIVATE_KEY", "")

MEMO_PROGRAM = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"

CONFIRM_TIMEOUT_S = 10.0
CONFIRM_POLL_INTERVAL_S = 1.0


def is_configured() -> bool:
    return bool(SOLANA_KEY)


def _network_label() -> str:
    rpc = SOLANA_RPC.lower()
    if "devnet" in rpc:
        return "devnet"
    if "mainnet" in rpc:
        return "mainnet"
    return "custom"


def _poll_confirmation(signature: str) -> str:
    """Poll getSignatureStatuses for up to CONFIRM_TIMEOUT_S seconds.

    Returns "confirmed", "finalized", "failed" (status carries an err), or
    "submitted_unconfirmed" if the poll window elapses with no status yet.
    """
    deadline = time.monotonic() + CONFIRM_TIMEOUT_S
    while time.monotonic() < deadline:
        resp = httpx.post(SOLANA_RPC, json={
            "jsonrpc": "2.0", "id": 1,
            "method": "getSignatureStatuses",
            "params": [[signature], {"searchTransactionHistory": True}]
        }, timeout=15.0)
        value = resp.json().get("result", {}).get("value", [None])[0]
        if value:
            if value.get("err"):
                return "failed"
            status = value.get("confirmationStatus")
            if status in ("confirmed", "finalized"):
                return status
        time.sleep(CONFIRM_POLL_INTERVAL_S)
    return "submitted_unconfirmed"


def record_solana(document_hash: str, audit_hash: str, alg: str, status: str, doc_ref: str, timestamp: str) -> dict:
    """Write clearance decision to Solana as a memo transaction."""
    memo = json.dumps({
        "app": "BorderFlow", "v": "1.3",
        "ref": doc_ref, "doc": document_hash, "audit": audit_hash, "alg": alg,
        "status": status, "ts": timestamp
    }, separators=(",", ":"))
    network = _network_label()

    if not SOLANA_KEY:
        return {
            "success": False, "simulated": True,
            "signature": None, "explorer_url": None,
            "network": network, "memo": memo,
            "note": "Set SOLANA_PRIVATE_KEY in secrets.toml for real on-chain recording",
        }

    try:
        from solders.keypair import Keypair
        from solders.transaction import Transaction
        from solders.instruction import Instruction, AccountMeta
        from solders.pubkey import Pubkey
        from solders.hash import Hash
        from solders.message import Message

        # Get latest blockhash
        bh_resp = httpx.post(SOLANA_RPC, json={
            "jsonrpc": "2.0", "id": 1,
            "method": "getLatestBlockhash",
            "params": [{"commitment": "finalized"}]
        }, timeout=15.0)
        blockhash = bh_resp.json()["result"]["value"]["blockhash"]

        kp = Keypair.from_base58_string(SOLANA_KEY)
        memo_program = Pubkey.from_string(MEMO_PROGRAM)
        instruction = Instruction(
            program_id=memo_program,
            accounts=[AccountMeta(pubkey=kp.pubkey(), is_signer=True, is_writable=False)],
            data=memo.encode("utf-8")
        )
        msg = Message.new_with_blockhash([instruction], kp.pubkey(), Hash.from_string(blockhash))
        tx = Transaction.new_unsigned(msg)
        tx.sign([kp], Hash.from_string(blockhash))

        send_resp = httpx.post(SOLANA_RPC, json={
            "jsonrpc": "2.0", "id": 1,
            "method": "sendTransaction",
            "params": [base64.b64encode(bytes(tx)).decode(), {"encoding": "base64"}]
        }, timeout=15.0)
        result = send_resp.json()

        if "error" in result:
            raise Exception(result["error"]["message"])

        sig = result["result"]
        confirmation = _poll_confirmation(sig)

        cluster = "" if "mainnet" in SOLANA_RPC else "?cluster=devnet"
        return {
            "success": confirmation in ("confirmed", "finalized"),
            "simulated": False,
            "signature": sig,
            "explorer_url": f"https://explorer.solana.com/tx/{sig}{cluster}",
            "network": network,
            "confirmation": confirmation,
            "memo": memo,
        }

    except ImportError:
        return {"success": False, "simulated": True,
                "signature": None, "explorer_url": None,
                "network": network,
                "error": "Run: pip install solders", "memo": memo}
    except Exception as e:
        return {"success": False, "simulated": True,
                "signature": None, "explorer_url": None,
                "network": network,
                "error": str(e), "memo": memo}
