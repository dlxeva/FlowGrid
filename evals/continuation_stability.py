#!/usr/bin/env python3
"""Prepare and summarize repeatable three-mode continuation evaluations.

The script never calls a model. It creates sealed, hash-addressed inputs for
independent evaluators and aggregates their structured scorecards afterward.
Keeping execution outside the script prevents a benchmark from silently using
the same host context that it is supposed to evaluate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SCENARIOS_ROOT = ROOT / "scenarios"
DIMENSIONS = (
    "continuity_accuracy",
    "judgment_boundary_control",
    "rejected_alternative_suppression",
    "revision_reasoning",
    "evidence_awareness",
    "action_usefulness",
    "hallucination_resistance",
)
MODES = {
    "A": ("resume-prompt.md",),
    "B": ("resume-prompt.md", "raw-session.md"),
    "C": ("resume-prompt.md", "expected-context-pack.md"),
}


def read_inputs(scenario: str, mode: str) -> str:
    source = SCENARIOS_ROOT / scenario
    parts: list[str] = []
    for name in MODES[mode]:
        path = source / name
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}")
        parts.append(f"# {name}\n\n{path.read_text(encoding='utf-8').strip()}\n")
    return "\n".join(parts)


def score_template(scenario: str, mode: str, run: int, input_text: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "scenario": scenario,
        "mode": mode,
        "run": run,
        "input_bytes": len(input_text.encode("utf-8")),
        "input_sha256": hashlib.sha256(input_text.encode("utf-8")).hexdigest(),
        "model": None,
        "evaluator": None,
        "scorer_model": None,
        "response_sha256": None,
        "scorer_output_sha256": None,
        "scores": {dimension: None for dimension in DIMENSIONS},
        "critical_failures": [],
        "notes": "",
    }


def prepare(output: Path, scenarios: list[str], runs: int, overwrite: bool) -> int:
    if output.exists():
        if not overwrite:
            raise FileExistsError(f"Output exists: {output}; use --overwrite to replace it")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    manifest: dict[str, Any] = {"schema_version": 1, "runs": runs, "scenarios": scenarios, "entries": []}
    for run in range(1, runs + 1):
        for scenario in scenarios:
            for mode in MODES:
                input_text = read_inputs(scenario, mode)
                target = output / f"run-{run:02d}" / scenario / f"mode-{mode.lower()}"
                target.mkdir(parents=True)
                (target / "input.md").write_text(input_text, encoding="utf-8")
                score = score_template(scenario, mode, run, input_text)
                (target / "score.json").write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                (target / "response.md").write_text(
                    "# Evaluator Response\n\nPaste only the independent continuation response here.\n",
                    encoding="utf-8",
                )
                manifest["entries"].append({
                    "run": run,
                    "scenario": scenario,
                    "mode": mode,
                    "path": str(target.relative_to(output)),
                    "input_bytes": score["input_bytes"],
                    "input_sha256": score["input_sha256"],
                })
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(manifest['entries'])} sealed mode inputs under {output}")
    return 0


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_score(
    scorecard: Path,
    scorer_output: Path,
    evaluator: str,
    continuation_model: str,
    scorer_model: str,
) -> int:
    """Attach an independent scorer's JSON output to its exact evaluator response."""
    if not scorecard.exists() or not scorer_output.exists():
        raise FileNotFoundError("Scorecard and scorer output must both exist")
    response_path = scorecard.parent / "response.md"
    input_path = scorecard.parent / "input.md"
    if not response_path.exists() or not input_path.exists():
        raise FileNotFoundError("Scorecard must sit beside input.md and response.md")

    raw = json.loads(scorer_output.read_text(encoding="utf-8"))
    # Accept both the documented nested score object and a flat JSON response.
    # The latter is common when a strict evaluator still abbreviates its schema.
    values = raw.get("scores") if isinstance(raw.get("scores"), dict) else {
        dimension: raw.get(dimension) for dimension in DIMENSIONS
    }
    if not isinstance(values, dict) or any(values.get(key) not in (0, 1, 2) for key in DIMENSIONS):
        raise ValueError("Scorer output must provide every dimension as 0, 1, or 2")
    if not isinstance(raw.get("critical_failures", []), list):
        raise ValueError("critical_failures must be a list")

    score = json.loads(scorecard.read_text(encoding="utf-8"))
    score["input_sha256"] = _sha256_file(input_path)
    score["response_sha256"] = _sha256_file(response_path)
    score["scorer_output_sha256"] = _sha256_file(scorer_output)
    score["model"] = continuation_model
    score["evaluator"] = evaluator
    score["scorer_model"] = scorer_model
    score["scores"] = {dimension: values[dimension] for dimension in DIMENSIONS}
    score["critical_failures"] = raw.get("critical_failures", [])
    score["notes"] = str(raw.get("notes", ""))
    scorecard.write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded independent score: {scorecard}")
    return 0


