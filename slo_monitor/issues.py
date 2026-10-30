"""GitHub issue filing for incidents and error-budget warnings, plus optional webhook alerts.

Issue creation uses the GitHub REST API directly with the workflow's built-in
GITHUB_TOKEN (least-privilege, repo-scoped, auto-rotated by GitHub) - no long-lived
personal access token is stored anywhere. An optional webhook URL (e.g. Discord) can
be supplied via a GitHub Actions secret for external notifications; it is never
hardcoded in source.
"""

from __future__ import annotations

import requests

from .budget import BudgetStatus

GITHUB_API = "https://api.github.com"
REQUEST_TIMEOUT_S = 10.0


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def find_open_issue(repo: str, token: str, label: str) -> dict | None:
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/issues",
        headers=_headers(token),
        params={"state": "open", "labels": label},
        timeout=REQUEST_TIMEOUT_S,
    )
    resp.raise_for_status()
    found = resp.json()
    return found[0] if found else None


def create_issue(repo: str, token: str, title: str, body: str, labels: list[str]) -> dict:
    resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/issues",
        headers=_headers(token),
        json={"title": title, "body": body, "labels": labels},
        timeout=REQUEST_TIMEOUT_S,
    )
    resp.raise_for_status()
    return resp.json()


def close_issue(repo: str, token: str, issue_number: int, comment: str) -> None:
    requests.post(
        f"{GITHUB_API}/repos/{repo}/issues/{issue_number}/comments",
        headers=_headers(token),
        json={"body": comment},
        timeout=REQUEST_TIMEOUT_S,
    ).raise_for_status()
    requests.patch(
        f"{GITHUB_API}/repos/{repo}/issues/{issue_number}",
        headers=_headers(token),
        json={"state": "closed"},
        timeout=REQUEST_TIMEOUT_S,
    ).raise_for_status()


def incident_body(
    target: str, url: str, status_code: int | None, error: str | None, timestamp: str
) -> str:
    return f"""## Incident: {target} check failed

**Detected at:** {timestamp}
**Target URL:** {url}
**HTTP status:** {status_code if status_code is not None else "no response"}
**Error:** {error or "response did not meet expected status/latency"}

---

### Blameless Postmortem

- **What happened:** _fill in once investigated_
- **Customer/user impact:** _fill in_
- **Contributing factors:** _fill in_
- **Action items:** _fill in_

_This issue was filed automatically by the SLO monitor. No individual is being blamed -
this template exists so every incident gets investigated the same structured way._
"""


def budget_warning_body(status: BudgetStatus) -> str:
    return f"""## Error budget warning: {status.target}

- **SLO target:** {status.slo_target_pct}%
- **Rolling window:** last {status.window_days} days
- **Observed uptime:** {status.uptime_pct}%
- **Error budget consumed:** {status.error_budget_consumed_pct}%
- **Checks in window:** {status.total_checks} ({status.successful_checks} successful)

This is a proactive warning - the SLO has not necessarily been breached yet, but the
error budget is burning faster than expected. Worth investigating before it turns into
a full incident.

_This issue was filed automatically by the SLO monitor._
"""


def notify_webhook(webhook_url: str | None, message: str) -> None:
    """Best-effort external notification. Never raises - a notification failure
    should never fail the monitoring run itself."""
    if not webhook_url:
        return
    try:
        requests.post(webhook_url, json={"content": message}, timeout=REQUEST_TIMEOUT_S)
    except requests.RequestException:
        pass
