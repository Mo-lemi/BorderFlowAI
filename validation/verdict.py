"""Verdict decision logic — pure, no Streamlit, no network, no secrets."""

from models import ForensicAudit


def compute_verdict(
    audit: ForensicAudit,
    id_ok: bool,
    permit_ok: bool,
    weight_severity: str,   # "PASS" | "WARN" | "FAIL"
    route_ok: bool,
    exif_ok: bool,
) -> str:
    """Returns 'CLEARED', 'WARNING', or 'FRAUD ALERT'. This function — not
    Gemini — owns the verdict."""
    if (
        not id_ok
        or (len(audit.discrepancies) > 0 and audit.confidence_score <= 4)
        or audit.recommended_action == "DETAIN_FOR_INVESTIGATION"
        or weight_severity == "FAIL"
    ):
        return "FRAUD ALERT"

    if (
        len(audit.discrepancies) > 0
        or not permit_ok
        or not route_ok
        or not exif_ok
        or weight_severity == "WARN"
        or audit.recommended_action == "SECONDARY_INSPECTION"
        or audit.confidence_score <= 6
    ):
        return "WARNING"

    return "CLEARED"


def exif_present(metadata_str: str) -> bool:
    return "No EXIF" not in metadata_str
