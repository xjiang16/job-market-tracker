import json

import pytest

import update_readme


SAMPLE_DATA = {
    "total_postings": 10,
    "none_mentioned": 3,
    "none_mentioned_pct": 30.0,
    "skills": [
        {"label": "SQL", "count": 7, "pct": 70.0},
        {"label": "Python", "count": 1, "pct": 10.0},
    ],
}

README_TEMPLATE = """# Project

Some intro text.

<!-- AUTO-GENERATED:RESULTS:START -->
old content
<!-- AUTO-GENERATED:RESULTS:END -->

Some footer text.
"""


@pytest.mark.parametrize("n,expected", [(0, "postings"), (1, "posting"), (2, "postings")])
def test_plural(n, expected):
    assert update_readme.plural(n) == expected


def test_build_block_singular_vs_plural_rows():
    block = update_readme.build_block(SAMPLE_DATA, "January 01, 2026")

    assert "| SQL | 7 postings | 70.0% |" in block
    assert "| Python | 1 posting | 10.0% |" in block
    assert "**10 postings**" in block
    assert "January 01, 2026" in block


def test_update_readme_replaces_marked_block(tmp_path):
    data_path = tmp_path / "data.json"
    readme_path = tmp_path / "README.md"
    data_path.write_text(json.dumps(SAMPLE_DATA))
    readme_path.write_text(README_TEMPLATE)

    update_readme.update_readme(data_path=str(data_path), readme_path=str(readme_path))

    result = readme_path.read_text()
    assert "old content" not in result
    assert "Some intro text." in result
    assert "Some footer text." in result
    assert "AUTO-GENERATED:RESULTS:START" in result
    assert "| SQL | 7 postings | 70.0% |" in result


def test_update_readme_raises_when_markers_missing(tmp_path):
    data_path = tmp_path / "data.json"
    readme_path = tmp_path / "README.md"
    data_path.write_text(json.dumps(SAMPLE_DATA))
    readme_path.write_text("# Project\n\nNo markers here.\n")

    with pytest.raises(SystemExit):
        update_readme.update_readme(data_path=str(data_path), readme_path=str(readme_path))
