#!/usr/bin/env python3
"""Prepare extraction-only artifacts for the Context Pack evaluation harness.

This script intentionally starts from a blank FLG project. Its output measures
closeout extraction and patch-to-context plumbing, not full resume quality.
Use each scenario's expected-context-pack.md as the oracle for the separate
three-mode continuation evaluation.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_ROOT = REPO_ROOT / "evals" / "scenarios"
SCENARIOS = ["campaign-proposal", "client-solution-proposal", "operations-mechanism-design"]


def resolve_flg_command() -> tuple[list[str], dict[str, str]]:
    env = os.environ.copy()
    sibling = Path(sys.executable).with_name("flg")
    if sibling.exists():
        return [str(sibling)], env
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return [sys.executable, "-m", "flg.cli"], env


def run(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True, capture_output=True, text=True)


def prepare_scenario(scenario: str, output_dir: Path) -> dict[str, object]:
    source_dir = SCENARIOS_ROOT / scenario
    flg_cmd, env = resolve_flg_command()
    with tempfile.TemporaryDirectory(prefix=f"flg-eval-{scenario}-") as temp:
        project = Path(temp) / "project"
        project.mkdir()
        raw = project / "raw-session.md"
        shutil.copy2(source_dir / "raw-session.md", raw)

        run(flg_cmd + ["init", f"Eval {scenario}"], project, env)
        run(flg_cmd + ["closeout", "--transcript", str(raw), "--no-llm"], project, env)
        patches = sorted((project / ".flg" / "patches").glob("closeout-*.patch.md"))
        if patches:
            run(flg_cmd + ["review", "--patch", patches[-1].name, "--accept-all"], project, env)
        run(flg_cmd + ["context", "--mode", "resume", "--budget", "4000"], project, env)

        output_path = output_dir / f"{scenario}-context-pack.md"
        shutil.copy2(project / ".flg" / "context" / "startup.md", output_path)
        return {
            "scenario": scenario,
            "evaluation_scope": "extraction_only",
            "context_pack": str(output_path),
            "characters": len(output_path.read_text(encoding="utf-8")),
            "resume_prompt": str(source_dir / "resume-prompt.md"),
            "raw_session": str(source_dir / "raw-session.md"),
            "golden_decisions": str(source_dir / "golden-decisions.md"),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=SCENARIOS, action="append")
    parser.add_argument("--output", type=Path, default=Path("/tmp/flowgrid-context-eval"))
    args = parser.parse_args()
    scenarios = args.scenario or SCENARIOS
    args.output.mkdir(parents=True, exist_ok=True)
    results = [prepare_scenario(scenario, args.output) for scenario in scenarios]
    (args.output / "README.md").write_text(
        """# Context Evaluation Artifacts

These generated packs are **extraction-only** artifacts. The harness starts
from a blank FLG project, so they do not measure full resume quality or prove
that Context Pack is better than raw history.

For the continuation comparison, use each scenario's
`expected-context-pack.md` as the oracle and compare no-state, raw history,
and FlowGrid Context Pack responses in isolated sessions.
""",
        encoding="utf-8",
    )
    print(json.dumps({"scenarios": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
