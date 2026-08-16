"""Deterministic preflight for the external-case cold-start A/B fixture."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_CASE = ROOT / "cold-start" / "external-windows-workbuddy"


def evaluate(case_dir: Path) -> dict:
    config = json.loads((case_dir / "invariants.json").read_text(encoding="utf-8"))
    results = {}
    for mode, filename in config["modes"].items():
        content = (case_dir / filename).read_text(encoding="utf-8").lower()
        checks = []
        for invariant in config["invariants"]:
            passed = all(needle.lower() in content for needle in invariant["needles"])
            checks.append({"id": invariant["id"], "passed": passed})
        results[mode] = {
            "passed": sum(item["passed"] for item in checks),
            "total": len(checks),
            "checks": checks,
        }
    return {
        "case_id": config["case_id"],
        "method": "deterministic input-invariant preflight",
        "results": results,
        "boundary": (
            "Measures information available to a cold-start agent. Does not measure "
            "agent output quality, user satisfaction, or cross-session improvement."
        ),
    }


def render_markdown(report: dict) -> str:
    no_flg = report["results"]["no_flg"]
    flg = report["results"]["flg"]
    lines = [
        "# External Windows + WorkBuddy cold-start A/B preflight",
        "",
        f"Date: {date.today().isoformat()}",
        "",
        "## Result",
        "",
        f"- Ordinary project files: {no_flg['passed']}/{no_flg['total']} continuity invariants available",
        f"- FlowGrid Context Pack: {flg['passed']}/{flg['total']} continuity invariants available",
        "",
        "| Invariant | Ordinary files | FlowGrid pack |",
        "| --- | ---: | ---: |",
    ]
    no_flg_checks = {item["id"]: item["passed"] for item in no_flg["checks"]}
    flg_checks = {item["id"]: item["passed"] for item in flg["checks"]}
    for invariant_id in no_flg_checks:
        lines.append(
            f"| `{invariant_id}` | {'pass' if no_flg_checks[invariant_id] else 'missing'} "
            f"| {'pass' if flg_checks[invariant_id] else 'missing'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            report["boundary"],
            "",
            "The observed screenshots establish real external use and behavior inside one existing chat context. "
            "A fresh-agent output comparison is still required before claiming a continuation gain.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    report = evaluate(args.case_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "external-windows-workbuddy-cold-start.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (args.output_dir / "external-windows-workbuddy-cold-start.md").write_text(
            render_markdown(report), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
