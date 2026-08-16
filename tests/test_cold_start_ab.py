import json
from pathlib import Path

from evals.cold_start_ab import DEFAULT_CASE, evaluate, render_markdown


def test_external_case_cold_start_fixture_is_reproducible():
    report = evaluate(DEFAULT_CASE)
    assert report["results"]["no_flg"]["passed"] == 1
    assert report["results"]["flg"]["passed"] == 6
    assert "Does not measure agent output quality" in report["boundary"]
    rendered = render_markdown(report)
    assert "Ordinary project files: 1/6" in rendered
    assert "FlowGrid Context Pack: 6/6" in rendered
    assert "fresh-agent output comparison is still required" in rendered


def test_external_case_fixture_uses_relative_local_sources():
    for path in DEFAULT_CASE.iterdir():
        assert path.is_file()
        assert not Path(path.name).is_absolute()


def test_recorded_external_case_result_matches_the_runner():
    recorded = json.loads(
        (DEFAULT_CASE.parents[1] / "results" / "external-windows-workbuddy-cold-start.json").read_text(
            encoding="utf-8"
        )
    )
    assert recorded == evaluate(DEFAULT_CASE)
