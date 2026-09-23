from validation.rules import validate_step1_required


def _valid_kwargs(**overrides):
    kwargs = dict(
        declaration="15 tons of furniture",
        vehicle_reg="GP 47 BW WX",
        driver_id="9005150001089",
        permit_no="BMA-TP-2026-00001",
        weight_kg=15000.0,
        dest_country="ZW",
    )
    kwargs.update(overrides)
    return kwargs


def test_all_valid_returns_no_errors():
    assert validate_step1_required(**_valid_kwargs()) == []


def test_missing_declaration_returns_error():
    errors = validate_step1_required(**_valid_kwargs(declaration="   "))
    assert "Cargo declaration is required." in errors


def test_missing_vehicle_reg_returns_error():
    errors = validate_step1_required(**_valid_kwargs(vehicle_reg=""))
    assert "Vehicle registration is required." in errors


def test_driver_id_not_13_digits_returns_error():
    errors = validate_step1_required(**_valid_kwargs(driver_id="12345"))
    assert "Driver SA ID Number must be exactly 13 digits." in errors


def test_driver_id_with_bad_checksum_but_valid_format_is_allowed():
    # 13 digits, wrong checksum — format-only check, so no error here.
    # The checksum failure is caught later, at audit time, as a fraud signal.
    errors = validate_step1_required(**_valid_kwargs(driver_id="9005150001080"))
    assert not any("Driver SA ID" in e for e in errors)


def test_missing_permit_no_returns_error():
    errors = validate_step1_required(**_valid_kwargs(permit_no=""))
    assert "BMA Permit Number is required." in errors


def test_zero_weight_returns_error():
    errors = validate_step1_required(**_valid_kwargs(weight_kg=0))
    assert "Declared weight must be greater than zero." in errors


def test_negative_weight_returns_error():
    errors = validate_step1_required(**_valid_kwargs(weight_kg=-5))
    assert "Declared weight must be greater than zero." in errors


def test_missing_dest_country_returns_error():
    errors = validate_step1_required(**_valid_kwargs(dest_country=" "))
    assert "Destination Country Code is required." in errors


def test_multiple_missing_fields_returns_multiple_errors():
    errors = validate_step1_required(**_valid_kwargs(declaration="", vehicle_reg="", weight_kg=0))
    assert len(errors) == 3
