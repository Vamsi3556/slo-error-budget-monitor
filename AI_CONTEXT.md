# AI Context & Decision Log — SLO & Error Budget Monitor

This file exists so any AI assistant (not just one specific tool/session) can resume work on
this repo with full context. If you are an AI picking this up, read this whole file before
touching anything - especially the "IN PROGRESS" section below, which describes an unfinished
task with exact next steps.

See `README.md` for the full project description (problem statement, architecture, security
practices). This file is about history, decisions, and in-flight work - not a duplicate of the
README.

## Project summary

A synthetic-monitoring tool (Python) that checks public API targets on a GitHub Actions cron
schedule, computes rolling uptime / SRE error-budget burn, and auto-files GitHub Issues for
incidents (immediate) and error-budget warnings (proactive). Built as a real "Featured Project"
for `Vamsi3556`'s GitHub profile README (see the sibling `Upskill/` workspace folder and its own
`AI_CONTEXT.md` for that broader context - this repo is one project referenced from there).

Status as of last session: fully built, tested locally (ruff/pytest/Bandit/pip-audit all clean),
pushed to https://github.com/Vamsi3556/slo-error-budget-monitor, CI green on GitHub, both
workflows (`ci.yml`, `monitor.yml`) live. `monitor.yml` runs via cron and commits
`data/history.json` back to the repo automatically.

## IN PROGRESS — chaos test of the incident/warning pipeline

**Why:** the three real targets (GitHub API, Open-Meteo, JSONPlaceholder) are all highly
reliable public services. That means the incident-filing and error-budget-warning code paths
are only verified by *mocked* unit tests - never proven against the real GitHub REST API in
production. The user asked specifically whether any of the monitored targets could break to
give us "room for testing," which led to this plan.

**The plan:**
1. Add a temporary 4th target to `config.yaml` that is *guaranteed* to fail deterministically:
   a URL on the reserved `.invalid` TLD (RFC 2606 - permanently unresolvable, no third-party
   dependency, no flakiness). Name: `canary-guaranteed-failure`, url:
   `https://canary-guaranteed-failure.invalid/health`.
2. Verify locally first (`python -m slo_monitor.main --dry-run`) that the canary target fails
   via a real `requests.ConnectionError` (DNS resolution failure) while the other 3 targets
   still succeed normally - i.e. one bad target shouldn't break the others.
3. Push the updated `config.yaml` to GitHub.
4. Trigger the `monitor.yml` workflow. There is no MCP tool available in this environment that
   can dispatch a GitHub Actions workflow run directly (checked the available GitHub MCP
   toolset - no `run_workflow`/`dispatch` tool exists). Options: (a) ask the user to click
   "Run workflow" on https://github.com/Vamsi3556/slo-error-budget-monitor/actions/workflows/monitor.yml
   (manual `workflow_dispatch` is already enabled in the workflow), or (b) just wait - the cron
   fires every 30 minutes regardless.
5. After the run completes, verify via the public GitHub REST API (no auth needed for a public
   repo - `https://api.github.com/repos/Vamsi3556/slo-error-budget-monitor/...` works fine with
   plain `web_fetch`, as already proven earlier in this project) that:
   - The workflow run shows `conclusion: failure` (expected - the workflow is designed to fail
     its own run when an incident is detected; this is intentional, not a bug)
   - An issue titled "Incident: canary-guaranteed-failure check failed" was created with the
     blameless-postmortem template
   - An issue titled "Error budget warning: canary-guaranteed-failure" was ALSO created in the
     same run - a single failure against a 99.9% SLO target instantly exceeds a 0.1% error
     budget, so both the incident path AND the warning path fire together on first failure.
     (Confirmed via the math in `budget.py` / `tests/test_budget.py` - one failure in a window
     of size 1 gives 0% uptime, which is nowhere close to 99.9%.)
6. Once both issues are confirmed to exist with correct content, revert `config.yaml` to remove
   the canary target (back to exactly the 3 original targets) and push that revert.
7. **Close both test issues manually** with a comment explaining they were a deliberate chaos
   test of the alerting pipeline, now confirmed working - do not leave them open indefinitely.
   (Important: once the canary target is removed from `config.yaml`, the code never re-evaluates
   it again, so the open warning issue would never auto-close itself - it must be closed by hand.)
