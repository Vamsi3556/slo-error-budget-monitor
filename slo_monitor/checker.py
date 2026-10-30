"""Synthetic HTTP checks against configured targets."""

from __future__ import annotations

import os
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


def _auth_headers(target: dict) -> dict[str, str]:
    """Build an optional bearer-token header for a target.

    The target names an environment variable with `bearer_token_env`; the token itself never
    lives in the config file. It is only sent over https, and if the variable is not set the
    check simply runs unauthenticated.
    """
    env_name = target.get("bearer_token_env")
    if not env_name or not str(target["url"]).lower().startswith("https://"):
        return {}
    token = os.environ.get(env_name)
    return {"Authorization": f"Bearer {token}"} if token else {}


def run_check(target: dict, timeout_s: float = DEFAULT_TIMEOUT_S) -> CheckResult:
    """Perform a single synthetic HTTP check against a target definition.

    A check is successful only if the response status code is one of the target's
    expected codes AND the observed latency is within the configured budget. Any
    network-level failure (timeout, DNS, connection refused, ...) is recorded as a
    failed check rather than raising, so a single bad check never crashes the run.
    A failed check always carries an `error` that says why, so the incident issue is
    actionable.
    """
    url = target["url"]
    method = target.get("method", "GET")
    expected_status = set(target.get("expected_status", [200]))
    max_latency_ms = target.get("max_latency_ms", DEFAULT_MAX_LATENCY_MS)

    start = time.perf_counter()
    try:
        response = requests.request(
            method, url, headers=_auth_headers(target), timeout=timeout_s
        )
        latency_ms = (time.perf_counter() - start) * 1000
        status_ok = response.status_code in expected_status
        latency_ok = latency_ms <= max_latency_ms
        error = None
        if not status_ok:
            error = (
                f"unexpected status {response.status_code}, "
                f"expected one of {sorted(expected_status)}"
            )
        elif not latency_ok:
            error = f"latency {latency_ms:.0f}ms exceeded the {max_latency_ms}ms limit"
        return CheckResult(
            target=target["name"],
            url=url,
            timestamp=datetime.now(UTC).isoformat(),
            status_code=response.status_code,
            latency_ms=round(latency_ms, 2),
            success=status_ok and latency_ok,
            error=error,
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
