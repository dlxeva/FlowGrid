"""Regression tests for repeatable continuation-evaluation packaging."""

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "evals" / "continuation_stability.py"
SPEC = importlib.util.spec_from_file_location("continuation_stability", SCRIPT)
assert SPEC and SPEC.loader
stability = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stability)


def test_prepare_and_summarize_repeatable_three_mode_runs(tmp_path, capsys):
    output = tmp_path / "stability"
    assert stability.prepare(output, ["campaign-proposal"], runs=2, overwrite=False) == 0
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["entries"]) == 6

    for entry in manifest["entries"]:
        score_path = output / entry["path"] / "score.json"
        response_path = score_path.parent / "response.md"
        response_path.write_text("Independent continuation response\n", encoding="utf-8")
        scorer_output = score_path.parent / "scorer-output.json"
        scorer_output.write_text(json.dumps({
            "scores": {dimension: 2 for dimension in stability.DIMENSIONS},
            "critical_failures": [],
            "notes": "Independent score",
        }), encoding="utf-8")
        score = json.loads(score_path.read_text(encoding="utf-8"))
        score_path.write_text(json.dumps(score), encoding="utf-8")
        assert stability.record_score(
            score_path,
            scorer_output,
            "independent-scorer",
            "test-model",
            "test-scorer",
        ) == 0

    assert stability.summarize(output, strict=True) == 0
    report = capsys.readouterr().out
    assert "Pass^k" in report
    assert "2/2" in report


def test_record_accepts_flat_scorer_json(tmp_path):
    output = tmp_path / "stability"
    stability.prepare(output, ["campaign-proposal"], runs=1, overwrite=False)
    target = output / "run-01" / "campaign-proposal" / "mode-a"
    (target / "response.md").write_text("A response\n", encoding="utf-8")
    scorer_output = target / "scorer-output.json"
    scorer_output.write_text(json.dumps({
        **{dimension: 1 for dimension in stability.DIMENSIONS},
        "critical_failures": [],
        "notes": "Flat schema",
    }), encoding="utf-8")
    stability.record_score(target / "score.json", scorer_output, "scorer", "continuation", "model")
    assert stability.validated_score(target / "score.json")["total"] == 7