8. Confirm the next scheduled run (or another manual trigger) goes back to
   `conclusion: success` and the `monitor.yml` badge on the README goes green again.

**Side effect while this is in progress:** the `monitor.yml` status badge in `README.md` will
show red/failing for as long as the canary target is active. This is expected and temporary -
don't "fix" it by changing the badge or the workflow; just finish the test and revert the config.

**CURRENT STATE (updated 2026-10-30):**
- Step 1 done. Step 2 done: the local dry-run showed the canary failing with a real DNS error
  (`NameResolutionError`), the other 3 targets OK, and exit code 1.
- Step 3 done: the canary config was pushed to `main` (commit `e0ea2e1`).
- Step 4 done: the user started a manual run of `monitor.yml` from the Actions tab.
- Step 5 done and PASSED: the run ended red as designed and filed issue #8 ("Incident:
  canary-guaranteed-failure check failed") and issue #9 ("Error budget warning:
  canary-guaranteed-failure") in the same run, with the correct labels, target URL, DNS error
  text, postmortem template and metrics (0% uptime over 1 check). The incident and warning
  paths are now proven against the real GitHub API.
- Step 6 done: the canary was removed from `config.yaml` (commit `f314944`). The file is
  byte-identical to the original 3-target version (same blob SHA `1a0c7ae`).
- **Step 7 PENDING: issues #8 and #9 are still OPEN.** The PAT in `mcp.json` lacks the "Issues:
  Read and write" permission, so commenting and closing fail with HTTP 403. Either the user adds
  that permission, or closes both by hand with a note that they were a deliberate chaos test.
- Step 8 pending: confirm the next run is green after the revert.
- **Unrelated finding (real, not part of the test):** issues #6 and #7 (an incident and a
  warning for `github-api`, filed 2026-10-30 15:46 UTC) are genuine. `data/history.json` shows
  HTTP 403 with no network error. Most likely cause, NOT confirmed: the unauthenticated check of
  api.github.com hit GitHub's anonymous rate limit, which is shared by runners on the same IP.
  That would be a false positive caused by my target choice. The checker does not record the
  response body, and a wrong status is reported only as "response did not meet expected
  status/latency", which made it hard to diagnose.
- **Resume point:** step 7, then step 8, then discuss the `github-api` false positive.

## Key decisions and rationale (carried over / established in this repo)

- **No fabricated/backdated commit timestamps, ever.** This came up in the broader README
  project (see `Upskill/AI_CONTEXT.md`) and applies here too: don't space out commit times to
  misrepresent when work happened, at any granularity (hours/days/weeks). The scheduled
  `monitor.yml` workflow already produces genuine, organically-timed commits on its own.
- **Commits/issues should read as genuine engineering work, not bot-generated filler.** Plain,
  descriptive commit messages; issue bodies use the real blameless-postmortem template, not
  placeholder text.
- **Don't leave deliberately-broken state live without closing the loop.** The canary test above
  is a controlled, temporary chaos experiment - it must be reverted and the resulting test issues
  closed with an explanation, not left as permanent "failing" state on a portfolio repo.
- **No tool in this environment can directly dispatch a GitHub Actions workflow run.** If this
  capability is needed again, either ask the user to click "Run workflow" in the GitHub UI, or
  wait for the existing cron schedule.

## Open items / next actions (backlog)

- [ ] Finish the chaos test: close issues #8 and #9 (step 7) and confirm a green run (step 8).
- [ ] Decide how to fix the `github-api` false positive (issues #6 and #7). Options: point the
      check at a target without the anonymous rate limit (for example the githubstatus.com API),
      or send the workflow's `GITHUB_TOKEN` with that one request. Also make a wrong status
      say so in the issue (for example "unexpected status 403, expected [200]") by filling the
      `error` field. Raise with the user before changing targets.
- [ ] Five Dependabot PRs (#1 to #5) are open and untouched, including bumps of the GitHub
      Actions versions (which also clears the Node 20 deprecation warning on runs).
- [ ] After that's closed out, consider whether a *permanent* lightweight canary/synthetic test
      is worth keeping (e.g. a scheduled, separate "pipeline self-test" that doesn't affect the
      real uptime numbers) - not yet decided, raise with the user before adding one.
- [ ] Longer-term backlog from the broader profile project (see `Upskill/AI_CONTEXT.md`):
      second portfolio project, real LinkedIn URL slug, optional local git clone setup.
