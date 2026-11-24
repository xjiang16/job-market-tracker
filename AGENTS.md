# AGENTS.md

Conventions and gotchas for working on this repo, learned the hard way. Keep this
current, not exhaustive — delete anything that stops being true.

## What this is

A data pipeline: Adzuna API → DuckDB (raw) → dbt (staging + skill extraction) →
`export_results.py` → `docs/data.json` / `docs/data_history.json` → GitHub Pages
dashboard. Runs daily via `.github/workflows/refresh-results.yml`.

## Where the data lives: `data/warehouse/*.csv`, not a database

The warehouse was Snowflake until its free trial expired (Nov 2026, PR #152); it's now
DuckDB, which is free but is just a local file — and GitHub Actions runners are fresh
every run. So the tables that can't be rebuilt (`RAW.job_postings`, and the daily
`ANALYTICS.skill_trends` snapshots) are persisted as sorted CSVs in `data/warehouse/`,
committed by the daily bot PR. Each run: `load_to_duckdb.py` rebuilds a fresh
`warehouse/JOB_MARKET_TRACKER.duckdb` from them, dbt runs, `export_results.py` saves
them back (see `warehouse.py`).

- **Those CSVs are the only copy of the data.** Never delete, regenerate, or
  hand-edit them casually; `skill_trends` history in particular can't be recomputed.
- **Don't commit the `.duckdb` file instead** — a binary rewritten daily bloats git
  history by megabytes a day; append-only CSV stores as small deltas. The root
  `/warehouse/` ignore rule is anchored on purpose so it can't match `data/warehouse/`.
- The file must be named `JOB_MARKET_TRACKER.duckdb`: dbt-duckdb names its catalog
  after the file, which matches `database:` in `models/sources.yml`.

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
`requirements-dev.txt` includes `dbt-duckdb`, needed for `tests/test_demo.py`, which
shells out to the `dbt` executable — run `pytest` with the virtualenv **activated**
(`source .venv/bin/activate`), or those tests fail with `FileNotFoundError: 'dbt'`
rather than a real failure. Coverage is enforced at 100% (`--cov-fail-under=100` in
`pytest.ini`, scoped via `.coveragerc`) — new logic without a test fails CI outright,
not just a warning.

**Test database code against a real DuckDB, not mocks.** DuckDB runs in-process, so
`duckdb.connect()` (in-memory) or a file under `tmp_path` costs nothing and returns
the real types the code will see. Hand-typed mock results are how a type mismatch
once shipped: mocked Snowflake rows used a `float` where Snowflake really returned
`decimal.Decimal`, and `json.dump()` crashed in production (see `build_history()`
and its Decimal regression test in `tests/test_export_results.py`).

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

## PR description style

Write PR descriptions as proper markdown, not a wall of prose:

- A `## Summary` section with a few bullet points on what changed and why.
- A `## Test plan` section listing how it was verified (commands run, tests added,
  manual checks) — a checklist (`- [ ]` / `- [x]`) if there are multiple steps.
- Reference issues/PRs with `#123` so GitHub auto-links them.
- Backtick any file path, command, or identifier mentioned inline.

This came out of review feedback on PR #86 (Misha: "add more info on how agents
should style PRs with nice markdown"). Treat it as a starting point, not a fixed
spec — if norms here shift, update this section rather than letting it go stale.

## Misc

- `.DS_Store` is (unfortunately) tracked in this repo. It'll show as modified in
  `git status` from normal Finder use — never include it when staging/committing.
- PR convention: small, single-purpose PRs; request `wardm5` as reviewer
  (`gh pr edit <n> --add-reviewer wardm5`) since he's the active collaborator.
