"""Rolling uptime and error-budget calculations.

Error-budget math follows the standard SRE definition: if a service has an SLO of
99.9% over a window, its error budget is the remaining 0.1% of allowed failures.
`error_budget_consumed_pct` expresses how much of that 0.1% has actually been used,
so values over 100% mean the SLO itself has been breached, not just the budget warned.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class BudgetStatus:
    target: str
    slo_target_pct: float
    window_days: int
    total_checks: int
    successful_checks: int
    uptime_pct: float
    error_budget_consumed_pct: float
    is_breached: bool
    is_warning: bool


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def filter_window(records: list[dict], target: str, window_days: int) -> list[dict]:
    """Return records for a given target within the last `window_days`."""
    cutoff = datetime.now(UTC) - timedelta(days=window_days)
    return [r for r in records if r["target"] == target and _parse_ts(r["timestamp"]) >= cutoff]


def compute_budget(
    records: list[dict],
    target: str,
    slo_target_pct: float,
    window_days: int,
    warn_threshold_pct: float,
) -> BudgetStatus:
    window = filter_window(records, target, window_days)
    total = len(window)
    successful = sum(1 for r in window if r["success"])

    if total == 0:
        # No data yet (e.g. first run) - assume healthy rather than flagging a false alarm.
        return BudgetStatus(
            target=target,
            slo_target_pct=slo_target_pct,
            window_days=window_days,
            total_checks=0,
            successful_checks=0,
            uptime_pct=100.0,
            error_budget_consumed_pct=0.0,
            is_breached=False,
            is_warning=False,
        )

    uptime_pct = (successful / total) * 100
    allowed_failure_pct = max(100 - slo_target_pct, 1e-6)
    actual_failure_pct = max(100 - uptime_pct, 0.0)
    consumed_pct = (actual_failure_pct / allowed_failure_pct) * 100

    return BudgetStatus(
        target=target,
        slo_target_pct=slo_target_pct,
        window_days=window_days,
        total_checks=total,
        successful_checks=successful,
        uptime_pct=round(uptime_pct, 4),
        error_budget_consumed_pct=round(consumed_pct, 2),
        is_breached=consumed_pct >= 100,
        is_warning=consumed_pct >= warn_threshold_pct,
    )