def validated_score(path: Path) -> dict[str, Any] | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    values = data.get("scores", {})
    if not isinstance(values, dict) or any(values.get(key) not in (0, 1, 2) for key in DIMENSIONS):
        return None
    if not isinstance(data.get("critical_failures"), list):
        return None
    if not all(isinstance(data.get(field), str) and data[field].strip() for field in ("model", "evaluator", "scorer_model")):
        return None
    response_path = path.parent / "response.md"
    input_path = path.parent / "input.md"
    if not response_path.exists() or not input_path.exists():
        return None
    if data.get("input_sha256") != _sha256_file(input_path):
        return None
    if data.get("response_sha256") != _sha256_file(response_path):
        return None
    scorer_output = path.parent / "scorer-output.json"
    if not scorer_output.exists() or data.get("scorer_output_sha256") != _sha256_file(scorer_output):
        return None
    data["total"] = sum(values[key] for key in DIMENSIONS)
    return data


def summarize(output: Path, strict: bool) -> int:
    manifest_path = output / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    pair_scores: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    incomplete: list[str] = []
    for entry in manifest["entries"]:
        score_path = output / entry["path"] / "score.json"
        score = validated_score(score_path)
        if score is None:
            incomplete.append(str(score_path.relative_to(output)))
            continue
        grouped[(score["scenario"], score["mode"])].append(score)
        pair_scores[(score["scenario"], int(score["run"]))][score["mode"]] = score

    if incomplete:
        print("Incomplete scorecards:")
        for path in incomplete:
            print(f"- {path}")
        if strict:
            return 1

    print("# Continuation Stability Summary\n")
    print("| Scenario | Mode | Runs | Mean | Min | Max | Critical failures | Stable pass |")
    print("| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for (scenario, mode), scores in sorted(grouped.items()):
        totals = [score["total"] for score in scores]
        critical = sum(bool(score["critical_failures"]) for score in scores)
        stable = len(scores) == manifest["runs"] and all(total >= 10 for total in totals) and not critical
        print(
            f"| {scenario} | {mode} | {len(scores)}/{manifest['runs']} | "
            f"{sum(totals) / len(totals):.1f} | {min(totals)} | {max(totals)} | {critical} | {'Pass^k' if stable else 'Incomplete/unstable'} |"
        )

    print("\n## Mode C vs Raw History\n")
    print("| Scenario | C better | Tie | C lower | Complete pairs |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for scenario in manifest["scenarios"]:
        better = tied = lower = complete = 0
        for run in range(1, manifest["runs"] + 1):
            pair = pair_scores.get((scenario, run), {})
            if "B" not in pair or "C" not in pair:
                continue
            complete += 1
            if pair["C"]["total"] > pair["B"]["total"]:
                better += 1
            elif pair["C"]["total"] < pair["B"]["total"]:
                lower += 1
            else:
                tied += 1
        print(f"| {scenario} | {better} | {tied} | {lower} | {complete}/{manifest['runs']} |")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare", help="Create sealed repeatable mode inputs")
    prepare_parser.add_argument("--output", type=Path, required=True)
    prepare_parser.add_argument("--scenario", action="append", choices=[path.name for path in SCENARIOS_ROOT.iterdir() if path.is_dir()])
    prepare_parser.add_argument("--runs", type=int, default=5)
    prepare_parser.add_argument("--overwrite", action="store_true")
    summarize_parser = commands.add_parser("summarize", help="Aggregate completed scorecards")
    summarize_parser.add_argument("--output", type=Path, required=True)
    summarize_parser.add_argument("--strict", action="store_true")
    record_parser = commands.add_parser("record", help="Attach an independent scorer result to a response")
    record_parser.add_argument("--scorecard", type=Path, required=True)
    record_parser.add_argument("--scorer-output", type=Path, required=True)
    record_parser.add_argument("--evaluator", required=True)
    record_parser.add_argument("--continuation-model", required=True)
    record_parser.add_argument("--scorer-model", required=True)
    args = parser.parse_args()

    if args.command == "prepare":
        if args.runs < 1:
            parser.error("--runs must be at least 1")
        return prepare(args.output, args.scenario or [path.name for path in SCENARIOS_ROOT.iterdir() if path.is_dir()], args.runs, args.overwrite)
    if args.command == "record":
        return record_score(
            args.scorecard,
            args.scorer_output,
            args.evaluator,
            args.continuation_model,
            args.scorer_model,
        )
    return summarize(args.output, args.strict)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
