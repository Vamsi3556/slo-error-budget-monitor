from slo_monitor import budget, issues


def test_incident_body_includes_target_url_and_postmortem_template():
    body = issues.incident_body(
        target="svc",
        url="https://example.com",
        status_code=500,
        error="server error",
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert "svc" in body
    assert "https://example.com" in body
    assert "500" in body
    assert "Blameless Postmortem" in body


def test_incident_body_handles_missing_status_and_error():
    body = issues.incident_body(
        target="svc",
        url="https://example.com",
        status_code=None,
        error=None,
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert "no response" in body


def test_budget_warning_body_includes_metrics():
    records = [{"target": "svc", "success": False, "timestamp": "2026-01-01T00:00:00+00:00"}] * 10
    status = budget.compute_budget(
        records, "svc", slo_target_pct=99.9, window_days=3650, warn_threshold_pct=50
    )
    body = issues.budget_warning_body(status)
    assert "svc" in body
    assert str(status.error_budget_consumed_pct) in body
    assert str(status.total_checks) in body
