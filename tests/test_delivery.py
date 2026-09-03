from datetime import datetime, timezone
import json
import os

from typer.testing import CliRunner

from flg.cli import app
from flg.core.delivery import active_delivery_issues

runner = CliRunner()


def _delivery(**overrides):
    value = {
        "code_root": "/tmp/candidate",
        "candidate_version": "0.1.28",
        "owner": "Codex",
        "as_of": "2026-07-29T00:00:00+00:00",
        "gates": ["human acceptance"],
        "evidence": ["npm verify"],
        "next_action": "run human acceptance",
    }
    value.update(overrides)
    return {"active_delivery": value}


def test_delivery_contract_is_optional_for_non_release_projects():
    assert active_delivery_issues({}) == []


def test_delivery_contract_reports_required_and_type_errors():
    issues = active_delivery_issues({"active_delivery": {"code_root": "/tmp"}})
    assert "active_delivery missing candidate_version" in issues
    assert "active_delivery missing gates" in issues

    issues = active_delivery_issues(_delivery(gates="not-a-list"))
    assert "active_delivery gates must be a list" in issues

    without_owner = _delivery()
    del without_owner["active_delivery"]["owner"]
    assert "active_delivery missing owner" in active_delivery_issues(without_owner)


def test_delivery_contract_rejects_structural_types_and_future_time():
    malformed = _delivery(
        owner=["not", "a", "string"],
        candidate_version={"value": "0.2.0"},
        next_action={"step": "ship"},
        gates=[{"gate": "human"}],
        evidence=[""],
        as_of="2099-01-01T00:00:00+00:00",
    )
    issues = active_delivery_issues(
        malformed, now=datetime(2026, 9, 2, tzinfo=timezone.utc)
    )
    assert "active_delivery owner must be a non-empty string" in issues
    assert "active_delivery candidate_version must be a non-empty string" in issues
    assert "active_delivery next_action must be a non-empty string" in issues
    assert "active_delivery gates must contain non-empty strings" in issues
    assert "active_delivery evidence must contain non-empty strings" in issues
    assert "active_delivery as_of is in the future" in issues


def test_delivery_contract_reports_staleness():
    issues = active_delivery_issues(
        _delivery(), now=datetime(2026, 8, 20, tzinfo=timezone.utc)
    )
    assert any("older than 14 days" in issue for issue in issues)


def test_delivery_contract_rejects_naive_timestamp_without_crashing():
    issues = active_delivery_issues(
        _delivery(as_of="2026-08-20T00:00:00"),
        now=datetime(2026, 8, 20, tzinfo=timezone.utc),
    )
    assert "active_delivery as_of must include a timezone" in issues


def test_delivery_cli_round_trip_and_doctor_strict(tmp_path):
    old = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Delivery Test"]).exit_code == 0
        code_root = tmp_path / "candidate"
        code_root.mkdir()
        result = runner.invoke(
            app,
            [
                "delivery", "set",
                "--code-root", str(code_root),
                "--candidate-version", "0.2.0",
                "--owner", "release-lead",
                "--gate", "human acceptance",
                "--evidence", "pytest passed",
                "--next-action", "request owner acceptance",
            ],
        )
        assert result.exit_code == 0
        state = json.loads((tmp_path / ".flg" / "state.json").read_text(encoding="utf-8"))
        assert state["active_delivery"]["candidate_version"] == "0.2.0"
        assert state["active_delivery"]["owner"] == "release-lead"

        shown = runner.invoke(app, ["delivery", "show"])
        assert shown.exit_code == 0
        assert "0.2.0" in shown.output
        assert runner.invoke(app, ["reindex"]).exit_code == 0
        healthy = runner.invoke(app, ["doctor", "--strict"])
        assert healthy.exit_code == 0
        assert "Active delivery contract" in healthy.output
        assert "OK" in healthy.output

        state["active_delivery"]["as_of"] = "2026-08-20T00:00:00"
        (tmp_path / ".flg" / "state.json").write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8"
        )
        strict = runner.invoke(app, ["doctor", "--strict"])
        assert strict.exit_code == 1
        assert "must include a timezone" in strict.output
    finally:
        os.chdir(old)
