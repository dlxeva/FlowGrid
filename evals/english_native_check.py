#!/usr/bin/env python3
"""Deterministic English-first FlowGrid smoke gate."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "evals" / "scenarios" / "campaign-proposal" / "raw-session.md"


def run_flg(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        ["python", "-m", "flg.cli", *args],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode:
        raise RuntimeError(
            f"{label} failed with exit {result.returncode}:\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/flowgrid-english-native-eval.json"),
        help="Path for the machine-readable result.",
    )
    args = parser.parse_args()

    if not FIXTURE.is_file():
        raise FileNotFoundError(FIXTURE)

    with tempfile.TemporaryDirectory(prefix="flg-english-eval-") as temp_dir:
        project = Path(temp_dir) / "english-project"
        require_success(
            run_flg(project.parent, "init", "English Native Gate", "--language", "en", "--dir", str(project)),
            "English init",
        )

        state = json.loads((project / ".flg" / "state.json").read_text(encoding="utf-8"))
        decisions_before = (project / "DECISIONS.md").read_text(encoding="utf-8")
        raw = project.parent / "raw-session.md"
        raw.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

        closeout = run_flg(project, "closeout", "--transcript", str(raw), "--no-llm")
        require_success(closeout, "English closeout")

        archives = list((project / ".flg" / "sessions").glob("*"))
        patches = list((project / ".flg" / "patches").glob("*.md"))
        patch_text = patches[0].read_text(encoding="utf-8") if patches else ""
        decisions_after = (project / "DECISIONS.md").read_text(encoding="utf-8")

        candidate_section = patch_text.split("## 2. Candidate Decisions", 1)[-1].split("## 3. Suggested Next Actions", 1)[0]
        checks = {
            "state_language_is_en": state.get("language") == "en",
            "core_template_is_english": "## Decision Rationale" in decisions_before,
            "core_template_has_no_chinese_decision_heading": "## 决策理由" not in decisions_before,
            "external_transcript_archived": len(archives) == 1 and archives[0].read_text(encoding="utf-8") == raw.read_text(encoding="utf-8"),
            "closeout_created_patch": len(patches) == 1,
            "patch_references_archived_source": archives and str(archives[0]) in patch_text,
            "closeout_keeps_formal_ledger_unchanged": decisions_after == decisions_before,
            "revisit_question_not_promoted": "asked whether we should reconsider" not in candidate_section.lower(),
            "english_closeout_output": "## 2. Candidate Decisions" in patch_text and "## 2. 候选决策" not in patch_text,
        }

        result = {
            "passed": all(bool(value) for value in checks.values()),
            "fixture": str(FIXTURE.relative_to(ROOT)),
            "checks": checks,
            "note": "Deterministic CLI gate; model-quality scoring remains a separate manual evaluation.",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))

        return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
