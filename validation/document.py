"""Small pure document helpers — no Streamlit, no network, no secrets."""

import hashlib
import json

from PIL import Image, ExifTags


def generate_hash(data: dict) -> str:
    raw = json.dumps(data, sort_keys=True)
    return "0x" + hashlib.sha256(raw.encode()).hexdigest().upper()


def hash_bytes(data: bytes) -> str:
    """Plain lowercase hex SHA-256, matching `sha256sum` output."""
    return hashlib.sha256(data).hexdigest()


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
