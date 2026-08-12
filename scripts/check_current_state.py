#!/usr/bin/env python3
"""Fail when product files changed after the current-state document."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_DOC = Path("docs/product/current-state.md")
PRODUCT_PREFIXES = (
    "src/",
    "tests/",
    "evals/",
    "skills/",
    "scripts/",
    "docs/product/",
)


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def product_changes_after_state_update(paths: list[str]) -> list[str]:
    return sorted(
        path
        for path in paths
        if path != str(STATE_DOC) and path.startswith(PRODUCT_PREFIXES)
    )


def main() -> int:
    # A local edit is an explicit refresh in progress. CI checks the committed
    # result, so this keeps the developer loop usable without hiding drift.
    if _git("status", "--short", "--", str(STATE_DOC)):
        print("current-state: refreshed in working tree")
        return 0

    last_update = _git("log", "-1", "--format=%H", "--", str(STATE_DOC))
    if not last_update:
        print("current-state: missing committed update history")
        return 1

    changed = _git("diff", "--name-only", f"{last_update}..HEAD").splitlines()
    drift = product_changes_after_state_update(changed)
    if drift:
        print("current-state: stale; product files changed after its last update")
        for path in drift[:20]:
            print(f"- {path}")
        return 1


    print(f"current-state: current at {last_update[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
