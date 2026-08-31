# CLAUDE.md

Conventions and gotchas for working on this repo, learned the hard way. Keep this
current, not exhaustive — delete anything that stops being true.

## What this is

A data pipeline: Adzuna API → Snowflake (raw) → dbt (staging + skill extraction) →
`export_results.py` → `docs/data.json` / `docs/data_history.json` → GitHub Pages
dashboard. Runs daily via `.github/workflows/refresh-results.yml`.

## Branch protection and the daily bot

`main` requires 1 review approval before merge, and GitHub never lets a PR's author
approve their own PR — not even a bot with admin-level tokens. The daily workflow
works around this by opening a PR and approving it with a **second identity**
(`APPROVER_TOKEN`, a separate PAT) before merging. Don't "simplify" this back to a
direct `git push` to `main` — that reverts real branch protection (this exact
regression showed up in PR #7, which forked before this flow existed).

## Misha (wardm5) works from a fork, not a branch

His PRs come from `wardm5/job-market-tracker`, a fork — not a branch on this repo.
We (and Claude) don't have push access there. If one of his PRs goes stale/conflicts
with `main`, don't try to rebase-and-force-push it — that's not ours to rewrite.
Instead, isolate what's actually new in his PR (diff it against its real fork point,
not against current `main`, or the diff is mostly noise from everything that merged
in the meantime), recreate just the good content in a fresh PR on this repo, and
comment on the original explaining why, before asking him to close it.

## `gh` CLI heredoc quoting bug

`gh pr create --body "$(cat <<'EOF' ... EOF)"` and `gh pr comment ... --body "$(...)"`
reliably fail with `unexpected EOF while looking for matching` in this environment.
Always write the body to a scratch file and use `--body-file` instead.

## Testing

```bash
pip install -r requirements-dev.txt -r requirements.txt
pytest -v
```
`requirements-dev.txt` includes `duckdb`, needed for `tests/test_demo.py` — a bare
`pytest.ini`-driven run without it fails on collection, not on a real test failure.
Coverage is enforced at 100% (`--cov-fail-under=100` in `pytest.ini`, scoped via
`.coveragerc`) — new logic without a test fails CI outright, not just a warning.

**When mocking a Snowflake cursor result**, use the real Python type Snowflake
returns, not whatever's convenient to type. `NUMBER(x,0)` columns (e.g. `COUNT(*)`
sums) come back as `int`; `NUMBER(x,1+)` columns (rounded percentages, etc.) come
back as `decimal.Decimal`, not `float`. A test using a `float` literal for the
latter won't catch a `json.dump()` crash — this shipped and broke production once
(see `export_results.py`'s `build_history()` and its Decimal regression test).

## Scheduled workflow timing

`.github/workflows/refresh-results.yml`'s cron is intentionally **not** on the top
of the hour (currently `17 7 * * *`). GitHub's own docs note scheduled workflows
can be delayed or dropped under high load, which peaks at `:00`. Confirmed
empirically on 2026-08-27/28: one run landed ~11h late, the next didn't fire at
all. Don't move it back to `:00`.

## Local frontend preview

`docs/index.html` is a static file that `fetch()`es `data.json` / `data_history.json`.
Opening it directly (`file://`) silently breaks — CORS blocks `fetch()` from a
`file://` origin. Serve it: `cd docs && python3 -m http.server 8000`.

## Misc

- `.DS_Store` is (unfortunately) tracked in this repo. It'll show as modified in
  `git status` from normal Finder use — never include it when staging/committing.
- PR convention: small, single-purpose PRs; request `wardm5` as reviewer
  (`gh pr edit <n> --add-reviewer wardm5`) since he's the active collaborator.
