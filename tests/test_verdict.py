from app import ForensicAudit, compute_verdict, exif_present


def _audit(discrepancies=None, confidence_score=9, recommended_action="PROCEED_TO_LANE"):
    return ForensicAudit(
        extracted_data={"field": "value"},
        discrepancies=discrepancies or [],
        forensic_observations="No tampering indicators found.",
        physical_logic_assessment="Weight is plausible for the declared commodity.",
        regulatory_compliance="Permit class matches cargo type.",
        confidence_score=confidence_score,
        recommended_action=recommended_action,
    )


def _clean_checks():
    return dict(id_ok=True, permit_ok=True, weight_severity="PASS", route_ok=True, exif_ok=True)


def test_clean_pass_is_cleared():
    verdict = compute_verdict(audit=_audit(), **_clean_checks())
    assert verdict == "CLEARED"


def test_failed_id_forces_fraud_alert_even_with_clean_audit():
    checks = _clean_checks()
    checks["id_ok"] = False
    verdict = compute_verdict(audit=_audit(), **checks)
    assert verdict == "FRAUD ALERT"


def test_discrepancies_with_high_confidence_is_warning_not_fraud():
    audit = _audit(discrepancies=["Weight mismatch"], confidence_score=9)
    verdict = compute_verdict(audit=audit, **_clean_checks())
    assert verdict == "WARNING"


def test_discrepancies_with_low_confidence_is_fraud_alert():
    audit = _audit(discrepancies=["Weight mismatch"], confidence_score=4)
    verdict = compute_verdict(audit=audit, **_clean_checks())
    assert verdict == "FRAUD ALERT"


def test_detain_recommendation_alone_forces_fraud_alert():
    audit = _audit(recommended_action="DETAIN_FOR_INVESTIGATION")
    verdict = compute_verdict(audit=audit, **_clean_checks())
    assert verdict == "FRAUD ALERT"


def test_weight_fail_alone_forces_fraud_alert():
    checks = _clean_checks()
    checks["weight_severity"] = "FAIL"
    verdict = compute_verdict(audit=_audit(), **checks)
    assert verdict == "FRAUD ALERT"


def test_permit_failure_alone_is_warning_not_fraud():
    checks = _clean_checks()
    checks["permit_ok"] = False
    verdict = compute_verdict(audit=_audit(), **checks)
    assert verdict == "WARNING"


def test_route_failure_alone_is_warning_not_fraud():
    checks = _clean_checks()
    checks["route_ok"] = False
    verdict = compute_verdict(audit=_audit(), **checks)
    assert verdict == "WARNING"


def test_exif_failure_alone_is_warning_not_fraud():
    checks = _clean_checks()
    checks["exif_ok"] = False
    verdict = compute_verdict(audit=_audit(), **checks)
    assert verdict == "WARNING"


def test_low_confidence_with_no_other_issues_is_warning():
    audit = _audit(confidence_score=6)
    verdict = compute_verdict(audit=audit, **_clean_checks())
    assert verdict == "WARNING"


def test_exif_present_false_when_no_exif_string():
    assert exif_present("No EXIF metadata found — possible screenshot or synthetic image") is False


def test_exif_present_true_for_real_metadata():
    assert exif_present('{"Make": "Canon", "Model": "EOS 90D"}') is True
