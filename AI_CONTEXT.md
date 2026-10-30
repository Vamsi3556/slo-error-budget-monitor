# AI Context & Decision Log — SLO & Error Budget Monitor

This file exists so any AI assistant (not just one specific tool/session) can resume work on
this repo with full context. Read it before touching anything, especially "Pending" below.

See `README.md` for the project description (problem, architecture, security practices). This
file is about history, decisions and in-flight work.

## Project summary

A synthetic-monitoring tool (Python 3.12) that checks public API targets on a GitHub Actions
cron schedule, computes rolling uptime and SRE error-budget burn, and files GitHub Issues for
incidents (immediate) and error-budget warnings (proactive). It is the first Featured Project on
`Vamsi3556`'s profile README (broader context: sibling `Upskill/AI_CONTEXT.md`).

Repo: https://github.com/Vamsi3556/slo-error-budget-monitor. CI (ruff, pytest, Bandit,
pip-audit, CodeQL) is green. `monitor.yml` runs on a schedule and commits `data/history.json`
back to the repo. GitHub only fires cron on young repos every few hours, not every 30 minutes.

## Chaos test of the incident and warning paths (2026-10-30): DONE, PASSED

The three real targets almost never fail, so the issue-filing code was only proven by mocked
tests. A temporary target `canary-guaranteed-failure` (URL on the reserved `.invalid` TLD, which
can never resolve) was added, the user triggered `monitor.yml` by hand, and the run ended red as
designed and filed, in the same run, issue #8 ("Incident: canary-guaranteed-failure check
failed") and issue #9 ("Error budget warning: canary-guaranteed-failure") with the correct
labels, target URL, error text, postmortem template and metrics. The canary was then removed and
both issues were commented on and closed as "not planned". The incident and warning paths are
now proven against the real GitHub API.

Lessons worth keeping:
- A single failure against a 99.9% SLO is thousands of percent of the error budget, so the
  incident and the warning always fire together on a first failure, and a warning will not
  clear until that failure ages out of the 7-day window (a removed target is never
  re-evaluated, so its warning must be closed by hand).
- Incident issues are never closed automatically, by design.
- No tool in this environment can dispatch a workflow run. Ask the user to click "Run workflow"
  at https://github.com/Vamsi3556/slo-error-budget-monitor/actions/workflows/monitor.yml
- Downloading Actions logs needs authentication, so run logs cannot be read from here. Use the
  public REST API for run status, issues and `data/history.json`.

## The `github-api` false positive (found by the chaos test)

Issues #6 and #7 (an incident and a warning for `github-api`, filed 2026-10-30 15:46 UTC) were
real, not part of the test. `data/history.json` showed HTTP 403 with no network error, and the
issue text only said "response did not meet expected status/latency". The service recovered by
20:38 UTC. The likely cause, NOT confirmed because logs are unreadable, is GitHub's shared
anonymous rate limit on the unauthenticated request to api.github.com.

Fix, pushed 2026-10-30 (commits `f9025cd` to `516c9ef`, CI green):
- A failed check now always records why (`unexpected status 403, expected one of [200]`, or
  `latency 5000ms exceeded the 1000ms limit`), so incident issues are actionable.
- A target can set `bearer_token_env: NAME` to send a bearer token read from that environment
  variable. It is https-only, never stored in the config, and falls back to unauthenticated if
  the variable is unset. `github-api` uses `bearer_token_env: GITHUB_TOKEN`, which
  `monitor.yml` already passes in.
- 19 tests pass. A local dry-run with a deliberately invalid token returned 401 with the new
  explanation, which proves the header is sent.

## Pending (resume here)

1. **Confirm the fix in production.** No run has happened since the fix. Ask the user to click
   "Run workflow", then check via the public API that the run is green and `github-api` has
   `success: true` in `data/history.json` (a green result with the token is the evidence). This
   also completes the last chaos-test step (a green run after removing the canary).
2. **Then close issues #6 and #7** with a comment: genuine 403 from the unauthenticated check,
   service recovered, check now authenticated and failures now explain themselves. Do not close
   them before the confirming run. Use `state_reason: not_planned` or `completed` as fits.
3. The README `monitor.yml` badge should go green after step 1.

## Decisions

- **No fabricated or backdated commit timestamps, ever.** Do not space commits out or alter
  dates. The scheduled workflow already produces genuine, organically timed history commits.
- **Commits and issues read as genuine engineering work.** Plain, descriptive commit messages.
  No AI attribution text.
- **Do not leave deliberately broken state live.** Temporary tests must be reverted and their
  issues closed with an explanation.
- **Tokens stay in the environment**, never in config or code.
- Push files with `create_or_update_file` one at a time (needs the current blob SHA). The
  multi-file `push_files` tool failed with 403 on this PAT. The PAT needs Contents, Workflows
  and Issues read/write.
- Use Python 3.12 locally (`py -3.12`), matching CI. Python 3.14 breaks Bandit and some wheel
  builds. If pip says a file in `.venv` is locked, a leftover pip process from an interrupted
  command is still running; wait for it to exit and retry.

## Backlog

- [ ] Five Dependabot PRs (#1 to #5) are open and untouched: `requests` 2.33.0 to 2.34.2, and
      bumps of `actions/checkout`, `actions/setup-python`, `github/codeql-action` and
      `stefanzweifel/git-auto-commit-action`. The Actions bumps also clear the Node 20
      deprecation warning shown on runs. Review CI on each before merging.
- [ ] `ci.yml` installs `pytest==8.3.4` inline, which `pip-audit` flagged as vulnerable
      (PYSEC-2026-1845, fixed in 9.0.3) in project #2. The security job only audits
      `requirements.txt`, so CI does not catch it. Consider a `requirements-dev.txt` like
      projects #2 and #3 use.
- [ ] Consider a retry before filing an incident, to cut false positives from one-off blips.
- [ ] Consider whether a permanent pipeline self-test (separate from real uptime numbers) is
      worth keeping. Not decided; raise with the user first.
- [ ] Broader profile backlog: see `Upskill/AI_CONTEXT.md` (LinkedIn URL slug, local git clone
      setup, and the locally built projects #2 and #3).
