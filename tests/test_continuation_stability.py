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
        score = json.loads(score_path.read_text(encoding="utf-8"))
        score["model"] = "test-model"
        score["evaluator"] = "independent-scorer"
        score["scores"] = {dimension: 2 for dimension in stability.DIMENSIONS}
        score_path.write_text(json.dumps(score), encoding="utf-8")

    assert stability.summarize(output, strict=True) == 0
    report = capsys.readouterr().out
    assert "Pass^k" in report
    assert "2/2" in report
