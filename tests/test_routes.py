from validation.rules import validate_route


def test_known_border_with_allowed_destination():
    ok, message = validate_route("Beit Bridge (ZA/ZW)", "ZW")
    assert ok is True
    assert "valid for" in message


def test_known_border_with_disallowed_destination():
    ok, message = validate_route("Beit Bridge (ZA/ZW)", "MZ")
    assert ok is False
    assert "does not serve" in message


def test_border_name_matching_is_case_insensitive():
    ok, _ = validate_route("LEBOMBO", "mz")
    assert ok is True


def test_destination_matching_is_case_insensitive():
    ok, _ = validate_route("Oshoek", "sz")
    assert ok is True


def test_unrecognized_border_defaults_to_permissive_pass():
    ok, message = validate_route("Some Random Crossing", "XX")
    assert ok is True
    assert "cross-check passed" in message


def test_single_country_border_rejects_other_destination():
    ok, message = validate_route("Kopfontein", "ZW")
    assert ok is False
    assert "does not serve" in message
