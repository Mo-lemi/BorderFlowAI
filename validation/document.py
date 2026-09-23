"""Small pure document helpers — no Streamlit, no network, no secrets."""

import hashlib
import hmac
import json

from PIL import Image, ExifTags


def generate_hash(data: dict, key: bytes | None = None) -> str:
    """Hash of the canonical JSON form of `data`. HMAC-SHA256 when `key` is
    given, plain SHA-256 otherwise."""
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"))
    if key:
        digest = hmac.new(key, raw.encode(), hashlib.sha256).hexdigest()
    else:
        digest = hashlib.sha256(raw.encode()).hexdigest()
    return "0x" + digest.upper()


def hash_bytes(data: bytes) -> str:
    """Plain lowercase hex SHA-256, matching `sha256sum` output."""
    return hashlib.sha256(data).hexdigest()


def extract_exif(img: Image.Image) -> str:
    exif = img.getexif()
    if not exif:
        return "No EXIF metadata found — possible screenshot or synthetic image"
    readable = {ExifTags.TAGS.get(t, t): v for t, v in exif.items() if t in ExifTags.TAGS}
    return json.dumps(readable, default=str)[:800]


def build_reason(
    id_ok: bool,
    permit_ok: bool,
    weight_severity: str,
    route_ok: bool,
    exif_ok: bool,
    discrepancies: list[str],
) -> str:
    """Short human-readable reason from failed rule checks plus Gemini's
    discrepancies, capped at ~120 characters for the audio script."""
    reasons = []
    if not id_ok:
        reasons.append("driver ID failed the checksum")
    if not permit_ok:
        reasons.append("permit does not match the declared cargo")
    if weight_severity == "FAIL":
        reasons.append("declared weight exceeds the legal limit")
    elif weight_severity == "WARN":
        reasons.append("declared weight requires a weigh-bridge check")
    if not route_ok:
        reasons.append("route does not match the border post")
    if not exif_ok:
        reasons.append("document image has no original metadata")
    reasons.extend(discrepancies)
    return "; ".join(reasons)[:120]


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
