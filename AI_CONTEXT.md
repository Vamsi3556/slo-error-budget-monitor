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
workflows (`ci.yml`, `monitor.yml`) live. `monitor.yml` runs every 30 minutes via cron and
commits `data/history.json` back to the repo automatically.

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

**Exact state as of this writing (so you can tell what's already done vs. not):**
- Local `config.yaml` in the working copy on this machine already has the canary target added
  (step 1 done, locally only).
- Step 2 (local dry-run verification) was **started but interrupted before completing** - a
  venv was being created and dependencies installed; the actual verification run had not
  produced output yet. Treat step 2 as NOT done - redo it from scratch rather than assuming a
  partial venv is usable.
- The canary target has **NOT** been pushed to GitHub yet - the live `config.yaml` on
  `main` (as of this writing, blob sha `1a0c7ae7d92be0c0586fe6cf3b35b620d9c73704`) still has only
  the original 3 targets. Steps 3-8 are all NOT done yet.
- No workflow run has been triggered for this test yet.

**Resume point:** start again from step 2 (local verification), assuming nothing beyond the
local config.yaml edit exists yet.

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

- [ ] Finish the chaos test above (steps 2-8) - this is the immediate next task.
- [ ] After that's closed out, consider whether a *permanent* lightweight canary/synthetic test
      is worth keeping (e.g. a scheduled, separate "pipeline self-test" that doesn't affect the
      real uptime numbers) - not yet decided, raise with the user before adding one.
- [ ] Longer-term backlog from the broader profile project (see `Upskill/AI_CONTEXT.md`):
      second portfolio project, real LinkedIn URL slug, optional local git clone setup.
