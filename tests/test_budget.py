from datetime import UTC, datetime, timedelta

from slo_monitor import budget


def _record(target: str, success: bool, days_ago: float = 0) -> dict:
    ts = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()
    return {"target": target, "success": success, "timestamp": ts}


def test_compute_budget_with_no_data_assumes_healthy():
    status = budget.compute_budget(
        [], "svc", slo_target_pct=99.9, window_days=7, warn_threshold_pct=50
    )
    assert status.total_checks == 0
    assert status.uptime_pct == 100.0
    assert not status.is_breached
    assert not status.is_warning


def test_compute_budget_all_successful_consumes_no_budget():
    records = [_record("svc", True) for _ in range(10)]
    status = budget.compute_budget(records, "svc", 99.9, 7, 50)
    assert status.uptime_pct == 100.0
    assert status.error_budget_consumed_pct == 0.0
    assert not status.is_warning
    assert not status.is_breached


def test_compute_budget_detects_warning_and_breach():
    records = [_record("svc", True) for _ in range(95)] + [_record("svc", False) for _ in range(5)]
    status = budget.compute_budget(records, "svc", 99.9, 7, 50)
    assert status.total_checks == 100
    assert status.uptime_pct == 95.0
    assert status.is_warning
    # a 5% failure rate vastly exceeds a 0.1% allowed error budget
    assert status.is_breached


def test_compute_budget_ignores_records_outside_window():
    records = [_record("svc", False, days_ago=30)]
    records += [_record("svc", True, days_ago=0) for _ in range(5)]
    status = budget.compute_budget(records, "svc", 99.9, window_days=7, warn_threshold_pct=50)
    assert status.total_checks == 5
    assert status.uptime_pct == 100.0


def test_compute_budget_filters_by_target():
    records = [_record("svc-a", False) for _ in range(5)]
    records += [_record("svc-b", True) for _ in range(5)]
    status = budget.compute_budget(records, "svc-b", 99.9, window_days=7, warn_threshold_pct=50)
    assert status.total_checks == 5
    assert status.uptime_pct == 100.0
