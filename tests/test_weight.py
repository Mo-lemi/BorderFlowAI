from app import validate_weight


def test_typical_legal_weight_passes():
    severity, message = validate_weight(30000)
    assert severity == "PASS"
    assert "within legal limits" in message


def test_zero_weight_fails():
    severity, message = validate_weight(0)
    assert severity == "FAIL"
    assert "zero" in message


def test_negative_weight_fails():
    severity, _ = validate_weight(-500)
    assert severity == "FAIL"


def test_weight_at_48000_boundary_passes():
    severity, _ = validate_weight(48000)
    assert severity == "PASS"


def test_weight_just_above_48000_warns():
    severity, message = validate_weight(48000.01)
    assert severity == "WARN"
    assert "weigh-bridge" in message


def test_weight_at_56000_boundary_warns():
    severity, _ = validate_weight(56000)
    assert severity == "WARN"


def test_weight_just_above_56000_fails():
    severity, message = validate_weight(56000.01)
    assert severity == "FAIL"
    assert "exceeds" in message
