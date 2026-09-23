"""Solana devnet memo ledger for recording clearance decisions."""

import base64
import json

import httpx
import streamlit as st

SOLANA_RPC = st.secrets.get("SOLANA_RPC_URL", "https://api.devnet.solana.com")
SOLANA_KEY = st.secrets.get("SOLANA_PRIVATE_KEY", "")

MEMO_PROGRAM = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"


def is_configured() -> bool:
    return bool(SOLANA_KEY)


def record_solana(document_hash: str, audit_hash: str, status: str, doc_ref: str, timestamp: str) -> dict:
    """Write clearance decision to Solana as a memo transaction."""
    memo = json.dumps({
        "app": "BorderFlow", "v": "1.1",
        "ref": doc_ref, "doc": document_hash, "audit": audit_hash,
        "status": status, "ts": timestamp
    }, separators=(",", ":"))

    if not SOLANA_KEY:
        fake_sig = "BF" + audit_hash.removeprefix("0x")[:16] + "DevnetDemo"
        return {
            "success": False, "simulated": True,
            "signature": fake_sig,
            "explorer_url": f"https://explorer.solana.com/tx/{fake_sig}?cluster=devnet",
            "memo": memo, "note": "Set SOLANA_PRIVATE_KEY in secrets.toml for real on-chain recording"
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
        cluster = "" if "mainnet" in SOLANA_RPC else "?cluster=devnet"
        return {
            "success": True, "simulated": False,
            "signature": sig,
            "explorer_url": f"https://explorer.solana.com/tx/{sig}{cluster}",
            "memo": memo
        }

    except ImportError:
        return {"success": False, "simulated": True,
                "error": "Run: pip install solders", "memo": memo}
    except Exception as e:
        return {"success": False, "simulated": True, "error": str(e), "memo": memo}
