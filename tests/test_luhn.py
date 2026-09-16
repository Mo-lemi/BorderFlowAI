from datetime import datetime, timedelta

from app import luhn_check


def _find_check_digit(base12: str) -> str:
    """Brute-force the 13th (checksum) digit by asking luhn_check itself
    which candidate is *not* rejected for a bad checksum, so the test
    never reimplements the Luhn algorithm."""
    for digit in "0123456789":
        _, message = luhn_check(base12 + digit)
        if "Checksum invalid" not in message:
            return digit
    raise AssertionError(f"no valid checksum digit found for base {base12!r}")


def _id_for_age(years_old: int, seq: str = "000108") -> str:
    dob = datetime.now() - timedelta(days=years_old * 365 + 10)
    base12 = f"{dob.year % 100:02d}{dob.month:02d}{dob.day:02d}{seq}"
    return base12 + _find_check_digit(base12)


def test_valid_id_passes():
    ok, message = luhn_check(_id_for_age(36))
    assert ok is True
    assert "Valid" in message


def test_valid_id_with_surrounding_whitespace_is_stripped():
    ok, _ = luhn_check(f"  {_id_for_age(36)}  ")
    assert ok is True


def test_wrong_length_is_rejected():
    ok, message = luhn_check("123456789012")  # 12 digits, not 13
    assert ok is False
    assert "13 digits" in message


def test_non_digit_characters_are_rejected():
    tampered = "A" + _id_for_age(36)[1:]
    ok, message = luhn_check(tampered)
    assert ok is False
    assert "13 digits" in message


def test_bad_checksum_is_rejected():
    id_number = _id_for_age(36)
    last_digit = int(id_number[-1])
    tampered = id_number[:-1] + str((last_digit + 1) % 10)
    ok, message = luhn_check(tampered)
    assert ok is False
    assert "Checksum invalid" in message


def test_invalid_embedded_date_is_rejected():
    base12 = "991301000108"  # month 13 does not exist
    id_number = base12 + _find_check_digit(base12)
    ok, message = luhn_check(id_number)
    assert ok is False
    assert "date of birth is invalid" in message


def test_age_exactly_18_is_valid():
    ok, _ = luhn_check(_id_for_age(18))
    assert ok is True


def test_age_17_is_rejected_as_too_young():
    ok, message = luhn_check(_id_for_age(17))
    assert ok is False
    assert "anomalous" in message


def test_age_exactly_80_is_valid():
    ok, _ = luhn_check(_id_for_age(80))
    assert ok is True


def test_age_81_is_rejected_as_too_old():
    ok, message = luhn_check(_id_for_age(81))
    assert ok is False
    assert "anomalous" in message
