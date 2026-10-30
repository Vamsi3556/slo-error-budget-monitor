# SLO & Error Budget Monitor

![CI](https://github.com/Vamsi3556/slo-error-budget-monitor/actions/workflows/ci.yml/badge.svg)
![SLO Monitor](https://github.com/Vamsi3556/slo-error-budget-monitor/actions/workflows/monitor.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

A synthetic-monitoring tool that checks services on a schedule, tracks rolling uptime against
an SLO target, computes error-budget burn, and **automatically files structured GitHub Issues**
when something breaks or the budget is burning too fast - so nobody has to notice problems
manually, and every incident gets the same blameless-postmortem treatment from the start.

## The problem

Teams define SLOs on paper ("99.9% uptime") but rarely track error-budget burn in real time.
By the time someone notices a problem, the budget's already gone and the response is reactive:
dig through logs, figure out what happened, write up a postmortem after the fact (if at all).
That reactive gap - between *having* an SLO and *actually acting on it* - is the difference
between doing DevOps and doing SRE.

This project closes that gap for a small set of monitored services:

- **Immediate incidents**: a failed check files a GitHub Issue the moment it happens, pre-filled
  with a blameless-postmortem template, instead of waiting for a human to notice.
- **Proactive budget warnings**: if the rolling error budget crosses a threshold (default 50%
  consumed) *before* the SLO is actually breached, it files a separate warning issue - the
  early signal most ad-hoc monitoring never gives you.
- **Self-closing**: once a service recovers and its error budget is healthy again, the warning
  issue is closed automatically with a summary comment.

## How it works

```
GitHub Actions (cron, every 30 min)
        │
        ▼
  run synthetic HTTP checks against configured targets (config.yaml)
        │
        ▼
  append result to data/history.json  ──► committed back to the repo by the workflow
        │
        ▼
  compute rolling uptime % and error-budget burn over a configurable window
        │
        ├─ check failed right now?        ──► file "incident" issue (if not already open)
        ├─ error budget crossing warn %?  ──► file "error-budget-warning" issue (if not already open)
        └─ budget recovered?              ──► close the open warning issue with a summary
```

Monitored targets are public APIs by design (see `config.yaml`), so the tool needs no stored
credentials for the services it watches. The one exception is optional: the `github-api` check
sends the workflow's own built-in `GITHUB_TOKEN` to stay clear of anonymous rate limits. Swap in
your own internal endpoints and it works the same way.

## Security practices

- **No secrets in code.** Issue creation uses the GitHub Actions workflow's built-in
  `GITHUB_TOKEN` (repo-scoped, auto-rotated, least privilege) - not a long-lived personal access
  token. An optional webhook URL for external notifications (e.g. Discord) is read from a
  GitHub Actions **secret** (`DISCORD_WEBHOOK_URL`) if configured; it is never hardcoded.
- **Least-privilege workflow permissions.** `monitor.yml` only requests `contents: write` (to
  commit history) and `issues: write` (to file/close issues) - nothing broader.
- **Static analysis (Bandit)** scans the Python source for common security issues on every push.
- **Dependency vulnerability scanning (`pip-audit`)** checks pinned dependencies against known
  CVEs on every push - this caught a real vulnerability in `requests==2.32.3` during development,
  which is why the pin is now `2.33.0`.
- **CodeQL** runs GitHub's semantic security analysis on every push.
- **Dependabot** keeps both the GitHub Actions versions and Python dependencies patched
  automatically (`.github/dependabot.yml`).
- **Tokens stay in the environment.** A target can set `bearer_token_env: NAME` to send a bearer
  token read from that environment variable. The config file never holds the token, and it is
  only ever sent over https. The `github-api` target uses this with the workflow's built-in
  `GITHUB_TOKEN`, because anonymous requests to api.github.com share a rate limit and can be
  refused with a 403.
- **Failures say why.** A failed check records the reason (for example `unexpected status 403,
  expected one of [200]` or the latency that exceeded the limit), so the incident issue is
  actionable without digging through run logs.

## Project layout

```
slo_monitor/
  checker.py   - performs the HTTP checks
  budget.py    - rolling uptime / error-budget math
  history.py   - append-only JSON history store
  issues.py    - GitHub issue creation, closing, and webhook notifications
  main.py      - orchestrates a single run
tests/         - unit tests (checker is mocked, budget math is tested directly)
config.yaml    - targets, SLO %, rolling window, warning threshold
data/history.json - check history, committed by the scheduled workflow
.github/workflows/ci.yml      - lint, tests, Bandit, pip-audit, CodeQL
.github/workflows/monitor.yml - the scheduled synthetic check itself
```

## Running it locally

```bash
python -m venv .venv
.venv/Scripts/activate   # or: source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

python -m slo_monitor.main --dry-run   # runs checks, prints results, writes/files nothing
```

To exercise issue filing locally against a real repo, set `GITHUB_TOKEN` (a token with `issues:
write` on the target repo) and pass `--repo owner/name` - but in normal operation this all comes
for free from the GitHub Actions workflow and needs no manual setup.

## Running the test suite

```bash
pip install ruff pytest bandit pip-audit
ruff check slo_monitor tests
pytest -q
bandit -r slo_monitor -ll
pip-audit -r requirements.txt
```

## Configuration

Edit `config.yaml` to point at your own services:

```yaml
targets:
  - name: my-api
    url: https://api.example.com/health
    expected_status: [200]
    max_latency_ms: 2000
    slo_target_pct: 99.9

window_days: 7            # rolling window for uptime / error-budget calculations
warn_threshold_pct: 50    # % of error budget consumed before a warning issue is filed
```

Add `bearer_token_env: MY_API_TOKEN` to a target to authenticate it with a token from the
environment (in GitHub Actions, map a repository secret to that variable in `monitor.yml`).
If the variable is not set, the check runs unauthenticated.

## License

MIT - see [LICENSE](LICENSE).
