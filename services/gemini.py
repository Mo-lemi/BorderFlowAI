"""Gemini Vision forensic audit — the only module that talks to Gemini."""

import streamlit as st
from google import genai
from google.genai import types
from pydantic import ValidationError
from PIL import Image

from models import ForensicAudit

if "GEMINI_KEY" not in st.secrets:
    st.error("❌ Missing `GEMINI_KEY` in `.streamlit/secrets.toml`")
    st.stop()

GEMINI_KEY = st.secrets["GEMINI_KEY"]

client = genai.Client(api_key=GEMINI_KEY)


def is_configured() -> bool:
    return bool(GEMINI_KEY)


def call_gemini_audit(declaration: str, image: Image.Image, metadata: str,
                      vehicle_reg: str, border: str, cargo: str,
                      weight: float, permit: str, dest: str) -> ForensicAudit:
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
"""
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[prompt, image],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ForensicAudit,
        ),
    )
    try:
        return ForensicAudit.model_validate_json(response.text)
    except ValidationError as e:
        raise RuntimeError("Gemini returned malformed audit data") from e
