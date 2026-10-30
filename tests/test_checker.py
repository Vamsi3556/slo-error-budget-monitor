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


@patch("slo_monitor.checker.requests.request")
def test_unexpected_status_is_explained(mock_request):
    mock_request.return_value = _mock_response(403)
    result = checker.run_check(TARGET)
    assert result.error == "unexpected status 403, expected one of [200]"


@patch("slo_monitor.checker.time")
@patch("slo_monitor.checker.requests.request")
def test_slow_response_is_explained(mock_request, mock_time):
    mock_request.return_value = _mock_response(200)
    mock_time.perf_counter.side_effect = [0.0, 5.0]
    result = checker.run_check({**TARGET, "max_latency_ms": 1000})
    assert not result.success
    assert result.status_code == 200
    assert result.error == "latency 5000ms exceeded the 1000ms limit"


@patch("slo_monitor.checker.requests.request")
def test_successful_check_has_no_error(mock_request):
    mock_request.return_value = _mock_response(200)
    assert checker.run_check(TARGET).error is None


@patch("slo_monitor.checker.requests.request")
def test_bearer_token_comes_from_the_named_environment_variable(mock_request, monkeypatch):
    monkeypatch.setenv("SLO_TEST_TOKEN", "s3cret")
    mock_request.return_value = _mock_response(200)
    checker.run_check({**TARGET, "bearer_token_env": "SLO_TEST_TOKEN"})
    assert mock_request.call_args.kwargs["headers"] == {"Authorization": "Bearer s3cret"}


@patch("slo_monitor.checker.requests.request")
def test_check_runs_unauthenticated_when_the_variable_is_not_set(mock_request, monkeypatch):
    monkeypatch.delenv("SLO_TEST_TOKEN", raising=False)
    mock_request.return_value = _mock_response(200)
    checker.run_check({**TARGET, "bearer_token_env": "SLO_TEST_TOKEN"})
    assert mock_request.call_args.kwargs["headers"] == {}


@patch("slo_monitor.checker.requests.request")
def test_bearer_token_is_never_sent_over_plain_http(mock_request, monkeypatch):
    monkeypatch.setenv("SLO_TEST_TOKEN", "s3cret")
    mock_request.return_value = _mock_response(200)
    target = {**TARGET, "url": "http://example.com", "bearer_token_env": "SLO_TEST_TOKEN"}
    checker.run_check(target)
    assert mock_request.call_args.kwargs["headers"] == {}


@patch("slo_monitor.checker.requests.request")
def test_no_token_header_without_configuration(mock_request, monkeypatch):
    monkeypatch.setenv("SLO_TEST_TOKEN", "s3cret")
    mock_request.return_value = _mock_response(200)
    checker.run_check(TARGET)
    assert mock_request.call_args.kwargs["headers"] == {}
