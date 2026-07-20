"""Smoke test for editable-installed FLG CLI."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_TRANSCRIPT = REPO_ROOT / "examples" / "demo-proposal-project" / "demo_transcript.md"


def run_cmd(
    cmd: list[str],
    cwd: Path,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command and fail fast with full output."""
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        print(f"[FAIL] {' '.join(cmd)}", file=sys.stderr)
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    return result


def resolve_flg_command() -> tuple[list[str], dict[str, str] | None, str]:
    """Use the current repo build, not an unrelated global installation."""
    exe_name = "flg.exe" if sys.platform.startswith("win") else "flg"
    repo_venv_exe = REPO_ROOT / ".venv" / ("Scripts" if sys.platform.startswith("win") else "bin") / exe_name
    if repo_venv_exe.exists():
        return [str(repo_venv_exe)], None, "repository virtualenv console script"

    sibling_exe = Path(sys.executable).with_name(exe_name)
    if sibling_exe.exists():
        return [str(sibling_exe)], None, "editable-installed console script"

    pythonpath = str(REPO_ROOT / "src")
    return (
        [sys.executable, "-m", "flg.cli"],
        {"PYTHONPATH": pythonpath},
        "repository source tree",
    )


def main() -> int:
    """Run a repository-local smoke test without touching real projects."""
    if not DEMO_TRANSCRIPT.exists():
        print(f"Demo transcript not found: {DEMO_TRANSCRIPT}", file=sys.stderr)
        return 1

    flg_cmd, env_overrides, execution_mode = resolve_flg_command()
    print(f"Using FLG command ({execution_mode}): {' '.join(flg_cmd)}")

    with tempfile.TemporaryDirectory(prefix="flg-smoke-") as tmpdir:
        project_dir = Path(tmpdir) / "demo-project"
        project_dir.mkdir()

        transcript_copy = project_dir / "demo_transcript.md"
        transcript_copy.write_text(DEMO_TRANSCRIPT.read_text(encoding="utf-8"), encoding="utf-8")

        run_cmd(flg_cmd + ["version"], cwd=project_dir, env_overrides=env_overrides)
        run_cmd(
            flg_cmd + ["init", "Smoke Test Project", "--type", "proposal", "--client", "Demo Client"],
            cwd=project_dir,
            env_overrides=env_overrides,
        )
        run_cmd(flg_cmd + ["frame"], cwd=project_dir, env_overrides=env_overrides)
        run_cmd(
            flg_cmd + ["closeout", "--transcript", str(transcript_copy)],
            cwd=project_dir,
            env_overrides=env_overrides,
        )

        closeout_patch_files = sorted((project_dir / ".flg" / "patches").glob("closeout-*.patch.md"))
        if not closeout_patch_files:
            print("[FAIL] No closeout patch generated", file=sys.stderr)
            return 1
        patch_name = max(closeout_patch_files, key=lambda path: path.stat().st_mtime).name

        run_cmd(
            flg_cmd + ["review", "--patch", patch_name, "--report-only"],
            cwd=project_dir,
            env_overrides=env_overrides,
        )
        run_cmd(
            flg_cmd + ["review", "--patch", patch_name, "--autonomous"],
            cwd=project_dir,
            env_overrides=env_overrides,
        )
        run_cmd(
            flg_cmd + ["merge", "--patch", patch_name, "--yes"],
            cwd=project_dir,
            env_overrides=env_overrides,
        )

        # The deterministic demo contains shell decisions, which --accept-all
        # intentionally skips. Exercise the confirmed-evidence path explicitly
        # instead of treating skipped low-context candidates as decisions.
        decision_result = run_cmd(
            flg_cmd
            + [
                "decision",
                "add",
                "--decision",
                "Use organic launch channels",
                "--rationale",
                "The demo budget and timeline favor an auditable local-first plan",
                "--alternatives",
                "Paid ads, defer launch",
            ],
            cwd=project_dir,
            env_overrides=env_overrides,
        )
        evidence_index = project_dir / ".flg" / "context" / "evidence_index.json"
        if not evidence_index.exists():
            print(f"[FAIL] Evidence index not generated: {evidence_index}", file=sys.stderr)
            return 1
        decision_match = re.search(r"\b(D-\d+)\b", decision_result.stdout)
        if not decision_match:
            print("[FAIL] Could not determine the generated decision ID", file=sys.stderr)
            return 1
        run_cmd(flg_cmd + ["evidence", decision_match.group(1)], cwd=project_dir, env_overrides=env_overrides)

        # Capture pipeline smoke test
        run_cmd(
            flg_cmd + ["capture", "add", "-c", "Focus on content marketing", "-r", "Budget limited, need organic growth first", "-t", "judgment", "-q", "Marketing strategy", "-e", "User: we should focus on content"],
            cwd=project_dir,
            env_overrides=env_overrides,
        )
        run_cmd(flg_cmd + ["capture", "list"], cwd=project_dir, env_overrides=env_overrides)
        # Verify capture file was created
        capture_files = list((project_dir / ".flg" / "captures").glob("cap-*.md"))
        if not capture_files:
            print("[FAIL] No capture file generated", file=sys.stderr)
            return 1
        run_cmd(flg_cmd + ["capture", "show", capture_files[0].stem], cwd=project_dir, env_overrides=env_overrides)

        run_cmd(flg_cmd + ["context", "--mode", "resume", "--budget", "4000"], cwd=project_dir, env_overrides=env_overrides)
        context_pack = project_dir / ".flg" / "context" / "startup.md"
        if not context_pack.exists():
            print(f"[FAIL] Context Pack not generated: {context_pack}", file=sys.stderr)
            return 1
        run_cmd(flg_cmd + ["handoff"], cwd=project_dir, env_overrides=env_overrides)
        run_cmd(flg_cmd + ["status"], cwd=project_dir, env_overrides=env_overrides)

        generated_files = sorted(
            str(path.relative_to(project_dir))
            for path in project_dir.rglob("*")
            if path.is_file()
        )
        print("Generated files:")
        for relpath in generated_files:
            print(f"- {relpath}")

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
