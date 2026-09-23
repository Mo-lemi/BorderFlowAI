"""Pure field validators — no Streamlit, no network, no secrets."""

import re
from datetime import datetime


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
