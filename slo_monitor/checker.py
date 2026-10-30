"""Synthetic HTTP checks against configured targets."""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

import requests

DEFAULT_TIMEOUT_S = 10.0
DEFAULT_MAX_LATENCY_MS = 5000


@dataclass(frozen=True)
class CheckResult:
    target: str
    url: str
    timestamp: str
    status_code: int | None
    latency_ms: float
    success: bool
    error: str | None = None


def run_check(target: dict, timeout_s: float = DEFAULT_TIMEOUT_S) -> CheckResult:
    """Perform a single synthetic HTTP check against a target definition.

    A check is successful only if the response status code is one of the target's
    expected codes AND the observed latency is within the configured budget. Any
    network-level failure (timeout, DNS, connection refused, ...) is recorded as a
    failed check rather than raising, so a single bad check never crashes the run.
    """
    url = target["url"]
    method = target.get("method", "GET")
    expected_status = set(target.get("expected_status", [200]))
    max_latency_ms = target.get("max_latency_ms", DEFAULT_MAX_LATENCY_MS)

    start = time.perf_counter()
    try:
        response = requests.request(method, url, timeout=timeout_s)
        latency_ms = (time.perf_counter() - start) * 1000
        success = response.status_code in expected_status and latency_ms <= max_latency_ms
        return CheckResult(
            target=target["name"],
            url=url,
            timestamp=datetime.now(UTC).isoformat(),
            status_code=response.status_code,
            latency_ms=round(latency_ms, 2),
            success=success,
        )
    except requests.RequestException as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            target=target["name"],
            url=url,
            timestamp=datetime.now(UTC).isoformat(),
            status_code=None,
            latency_ms=round(latency_ms, 2),
            success=False,
            error=str(exc),
        )


def run_checks(targets: Iterable[dict], timeout_s: float = DEFAULT_TIMEOUT_S) -> list[CheckResult]:
    return [run_check(target, timeout_s=timeout_s) for target in targets]
