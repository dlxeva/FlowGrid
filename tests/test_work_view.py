"""Source-backed current-work projection and block-level freshness tests."""

import json
import os

import pytest
from typer.testing import CliRunner

from flg.cli import app
from flg.commands.context import build_context_pack
from flg.core.state import load_state
from flg.core.work_view import build_work_view, inspect_work_view


runner = CliRunner()
START = "<!-- current-work:start -->"
END = "<!-- current-work:end -->"


def _project(tmp_path):
    old = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["init", "Generic Operations Project"])
    finally:
        os.chdir(old)
    assert result.exit_code == 0, result.output
    source = tmp_path / "docs" / "work-ledger.md"
    source.parent.mkdir(exist_ok=True)
    source.write_text(
        "# Work Ledger\n\nUnrelated preface.\n\n"
        f"{START}\n"
        "## Current Action\n- Interview the next operator.\n\n"
        "## Blockers\n- Waiting for a sample export.\n\n"
        "## Necessary Constraints\n- Do not treat a draft as approval.\n"
        f"{END}\n\nUnrelated appendix.\n",
        encoding="utf-8",
    )
    state_path = tmp_path / ".flg" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["work_source"] = {
        "schema_version": "1",
        "path": "docs/work-ledger.md",
        "start_marker": START,
        "end_marker": END,
    }
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return source


def _invoke(tmp_path, args):
    old = os.getcwd()
    os.chdir(tmp_path)
    try:
        return runner.invoke(app, args)
    finally:
        os.chdir(old)


def test_work_view_builds_generic_projection_and_tracks_only_marked_block(tmp_path):
    source = _project(tmp_path)
    result = _invoke(tmp_path, ["context", "--mode", "work"])
    assert result.exit_code == 0, result.output
    rendered = (tmp_path / ".flg" / "context" / "work-view.md").read_text(encoding="utf-8")
    assert "Interview the next operator." in rendered
    assert "Waiting for a sample export." in rendered
    assert "Do not treat a draft as approval." in rendered
    assert "docs/work-ledger.md#L" in rendered
    assert "sed -n" not in rendered

    state = load_state(tmp_path)
    assert inspect_work_view(tmp_path, state)["status"] == "fresh"

    source.write_text(source.read_text(encoding="utf-8") + "Outside-only note.\n", encoding="utf-8")
    assert inspect_work_view(tmp_path, state)["status"] == "fresh"

    source.write_text(
        source.read_text(encoding="utf-8").replace(
            "Interview the next operator.", "Interview two operators."
        ),
        encoding="utf-8",
    )
    status = inspect_work_view(tmp_path, state)
    assert status["status"] == "stale"
    assert status["action_status"] == "needs_recheck"
    _, manifest_meta = build_context_pack(tmp_path, mode="manifest")
    assert manifest_meta["current_action"]["status"] == "needs_recheck"
    assert manifest_meta["current_action"]["action"] is None


@pytest.mark.parametrize(
    "replacement,error",
    [
        ("", "start_marker must occur exactly once"),
        (f"{START}\n{START}", "start_marker must occur exactly once"),
        (f"{END}\n{START}", "markers are out of order"),
    ],
)
def test_work_view_rejects_missing_duplicate_or_reversed_markers(tmp_path, replacement, error):
    source = _project(tmp_path)
    text = source.read_text(encoding="utf-8")
    if replacement.startswith(END):
        text = text.replace(START, "TEMP", 1).replace(END, START, 1).replace("TEMP", END, 1)
    else:
        text = text.replace(START, replacement, 1)
    source.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        build_work_view(tmp_path, load_state(tmp_path))


def test_work_view_rejects_path_escape_and_symlink(tmp_path):
    _project(tmp_path)
    state = load_state(tmp_path)
    state["work_source"]["path"] = "../outside.md"
    with pytest.raises(ValueError, match="stay inside"):
        build_work_view(tmp_path, state)

    target = tmp_path / "docs" / "work-ledger.md"
    link = tmp_path / "docs" / "linked.md"
    link.symlink_to(target)
    state["work_source"]["path"] = "docs/linked.md"
    with pytest.raises(ValueError, match="Symlinked"):
        build_work_view(tmp_path, state)


def test_work_view_rejects_non_utf8_source_with_actionable_error(tmp_path):
    source = _project(tmp_path)
    source.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(ValueError, match="must be UTF-8 text"):
        build_work_view(tmp_path, load_state(tmp_path))


def test_work_view_small_budget_compacts_once_without_recursive_failure(tmp_path):
    source = _project(tmp_path)
    text = source.read_text(encoding="utf-8")
    long_items = "\n".join(f"- blocker-{index}-" + ("x" * 210) for index in range(6))
    text = text.replace("- Waiting for a sample export.", long_items)
    source.write_text(text, encoding="utf-8")
    content, metadata = build_work_view(tmp_path, load_state(tmp_path), budget=1)
    assert len(content) <= 1200
    assert metadata["truncated"] is True


def test_doctor_strict_reports_unbuilt_and_stale_work_view(tmp_path):
    source = _project(tmp_path)
    unbuilt = _invoke(tmp_path, ["doctor", "--strict"])
    assert unbuilt.exit_code == 1
    assert "source-backed work view is unbuilt" in unbuilt.output

    built = _invoke(tmp_path, ["context", "--mode", "work"])
    assert built.exit_code == 0
    fresh = _invoke(tmp_path, ["doctor", "--strict"])
    assert "source-backed work view is stale" not in fresh.output

    source.write_text(
        source.read_text(encoding="utf-8").replace(
            "Waiting for a sample export.", "Waiting for two exports."
        ),
        encoding="utf-8",
    )
    stale = _invoke(tmp_path, ["doctor", "--strict"])
    assert stale.exit_code == 1
    assert "source-backed work view is stale" in stale.output
