"""
BorderFlow AI: Forensic Auditor — Hackathon Edition
Streamlit app with Gemini Vision, ElevenLabs TTS, and Solana proof-of-cargo.
"""

import streamlit as st
from PIL import Image
import io
import json
from datetime import datetime, timezone

from models import ForensicAudit
from validation import (
    luhn_check, validate_permit, validate_weight, validate_route,
    compute_verdict, exif_present,
    generate_hash, hash_bytes, extract_exif, build_audio_script,
)

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
# SERVICES
# ─────────────────────────────────────────────
# Imported here rather than at the top of the file: services.gemini hard-stops
# the app via st.error()/st.stop() when GEMINI_KEY is missing, and Streamlit
# requires st.set_page_config() to be the first Streamlit command in the
# script, so this import must come after it.

from services.gemini import call_gemini_audit, is_configured as gemini_configured
from services.elevenlabs import call_elevenlabs, is_configured as elevenlabs_configured
from services.solana import record_solana, is_configured as solana_configured


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
    "doc_bytes": None,
    "document_hash": None,
    "audit_hash": None,
    "doc_ref": None,
    "timestamp": None,
    "verdict": None,
    "audio_script": "",
    "ledger_result": None,
    "audio_bytes": None,
    "image_obj": None,
    "metadata_str": "",
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🛡️ BorderFlow AI")
    st.markdown("*BMA Forensic Pre-Clearance*")
    st.divider()

    st.markdown("**Integration Status**")

    gemini_ok = gemini_configured()
    el_ok = elevenlabs_configured()
    sol_ok = solana_configured()

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
            doc_bytes = uploaded.getvalue()
            st.session_state.doc_bytes = doc_bytes
            st.session_state.document_hash = hash_bytes(doc_bytes)

            image = Image.open(io.BytesIO(doc_bytes))
            st.session_state.image_obj = image
            metadata = extract_exif(image)
            st.session_state.metadata_str = metadata
            st.image(image, caption="Uploaded document", use_container_width=True)
            st.code(f"SHA-256: {st.session_state.document_hash}", language=None)

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
                audit = call_gemini_audit(
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
                st.session_state.audit_result = audit
            except Exception as e:
                st.error(f"Gemini audit failed: {e}")
                st.stop()

        # Rule-based checks feed the verdict alongside Gemini's findings
        id_ok, _ = luhn_check(st.session_state.driver_id)
        permit_ok, _ = validate_permit(st.session_state.permit_no, st.session_state.cargo_type)
        weight_severity, _ = validate_weight(st.session_state.weight_kg)
        route_ok, _ = validate_route(st.session_state.border_post, st.session_state.dest_country)
        exif_ok = exif_present(st.session_state.metadata_str)

        verdict = compute_verdict(
            audit=audit,
            id_ok=id_ok,
            permit_ok=permit_ok,
            weight_severity=weight_severity,
            route_ok=route_ok,
            exif_ok=exif_ok,
        )

        # Build audit hash — one timestamp source drives both timestamp and doc_ref
        now = datetime.now(timezone.utc)
        timestamp = now.isoformat().replace("+00:00", "Z")
        doc_ref = f"BF-{now.strftime('%Y%m%d%H%M%S')}"

        hash_input = {
            "declaration": st.session_state.declaration,
            "vehicle_reg": st.session_state.vehicle_reg,
            "driver_id": st.session_state.driver_id,
            "permit": st.session_state.permit_no,
            "border": st.session_state.border_post,
            "document_hash": st.session_state.document_hash,
            "verdict": verdict,
            "ts": timestamp
        }
        audit_hash = generate_hash(hash_input)
        st.session_state.audit_hash = audit_hash
        st.session_state.doc_ref = doc_ref
        st.session_state.timestamp = timestamp
        st.session_state.verdict = verdict

        # Generate audio script
        reason = "; ".join(audit.discrepancies)[:120] if verdict != "CLEARED" else ""
        audio_script = build_audio_script(verdict, doc_ref, reason)
        st.session_state.audio_script = audio_script

        # Record to Solana
        with st.spinner("⛓ Recording to Solana ledger..."):
            ledger = record_solana(
                document_hash=st.session_state.document_hash,
                audit_hash=audit_hash,
                status=verdict,
                doc_ref=doc_ref,
                timestamp=timestamp,
            )
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
    document_hash = st.session_state.get("document_hash", "")
    audit_hash = st.session_state.get("audit_hash", "")
    timestamp = st.session_state.get("timestamp", "")
    audit: ForensicAudit = st.session_state.get("audit_result")
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
        if not elevenlabs_configured():
            st.info("💡 Add `ELEVENLABS_KEY` to secrets.toml to enable live audio playback")

    st.divider()

    # Two column layout: Gemini report + ledger
    col1, col2 = st.columns([1.4, 1])

    with col1:
        st.markdown("#### 📋 Gemini Forensic Report")

        # Show metrics row
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Audit Status", verdict)
        with m2:
            st.metric("Confidence", f"{audit.confidence_score}/10")
        with m3:
            st.metric("Action", audit.recommended_action.replace("_", " ").title()[:20])

        with st.expander("📄 Extracted Document Data"):
            if audit.extracted_data:
                for key, value in audit.extracted_data.items():
                    st.markdown(f"- **{key}:** {value}")
            else:
                st.markdown("No fields extracted.")

        with st.expander("🔍 Discrepancies Found", expanded=bool(audit.discrepancies)):
            if audit.discrepancies:
                for item in audit.discrepancies:
                    st.markdown(f"- {item}")
            else:
                st.markdown("None found.")

        with st.expander("🧬 Forensic Observations"):
            st.markdown(audit.forensic_observations)

        with st.expander("⚖️ Physical Logic Assessment"):
            st.markdown(audit.physical_logic_assessment)

        with st.expander("📜 Regulatory Compliance"):
            st.markdown(audit.regulatory_compliance)

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

        exif_ok = exif_present(st.session_state.metadata_str)
        st.markdown(f"{'✅' if exif_ok else '⚠️'} **EXIF** — {'Original metadata present' if exif_ok else 'No metadata — possible screenshot'}")

        st.divider()

        # Solana ledger
        st.markdown("#### ⛓ Solana Ledger")

        solana_payload = {
            "document_hash": document_hash,
            "audit_hash": audit_hash,
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
                    "gemini_audit": audit.model_dump(),
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
