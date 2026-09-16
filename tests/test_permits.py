from datetime import datetime

from app import validate_permit

CURRENT_YEAR = datetime.now().year


def test_valid_permit_matching_cargo_class():
    ok, message = validate_permit(f"BMA-TP-{CURRENT_YEAR}-00001", "General Freight")
    assert ok is True
    assert "Valid" in message


def test_lowercase_and_whitespace_are_normalized():
    ok, _ = validate_permit(f"bma-tp-{CURRENT_YEAR}-00001  ", "General Freight")
    assert ok is True


def test_malformed_format_is_rejected():
    ok, message = validate_permit("NOT-A-PERMIT", "General Freight")
    assert ok is False
    assert "Format invalid" in message


def test_unknown_class_code_is_rejected():
    ok, message = validate_permit(f"BMA-XX-{CURRENT_YEAR}-00001", "General Freight")
    assert ok is False
    assert "Format invalid" in message


def test_serial_below_min_length_is_rejected():
    ok, message = validate_permit(f"BMA-TP-{CURRENT_YEAR}-001", "General Freight")  # 3 digits
    assert ok is False
    assert "Format invalid" in message


def test_serial_at_min_length_is_accepted():
    ok, _ = validate_permit(f"BMA-TP-{CURRENT_YEAR}-0001", "General Freight")  # 4 digits
    assert ok is True


def test_serial_at_max_length_is_accepted():
    ok, _ = validate_permit(f"BMA-TP-{CURRENT_YEAR}-123456", "General Freight")  # 6 digits
    assert ok is True


def test_serial_above_max_length_is_rejected():
    ok, message = validate_permit(f"BMA-TP-{CURRENT_YEAR}-1234567", "General Freight")  # 7 digits
    assert ok is False
    assert "Format invalid" in message


def test_permit_year_one_year_old_is_still_valid():
    ok, _ = validate_permit(f"BMA-TP-{CURRENT_YEAR - 1}-00001", "General Freight")
    assert ok is True


def test_permit_year_two_years_old_is_expired():
    ok, message = validate_permit(f"BMA-TP-{CURRENT_YEAR - 2}-00001", "General Freight")
    assert ok is False
    assert "expired" in message


def test_permit_year_in_the_future_is_invalid():
    ok, message = validate_permit(f"BMA-TP-{CURRENT_YEAR + 1}-00001", "General Freight")
    assert ok is False
    assert "expired or invalid" in message


def test_cargo_class_mismatch_is_rejected():
    ok, message = validate_permit(f"BMA-TP-{CURRENT_YEAR}-00001", "Hazardous Materials")
    assert ok is False
    assert "requires HZ" in message


def test_unknown_cargo_type_defaults_to_tp_requirement():
    ok, _ = validate_permit(f"BMA-TP-{CURRENT_YEAR}-00001", "Some Unlisted Cargo")
    assert ok is True


def test_unknown_cargo_type_rejects_non_tp_permit():
    ok, message = validate_permit(f"BMA-HZ-{CURRENT_YEAR}-00001", "Some Unlisted Cargo")
    assert ok is False
    assert "requires TP" in message
