"""
Regenerates the "What the data shows" section in README.md from docs/data.json,
replacing everything between the AUTO-GENERATED marker comments.

Run this after export_results.py (which writes docs/data.json).
"""

import json
import re
from datetime import date

MARKER_PATTERN = re.compile(
    r"<!-- AUTO-GENERATED:RESULTS:START -->.*?<!-- AUTO-GENERATED:RESULTS:END -->",
    re.DOTALL,
)


def plural(n):
    return "posting" if n == 1 else "postings"


def build_block(data, today):
    skills = data["skills"]
    total = data["total_postings"]
    none_ct = data["none_mentioned"]
    none_pct = data["none_mentioned_pct"]
    top = skills[0]
    tool_count = len(skills)

    table_rows = "\n".join(
        f"| {s['label']} | {s['count']} {plural(s['count'])} | {s['pct']}% |"
        for s in skills
    )

    return f"""<!-- AUTO-GENERATED:RESULTS:START -->
## What the data shows

Current snapshot (updated {today}): **{total} postings** after deduplication.

| Tool | Mentioned in | Share |
|------|-------------:|------:|
{table_rows}

The most notable finding is that **{none_pct}% of postings ({none_ct} out of {total}) mention none of the {tool_count} tracked tools explicitly**.

Instead, most postings describe responsibilities in general terms such as *"build data pipelines"* or *"own the data platform"* rather than naming a specific technology stack. Of the {tool_count} tracked tools, **{top['label']}** appears most often in this sample ({top['pct']}%).

This is a growing sample, refreshed automatically once a day via [GitHub Actions](https://github.com/xjiang16/job-market-tracker/actions/workflows/refresh-results.yml). See the [live results page](https://xjiang16.github.io/job-market-tracker/) for the current interactive chart, or the roadmap below for what's next.
<!-- AUTO-GENERATED:RESULTS:END -->"""


def update_readme(data_path="docs/data.json", readme_path="README.md"):
    with open(data_path) as f:
        data = json.load(f)

    with open(readme_path) as f:
        readme = f.read()

    if not MARKER_PATTERN.search(readme):
        raise SystemExit(
            "Markers not found in README.md — paste the marked block in manually once "
            "before this script can find where to update."
        )

    block = build_block(data, date.today().strftime("%B %d, %Y"))
    readme = MARKER_PATTERN.sub(block, readme)

    with open(readme_path, "w") as f:
        f.write(readme)

    print("README.md results section updated.")


if __name__ == "__main__":  # pragma: no cover
    update_readme()
