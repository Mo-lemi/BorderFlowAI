"""
BorderFlow AI: Forensic Auditor — Hackathon Edition
Streamlit app with Gemini Vision, ElevenLabs TTS, and Solana proof-of-cargo.
"""

import streamlit as st
from google import genai
from PIL import Image, ExifTags
import httpx
import hashlib
import json
import re
import base64
import asyncio
from datetime import datetime

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="BorderFlow AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CUSTOM CSS  — dark forensic terminal aesthetic
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Chakra+Petch:wght@400;600&display=swap');

html, body, [class*="css"] {
    background-color: #080c0a !important;
    color: #3dd68c !important;
    font-family: 'Share Tech Mono', monospace !important;
}

.stApp { background-color: #080c0a; }

h1, h2, h3 {
    font-family: 'Chakra Petch', sans-serif !important;
    color: #3dd68c !important;
    letter-spacing: 0.06em;
}

.stButton > button {
    background: #1a3a28 !important;
    border: 1px solid #2a6644 !important;
    color: #3dd68c !important;
    font-family: 'Share Tech Mono', monospace !important;
    letter-spacing: 0.1em;
    border-radius: 4px;
    transition: all 0.15s;
}

.stButton > button:hover {
    background: #224a34 !important;
    border-color: #3dd68c !important;
}

.stTextArea textarea, .stTextInput input, .stSelectbox select {
    background: #0c1410 !important;
    border: 1px solid #1a2e20 !important;
    color: #7ab893 !important;
    font-family: 'Share Tech Mono', monospace !important;
    border-radius: 4px;
}

.stFileUploader {
    border: 1px dashed #2a6644 !important;
    border-radius: 4px;
    background: #0c1410 !important;
}

.stProgress > div > div {
    background: #3dd68c !important;
}

[data-testid="stSidebar"] {
    background: #0c1410 !important;
    border-right: 1px solid #1a2e20;
}

.verdict-approved {
    background: #0d2218;
    border: 1px solid #2a6644;
    border-radius: 6px;
    padding: 16px;
    margin: 10px 0;
}

.verdict-flagged {
    background: #200d0d;
    border: 1px solid #4a2020;
    border-radius: 6px;
    padding: 16px;
    margin: 10px 0;
}

.verdict-warning {
    background: #1a1500;
    border: 1px solid #3a2a00;
    border-radius: 6px;
    padding: 16px;
    margin: 10px 0;
}

.json-block {
    background: #060e09;
    border: 1px solid #1a2e20;
    border-radius: 4px;
    padding: 12px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 12px;
    color: #4a7a5e;
    white-space: pre-wrap;
    word-break: break-all;
}

.ledger-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid #1a2e20;
    font-size: 12px;
}

