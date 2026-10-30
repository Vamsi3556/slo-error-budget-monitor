from unittest.mock import MagicMock, patch

import requests

from slo_monitor import checker

TARGET = {
    "name": "svc",
    "url": "https://example.com",
    "expected_status": [200],
    "max_latency_ms": 5000,
}


def _mock_response(status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


@patch("slo_monitor.checker.requests.request")
def test_run_check_success(mock_request):
    mock_request.return_value = _mock_response(200)
    result = checker.run_check(TARGET)
    assert result.success
    assert result.status_code == 200
    assert result.error is None


@patch("slo_monitor.checker.requests.request")
def test_run_check_unexpected_status_is_a_failure(mock_request):
    mock_request.return_value = _mock_response(500)
    result = checker.run_check(TARGET)
    assert not result.success
    assert result.status_code == 500


@patch("slo_monitor.checker.requests.request")
def test_run_check_handles_request_exception(mock_request):
    mock_request.side_effect = requests.ConnectionError("boom")
    result = checker.run_check(TARGET)
    assert not result.success
    assert result.status_code is None
    assert "boom" in result.error


@patch("slo_monitor.checker.requests.request")
def test_run_checks_runs_every_target(mock_request):
    mock_request.return_value = _mock_response(200)
    results = checker.run_checks([TARGET, {**TARGET, "name": "svc-2"}])
    assert [r.target for r in results] == ["svc", "svc-2"]
