"""Entry point: run checks, update history, evaluate error budgets, file incidents."""

from __future__ import annotations

import argparse
import os
import sys

import yaml

from . import budget, checker, history, issues


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SLO / error-budget checks.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run checks and print results without writing history or filing issues.",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    token = os.environ.get("GITHUB_TOKEN", "")
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    results = checker.run_checks(config["targets"])

    records = history.load_history(config["history_file"])
    for r in results:
        records.append(
            {
                "target": r.target,
                "url": r.url,
                "timestamp": r.timestamp,
                "status_code": r.status_code,
                "latency_ms": r.latency_ms,
                "success": r.success,
                "error": r.error,
            }
        )

    if not args.dry_run:
        history.save_history(
            config["history_file"], records, max_records=config.get("max_history_records", 5000)
        )

    had_incident = False
    for target_cfg in config["targets"]:
        name = target_cfg["name"]
        result = next(r for r in results if r.target == name)

        if not result.success:
            had_incident = True
            print(f"[FAIL] {name}: status={result.status_code} error={result.error}")
            _file_incident_if_new(args, token, webhook_url, name, result)
        else:
            print(f"[OK]   {name}: status={result.status_code} latency={result.latency_ms}ms")

        status = budget.compute_budget(
            records,
            target=name,
            slo_target_pct=target_cfg["slo_target_pct"],
            window_days=config.get("window_days", 7),
            warn_threshold_pct=config.get("warn_threshold_pct", 50),
        )
        print(
            f"       budget: uptime={status.uptime_pct}% "
            f"consumed={status.error_budget_consumed_pct}% (n={status.total_checks})"
        )
        _handle_budget_warning(args, token, webhook_url, name, status)

    return 1 if had_incident else 0


def _file_incident_if_new(args, token, webhook_url, name, result) -> None:
    if args.dry_run or not args.repo or not token:
        return
    label = f"incident:{name}"
    if issues.find_open_issue(args.repo, token, label):
        return
    issues.create_issue(
        args.repo,
        token,
        title=f"Incident: {name} check failed",
        body=issues.incident_body(
            name, result.url, result.status_code, result.error, result.timestamp
        ),
        labels=["incident", label],
    )
    issues.notify_webhook(webhook_url, f"Incident filed for {name} - check failed.")


def _handle_budget_warning(args, token, webhook_url, name, status) -> None:
    if args.dry_run or not args.repo or not token:
        return
    warn_label = f"error-budget-warning:{name}"
    existing_warning = issues.find_open_issue(args.repo, token, warn_label)

    if status.is_warning and not existing_warning:
        issues.create_issue(
            args.repo,
            token,
            title=f"Error budget warning: {name}",
            body=issues.budget_warning_body(status),
            labels=["error-budget-warning", warn_label],
        )
        issues.notify_webhook(
            webhook_url,
            f"Error budget warning for {name} ({status.error_budget_consumed_pct}% consumed).",
        )
    elif not status.is_warning and existing_warning:
        issues.close_issue(
            args.repo,
            token,
            existing_warning["number"],
            comment=(
                f"Error budget has recovered: {status.error_budget_consumed_pct}% consumed, "
                f"uptime {status.uptime_pct}%. Closing automatically."
            ),
        )


if __name__ == "__main__":
    sys.exit(main())