.check-pass { color: #3dd68c; }
.check-fail { color: #e05a5a; }
.check-warn { color: #e0a840; }

.metric-box {
    background: #0c1410;
    border: 1px solid #1a2e20;
    border-radius: 4px;
    padding: 12px;
    text-align: center;
}

div[data-testid="stExpander"] {
    background: #0c1410 !important;
    border: 1px solid #1a2e20 !important;
    border-radius: 4px;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECRETS CHECK
# ─────────────────────────────────────────────

required_secrets = ["GEMINI_KEY"]
optional_secrets = ["ELEVENLABS_KEY", "ELEVENLABS_VOICE_ID", "SOLANA_RPC_URL", "SOLANA_PRIVATE_KEY"]

for s in required_secrets:
    if s not in st.secrets:
        st.error(f"❌ Missing `{s}` in `.streamlit/secrets.toml`")
        st.stop()

GEMINI_KEY = st.secrets["GEMINI_KEY"]
ELEVENLABS_KEY = st.secrets.get("ELEVENLABS_KEY", "")
ELEVENLABS_VOICE_ID = st.secrets.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
SOLANA_RPC = st.secrets.get("SOLANA_RPC_URL", "https://api.devnet.solana.com")
SOLANA_KEY = st.secrets.get("SOLANA_PRIVATE_KEY", "")

client = genai.Client(api_key=GEMINI_KEY)

MEMO_PROGRAM = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

defaults = {
    "step": 1,
    "declaration": "",
    "border_post": "Beit Bridge (ZA/ZW)",
    "cargo_type": "General Freight",
    "vehicle_reg": "",
    "driver_id": "",
    "permit_no": "",
    "weight_kg": 0.0,
    "dest_country": "ZW",
    "audit_result": None,
    "doc_hash": None,
    "ledger_result": None,
    "audio_bytes": None,
    "image_obj": None,
    "metadata_str": "",
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def luhn_check(id_number: str) -> tuple[bool, str]:
    """SA ID Luhn validation."""
    id_number = id_number.strip()
    if not id_number.isdigit() or len(id_number) != 13:
        return False, "Must be exactly 13 digits"
    total = 0
    for i, d in enumerate(id_number[:12]):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    expected = (10 - (total % 10)) % 10
    if expected != int(id_number[12]):
        return False, f"Checksum invalid — possible forged ID"
    try:
        yy, mm, dd = int(id_number[:2]), int(id_number[2:4]), int(id_number[4:6])
        year = 1900 + yy if yy >= 24 else 2000 + yy
        dob = datetime(year, mm, dd)
        age = (datetime.now() - dob).days // 365
        if age < 18 or age > 80:
            return False, f"Embedded DOB implies age {age} — anomalous"
    except ValueError:
        return False, "Embedded date of birth is invalid"
    return True, f"Valid · DOB encoded · Citizenship digit {id_number[10]}"


def validate_permit(permit: str, cargo: str) -> tuple[bool, str]:
    CARGO_CLASS = {
        "General Freight": "TP", "Electronics": "TP",
        "Perishables": "PA", "Live Animals": "LA",
        "Hazardous Materials": "HZ", "Fuel / Petroleum": "FP",
        "Pharmaceuticals": "PH",
    }
    permit = permit.upper().strip()
    if not re.match(r"^BMA-(TP|HZ|PA|LA|FP|PH)-\d{4}-\d{4,6}$", permit):
        return False, f"Format invalid — expected BMA-{{CLASS}}-YYYY-XXXXX"
    permit_year = int(permit.split("-")[2])
    current_year = datetime.now().year
    if permit_year < current_year - 1 or permit_year > current_year:
        return False, f"Permit year {permit_year} is expired or invalid"
    permit_class = permit.split("-")[1]
    required = CARGO_CLASS.get(cargo, "TP")
    if permit_class != required:
        return False, f"{cargo} requires {required} permit; found {permit_class}"
    return True, f"Valid · Class {permit_class} · Year {permit_year}"


BORDER_COUNTRIES = {
    "Beit Bridge": ["ZW", "ZM", "MW"],
    "Lebombo": ["MZ", "SZ"],
    "Kopfontein": ["BW", "NA"],
    "Oshoek": ["SZ"],
    "Ficksburg": ["LS"],
    "Maseru": ["LS"],
    "Vioolsdrift": ["NA"],
}


def validate_route(border: str, dest: str) -> tuple[bool, str]:
    for b, countries in BORDER_COUNTRIES.items():
        if b.lower() in border.lower():
            if dest.upper() in countries:
                return True, f"{border} is valid for {dest}"
            return False, f"{border} does not serve {dest}"
    return True, "Route cross-check passed"


def validate_weight(weight: float) -> tuple[str, str]:
    """Returns severity, message."""
    if weight <= 0:
        return "FAIL", "Declared weight is zero"
    if weight > 56000:
        return "FAIL", f"{weight:,.0f} kg exceeds 56,000 kg national GVM limit"
    if weight > 48000:
        return "WARN", f"{weight:,.0f} kg — secondary weigh-bridge check advised"
    return "PASS", f"{weight:,.0f} kg within legal limits"


def generate_hash(data: dict) -> str:
    raw = json.dumps(data, sort_keys=True)
    return "0x" + hashlib.sha256(raw.encode()).hexdigest().upper()


def extract_exif(img: Image.Image) -> str:
    exif = img.getexif()
    if not exif:
        return "No EXIF metadata found — possible screenshot or synthetic image"
    readable = {ExifTags.TAGS.get(t, t): v for t, v in exif.items() if t in ExifTags.TAGS}
    return json.dumps(readable, default=str)[:800]


def build_audio_script(status: str, doc_ref: str, reason: str = "") -> str:
    if status == "CLEARED":
        return (
            f"Clearance approved for document {doc_ref}. "
            "All forensic checks have passed. "
            "Please proceed to the designated departure lane and retain this confirmation."
        )
    elif status == "WARNING":
        return (
            f"Attention — document {doc_ref} has been flagged for review. "
            f"{reason} "
            "Please proceed to the secondary inspection bay."
        )
    else:
        return (
            f"Clearance denied for document {doc_ref}. "
            f"{reason} "
            "Please park in the inspection zone and await a BMA officer. Do not attempt to proceed."
        )


# ─────────────────────────────────────────────
# API INTEGRATIONS
# ─────────────────────────────────────────────

def call_gemini_audit(declaration: str, image: Image.Image, metadata: str,
                      vehicle_reg: str, border: str, cargo: str,
                      weight: float, permit: str, dest: str) -> str:
    """Full multimodal forensic audit via Gemini Vision."""
    prompt = f"""ACT AS: A South African BMA Forensic Customs Auditor.

DRIVER DECLARATION: {declaration}
VEHICLE REGISTRATION: {vehicle_reg}
BORDER POST: {border}
DECLARED CARGO: {cargo}
DECLARED WEIGHT: {weight} kg
PERMIT NUMBER: {permit}
DESTINATION: {dest}
IMAGE EXIF METADATA: {metadata}

YOUR FORENSIC TASK — analyze the uploaded manifest/document image and:

1. OCR ALL TEXT from the document image. Extract every number, name, date, and field.
2. CROSS-REFERENCE: Compare the extracted document data against every declared field above.
   Flag mismatches in: commodity type, weight, consignee, origin/destination, permit number, registration.
3. PHYSICAL LOGIC CHECK: Is the declared weight physically plausible for this commodity?
   (e.g., 24 tons of flowers is implausible; 24 tons of steel beams is plausible)
4. FORENSIC IMAGE CHECK: Assess the document for signs of tampering:
   - Font inconsistencies or pixel artifacts around text
   - Missing official stamps or watermarks
   - EXIF metadata anomalies (stripped metadata suggests screenshot/synthetic)
   - Mismatched ink colors or printing inconsistencies
5. REGULATORY CHECK: Does the permit class match the cargo type under SARS/BMA 2024 rules?

OUTPUT FORMAT (use exactly this structure):
AUDIT STATUS: [CLEARED / WARNING / FRAUD ALERT]

EXTRACTED DOCUMENT DATA:
[List every field you can read from the image]

DISCREPANCIES FOUND:
[List each specific mismatch between declaration and document, or NONE]

FORENSIC OBSERVATIONS:
[Document integrity assessment — tampering indicators, metadata analysis]

PHYSICAL LOGIC ASSESSMENT:
[Weight/commodity plausibility check]

REGULATORY COMPLIANCE:
[Permit class vs cargo type per BMA/SARS rules]

CONFIDENCE SCORE: [1-10]

RECOMMENDED ACTION: [PROCEED TO LANE / SECONDARY INSPECTION / DETAIN FOR INVESTIGATION]
"""
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt, image],
    )
    return response.text or "No response from Gemini."


def call_elevenlabs(script: str) -> bytes | None:
    """Generate MP3 audio from clearance script."""
    if not ELEVENLABS_KEY:
        return None
    try:
        r = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            json={
                "text": script,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.75,
                    "similarity_boost": 0.85,
                    "style": 0.2,
                    "use_speaker_boost": True
                }
            },
            headers={
                "xi-api-key": ELEVENLABS_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            },
            timeout=30.0
        )
        r.raise_for_status()
        return r.content
    except Exception as e:
        st.warning(f"ElevenLabs error: {e}")
        return None


def record_solana(doc_hash: str, status: str, doc_ref: str, timestamp: str) -> dict:
    """Write clearance decision to Solana as a memo transaction."""
    memo = json.dumps({
        "app": "BorderFlow", "v": "1.0",
        "ref": doc_ref, "hash": doc_hash,
        "status": status, "ts": timestamp
    }, separators=(",", ":"))

    if not SOLANA_KEY:
        fake_sig = "BF" + doc_hash[2:18] + "DevnetDemo"
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


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🛡️ BorderFlow AI")
    st.markdown("*BMA Forensic Pre-Clearance*")
    st.divider()

    st.markdown("**Integration Status**")

    gemini_ok = bool(GEMINI_KEY)
    el_ok = bool(ELEVENLABS_KEY)
    sol_ok = bool(SOLANA_KEY)

    st.markdown(f"{'✅' if gemini_ok else '❌'} Gemini Vision")
    st.markdown(f"{'✅' if el_ok else '⚠️'} ElevenLabs Audio")
    st.markdown(f"{'✅' if sol_ok else '⚠️'} Solana Ledger")

    st.divider()

    with st.expander("ℹ️ How it works"):
        st.markdown("""
1. **Declare** cargo and fill document fields
2. **Upload** manifest photo
3. **Gemini Vision** OCRs and cross-references everything
4. **Solana** records the hash on-chain
5. **ElevenLabs** reads the verdict aloud to the driver
        """)

    st.divider()

    if st.button("🔄 Reset Workflow", use_container_width=True):
        for k, v in defaults.items():
            st.session_state[k] = v
        st.rerun()


# ─────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────

st.title("🛡️ BorderFlow AI: Forensic Auditor")
st.caption("SADC Border Management Authority · Real-time Cargo Pre-Clearance")

progress_map = {1: 0.25, 2: 0.5, 3: 0.75, 4: 1.0}
st.progress(progress_map.get(st.session_state.step, 0.25),
            text=f"Step {st.session_state.step} of 4")

st.divider()


# ─────────────────────────────────────────────
# STEP 1 — DRIVER DECLARATION
# ─────────────────────────────────────────────

if st.session_state.step == 1:
    st.subheader("Step 1 — Driver & Cargo Declaration")
    st.caption("Enter the details exactly as they appear on your paperwork.")

    col1, col2 = st.columns(2)

    with col1:
        declaration = st.text_area(
            "Cargo Declaration",
            value=st.session_state.declaration,
            placeholder="e.g. 15 tons of Furniture from Pretoria to Harare...",
            height=100
        )
        vehicle_reg = st.text_input(
            "Vehicle Registration",
            value=st.session_state.vehicle_reg,
            placeholder="e.g. GP 47 BW WX"
        )
        driver_id = st.text_input(
            "Driver SA ID Number",
            value=st.session_state.driver_id,
            placeholder="13-digit SA ID"
        )

    with col2:
        border_post = st.selectbox("Border Post", [
            "Beit Bridge (ZA/ZW)", "Lebombo (ZA/MZ)", "Kopfontein (ZA/BW)",
            "Oshoek (ZA/SZ)", "Ficksburg (ZA/LS)", "Maseru Bridge (ZA/LS)", "Vioolsdrift (ZA/NA)"
        ], index=["Beit Bridge (ZA/ZW)", "Lebombo (ZA/MZ)", "Kopfontein (ZA/BW)",
                  "Oshoek (ZA/SZ)", "Ficksburg (ZA/LS)", "Maseru Bridge (ZA/LS)", "Vioolsdrift (ZA/NA)"
                  ].index(st.session_state.border_post) if st.session_state.border_post in
                          ["Beit Bridge (ZA/ZW)", "Lebombo (ZA/MZ)", "Kopfontein (ZA/BW)",
                           "Oshoek (ZA/SZ)", "Ficksburg (ZA/LS)", "Maseru Bridge (ZA/LS)", "Vioolsdrift (ZA/NA)"] else 0)

        cargo_type = st.selectbox("Cargo Type", [
            "General Freight", "Perishables", "Hazardous Materials",
            "Live Animals", "Fuel / Petroleum", "Electronics", "Pharmaceuticals"
        ])
        dest_country = st.text_input("Destination Country Code", value=st.session_state.dest_country,
                                     placeholder="e.g. ZW, MZ, BW")

    col3, col4 = st.columns(2)
    with col3:
        permit_no = st.text_input(
            "BMA Permit Number",
            value=st.session_state.permit_no,
            placeholder="BMA-TP-2024-88341"
        )
    with col4:
        weight_kg = st.number_input("Declared Weight (kg)", min_value=0.0,
                                    value=float(st.session_state.weight_kg), step=100.0)

    # Live pre-checks
    if driver_id:
        id_ok, id_msg = luhn_check(driver_id)
        if id_ok:
            st.success(f"✓ ID Valid: {id_msg}")
        else:
            st.error(f"✕ ID Invalid: {id_msg}")

    if permit_no and cargo_type:
        p_ok, p_msg = validate_permit(permit_no, cargo_type)
        if p_ok:
            st.success(f"✓ Permit Valid: {p_msg}")
        else:
            st.error(f"✕ Permit Issue: {p_msg}")

    if weight_kg > 0:
        w_sev, w_msg = validate_weight(weight_kg)
        if w_sev == "PASS":
            st.success(f"✓ Weight: {w_msg}")
        elif w_sev == "WARN":
            st.warning(f"⚠ Weight: {w_msg}")
        else:
            st.error(f"✕ Weight: {w_msg}")

    st.divider()

    if st.button("Next: Upload Document →", use_container_width=True):
        if not declaration.strip():
            st.error("Cargo declaration is required.")
        elif not vehicle_reg.strip():
            st.error("Vehicle registration is required.")
        else:
            st.session_state.declaration = declaration.strip()
            st.session_state.vehicle_reg = vehicle_reg.strip()
            st.session_state.driver_id = driver_id.strip()
            st.session_state.border_post = border_post
            st.session_state.cargo_type = cargo_type
            st.session_state.dest_country = dest_country.strip().upper()
            st.session_state.permit_no = permit_no.strip()
            st.session_state.weight_kg = weight_kg
            st.session_state.step = 2
            st.rerun()


# ─────────────────────────────────────────────
# STEP 2 — DOCUMENT UPLOAD
# ─────────────────────────────────────────────

elif st.session_state.step == 2:
    st.subheader("Step 2 — Upload Manifest / Document")

    st.info(f"**Declaration:** {st.session_state.declaration}")

    col1, col2 = st.columns([1.2, 1])

    with col1:
        uploaded = st.file_uploader(
            "Upload document image",
            type=["jpg", "jpeg", "png"],
            help="Bill of Lading, Transit Permit, or Driver ID"
        )

        if uploaded:
            image = Image.open(uploaded)
            st.session_state.image_obj = image
            metadata = extract_exif(image)
            st.session_state.metadata_str = metadata
            st.image(image, caption="Uploaded document", use_container_width=True)

    with col2:
        if st.session_state.image_obj:
            st.markdown("**EXIF Metadata Analysis**")
            meta = st.session_state.metadata_str
            if "No EXIF" in meta:
                st.warning("⚠ No metadata detected — possible screenshot or synthetic image")
            else:
                st.success("✓ Original EXIF metadata present")
                with st.expander("View raw metadata"):
                    st.code(meta, language="json")

    st.divider()

    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col_next:
        if st.button("Run Forensic Audit →", use_container_width=True, type="primary"):
            if not st.session_state.image_obj:
                st.error("Please upload a document image.")
            else:
                st.session_state.step = 3
                st.rerun()


# ─────────────────────────────────────────────
# STEP 3 — GEMINI AUDIT (runs automatically)
# ─────────────────────────────────────────────

elif st.session_state.step == 3:
    st.subheader("Step 3 — Forensic Audit in Progress")

    if st.session_state.audit_result is None:
        with st.spinner("🔬 Gemini is auditing the chain of custody..."):
            try:
                result = call_gemini_audit(
                    declaration=st.session_state.declaration,
                    image=st.session_state.image_obj,
                    metadata=st.session_state.metadata_str,
                    vehicle_reg=st.session_state.vehicle_reg,
                    border=st.session_state.border_post,
                    cargo=st.session_state.cargo_type,
                    weight=st.session_state.weight_kg,
                    permit=st.session_state.permit_no,
                    dest=st.session_state.dest_country
                )
                st.session_state.audit_result = result
            except Exception as e:
                st.error(f"Gemini audit failed: {e}")
                st.stop()

        # Extract status from Gemini response
        result_text = st.session_state.audit_result
        if "FRAUD ALERT" in result_text:
            verdict = "FRAUD ALERT"
        elif "WARNING" in result_text:
            verdict = "WARNING"
        else:
            verdict = "CLEARED"

        # Build doc hash
        timestamp = datetime.utcnow().isoformat() + "Z"
        hash_input = {
            "declaration": st.session_state.declaration,
            "vehicle_reg": st.session_state.vehicle_reg,
            "driver_id": st.session_state.driver_id,
            "permit": st.session_state.permit_no,
            "border": st.session_state.border_post,
            "verdict": verdict,
            "ts": timestamp
        }
        doc_hash = generate_hash(hash_input)
        doc_ref = f"BF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        st.session_state.doc_hash = doc_hash
        st.session_state.doc_ref = doc_ref
        st.session_state.timestamp = timestamp
        st.session_state.verdict = verdict

        # Generate audio script
        # Pull first discrepancy/reason from audit text if flagged
        reason = ""
        if verdict != "CLEARED":
            lines = result_text.split("\n")
            for line in lines:
                if "DISCREPAN" in line.upper() or "MISMATCH" in line.upper():
                    reason = line.strip()[:120]
                    break
        audio_script = build_audio_script(verdict, doc_ref, reason)
        st.session_state.audio_script = audio_script

        # Record to Solana
        with st.spinner("⛓ Recording to Solana ledger..."):
            ledger = record_solana(doc_hash, verdict, doc_ref, timestamp)
            st.session_state.ledger_result = ledger

        # Generate ElevenLabs audio
        with st.spinner("🔊 Generating driver audio..."):
            audio = call_elevenlabs(audio_script)
            st.session_state.audio_bytes = audio

        st.session_state.step = 4
        st.rerun()

    else:
        st.session_state.step = 4
        st.rerun()


# ─────────────────────────────────────────────
# STEP 4 — RESULTS
# ─────────────────────────────────────────────

elif st.session_state.step == 4:
    verdict = st.session_state.get("verdict", "CLEARED")
    doc_ref = st.session_state.get("doc_ref", "BF-UNKNOWN")
    doc_hash = st.session_state.get("doc_hash", "")
    timestamp = st.session_state.get("timestamp", "")
    audit_text = st.session_state.get("audit_result", "")
    ledger = st.session_state.get("ledger_result", {})
    audio_bytes = st.session_state.get("audio_bytes")

    # Verdict banner
    if verdict == "CLEARED":
        verdict_class = "verdict-approved"
        icon = "✅"
        verdict_label = "PRE-CLEARANCE APPROVED"
    elif verdict == "WARNING":
        verdict_class = "verdict-warning"
        icon = "⚠️"
        verdict_label = "SECONDARY INSPECTION REQUIRED"
    else:
        verdict_class = "verdict-flagged"
        icon = "🚫"
        verdict_label = "CLEARANCE DENIED — FRAUD ALERT"

    st.markdown(f"""
    <div class="{verdict_class}">
        <h2 style="margin:0;">{icon} {verdict_label}</h2>
        <p style="margin:6px 0 0; font-size:12px; color:#4a7a5e;">
            Ref: {doc_ref} &nbsp;·&nbsp; {timestamp[:19].replace('T', ' ')} UTC
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Driver audio
    st.markdown("#### 🔊 Driver Audio Notification")
    if audio_bytes:
        st.audio(audio_bytes, format="audio/mp3")
        st.caption(f"*\"{st.session_state.get('audio_script', '')}\"*")
    else:
        st.caption(f"*\"{st.session_state.get('audio_script', '')}\"*")
        if not ELEVENLABS_KEY:
            st.info("💡 Add `ELEVENLABS_KEY` to secrets.toml to enable live audio playback")

    st.divider()

    # Two column layout: Gemini report + ledger
    col1, col2 = st.columns([1.4, 1])

    with col1:
        st.markdown("#### 📋 Gemini Forensic Report")
        # Parse and display formatted sections
        sections = {
            "EXTRACTED DOCUMENT DATA": "📄",
            "DISCREPANCIES FOUND": "🔍",
            "FORENSIC OBSERVATIONS": "🧬",
            "PHYSICAL LOGIC ASSESSMENT": "⚖️",
            "REGULATORY COMPLIANCE": "📜",
        }

        current_section = None
        section_content = {}
        status_line = ""
        confidence = ""
        action = ""

        for line in audit_text.split("\n"):
            if line.startswith("AUDIT STATUS:"):
                status_line = line
            elif line.startswith("CONFIDENCE SCORE:"):
                confidence = line
            elif line.startswith("RECOMMENDED ACTION:"):
                action = line
            else:
                for sec in sections:
                    if line.startswith(sec):
                        current_section = sec
                        section_content[sec] = []
                        break
                else:
                    if current_section and line.strip():
                        section_content[current_section].append(line)

        # Show metrics row
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Audit Status", verdict)
        with m2:
            conf_val = confidence.replace("CONFIDENCE SCORE:", "").strip()
            st.metric("Confidence", conf_val if conf_val else "—")
        with m3:
            act_val = action.replace("RECOMMENDED ACTION:", "").strip()
            st.metric("Action", act_val[:20] if act_val else "—")

        for sec, emoji in sections.items():
            content = section_content.get(sec, [])
            if content:
                with st.expander(f"{emoji} {sec.title()}", expanded=(sec == "DISCREPANCIES FOUND")):
                    for line in content:
                        if line.strip():
                            st.markdown(line)

    with col2:
        # Rule-based checks
        st.markdown("#### ✅ Rule-Based Checks")

        id_ok, id_msg = luhn_check(st.session_state.driver_id)
        st.markdown(f"{'✅' if id_ok else '❌'} **SA ID** — {id_msg[:50]}")

        p_ok, p_msg = validate_permit(st.session_state.permit_no, st.session_state.cargo_type)
        st.markdown(f"{'✅' if p_ok else '❌'} **Permit** — {p_msg[:50]}")

        w_sev, w_msg = validate_weight(st.session_state.weight_kg)
        w_icon = "✅" if w_sev == "PASS" else ("⚠️" if w_sev == "WARN" else "❌")
        st.markdown(f"{w_icon} **Weight** — {w_msg[:50]}")

        r_ok, r_msg = validate_route(st.session_state.border_post, st.session_state.dest_country)
        st.markdown(f"{'✅' if r_ok else '❌'} **Route** — {r_msg[:50]}")

        exif_ok = "No EXIF" not in st.session_state.metadata_str
        st.markdown(f"{'✅' if exif_ok else '⚠️'} **EXIF** — {'Original metadata present' if exif_ok else 'No metadata — possible screenshot'}")

        st.divider()

        # Solana ledger
        st.markdown("#### ⛓ Solana Ledger")

        solana_payload = {
            "document_hash": doc_hash,
            "verification_status": verdict,
            "doc_ref": doc_ref,
            "timestamp": timestamp,
            "flags_raised": sum([not id_ok, not p_ok, w_sev == "FAIL", not r_ok])
        }

        st.markdown(f"""
        <div class="json-block">{json.dumps(solana_payload, indent=2)}</div>
        """, unsafe_allow_html=True)

        if ledger:
            net_status = "🟢 ON-CHAIN" if ledger.get("success") else "🟡 SIMULATED"
            st.markdown(f"**Network:** {ledger.get('network', 'devnet')} · {net_status}")
            if ledger.get("explorer_url"):
                st.markdown(f"[View on Solana Explorer ↗]({ledger['explorer_url']})")
            if ledger.get("note"):
                st.caption(ledger["note"])
            if ledger.get("error"):
                st.caption(f"Error: {ledger['error']}")

    st.divider()

    # Actions
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 New Audit", use_container_width=True, type="primary"):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.rerun()
    with col_b:
        if st.button("📥 Download Report", use_container_width=True):
            report = {
                "borderflow_report": {
                    "doc_ref": doc_ref,
                    "timestamp": timestamp,
                    "verdict": verdict,
                    "solana_payload": solana_payload,
                    "ledger": ledger,
                    "audio_script": st.session_state.get("audio_script", ""),
                    "gemini_audit": audit_text,
                    "rule_checks": {
                        "sa_id": {"passed": id_ok, "detail": id_msg},
                        "permit": {"passed": p_ok, "detail": p_msg},
                        "weight": {"severity": w_sev, "detail": w_msg},
                        "route": {"passed": r_ok, "detail": r_msg},
                        "exif": {"original_metadata": exif_ok}
                    }
                }
            }
            st.download_button(
                "⬇️ Download JSON",
                data=json.dumps(report, indent=2),
                file_name=f"borderflow_{doc_ref}.json",
                mime="application/json"
            )