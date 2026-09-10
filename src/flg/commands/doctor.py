"""Cross-file project consistency diagnostics and evidence reindexing."""

import json
from pathlib import Path
import subprocess

import typer
from rich.console import Console
from rich.table import Table

from ..core.evidence import rebuild_evidence_index, save_evidence_index, validate_project
from ..core.delivery import active_delivery_issues
from ..core.files import is_flg_project
from ..core.relations import validate_decision_relations
from ..core.state import load_state
from ..core.wiki import wiki_health_issues
from ..core.work_view import work_view_health_issues

console = Console()


def _git_value(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _runtime_identity(root: Path) -> dict | None:
    """Inspect the mapped code checkout without affecting unmapped projects."""
    map_path = root / ".flg" / "repo-map.json"
    if not map_path.exists():
        return None

    try:
        mapping = json.loads(map_path.read_text(encoding="utf-8"))
        repo = Path(mapping["code_repo"]).expanduser().resolve()
        branch = _git_value(repo, "branch", "--show-current") or "(detached)"
        head = _git_value(repo, "rev-parse", "HEAD")
        dirty_lines = _git_value(repo, "status", "--short").splitlines()
    except (
        OSError,
        KeyError,
        json.JSONDecodeError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as exc:
        return {
            "configured": True,
            "error": str(exc),
            "issues": ["mapped runtime could not be inspected"],
        }

    expected_branch = mapping.get("branch")
    expected_head = mapping.get("remote_commit")
    issues = []
    if expected_branch and branch != expected_branch:
        issues.append(
            f"branch mismatch: expected {expected_branch}, found {branch}"
        )
    if expected_head and head != expected_head:
        issues.append(f"HEAD mismatch: expected {expected_head}, found {head}")

    return {
        "configured": True,
        "repo": str(repo),
        "branch": branch,
        "expected_branch": expected_branch,
        "head": head,
        "expected_head": expected_head,
        "dirty_count": len(dirty_lines),
        "issues": issues,
    }


def doctor(
    project_path: str = typer.Argument(".", help="Path to a FLG project"),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Exit with code 1 when issues are found",
    ),
) -> None:
    """Check consistency between the formal ledger, state, and derived indexes."""
    root = Path(project_path).resolve()
    if not root.exists() or not is_flg_project(root):
        console.print(f"[red]Not a FLG project: {root}[/red]")
        raise typer.Exit(1)

    report = validate_project(root)
    decisions_path = root / "DECISIONS.md"
    decisions_content = (
        decisions_path.read_text(encoding="utf-8")
        if decisions_path.exists()
        else ""
    )
    relation_issues = validate_decision_relations(decisions_content)
    identity = _runtime_identity(root)
    identity_issues = identity.get("issues", []) if identity else []
    state = load_state(root) or {}
    delivery_issues = active_delivery_issues(state)
    wiki_issues = wiki_health_issues(root)
    work_view_issues = work_view_health_issues(root, state)
    table = Table(title=f"FlowGrid Doctor: {root}")
    table.add_column("Check", style="cyan")
    table.add_column("Result", style="bold")
    overall_ok = (
        report["status"] == "ok"
        and not relation_issues
        and not identity_issues
        and not delivery_issues
        and not wiki_issues
        and not work_view_issues
    )
    table.add_row("Overall", "OK" if overall_ok else "Needs attention")
    table.add_row("Formal decisions", str(report["decision_count"]))
    table.add_row(
        "Unparsed decision entries",
        str(len(report["unparsed_decisions"])),
    )
    table.add_row("Indexed decisions", str(report["index_count"]))
    table.add_row(
        "Missing index entries",
        str(len(report["missing_index"])),
    )
    table.add_row(
        "Orphan index entries",
        str(len(report["orphan_index"])),
    )
    table.add_row(
        "Broken evidence refs",
        str(len(report["broken_references"])),
    )
    table.add_row(
        "Missing source episodes",
        str(len(report["missing_source_episodes"])),
    )
    table.add_row(
        "Broken source episodes",
        str(len(report["broken_source_episodes"])),
    )
    table.add_row(
        "Broken decision relations",
        str(len(relation_issues)),
    )
    table.add_row("Legacy paths", str(len(report["legacy_paths"])))
    table.add_row(
        "Closed patches still pending",
        str(len(report["merged_pending"])),
    )
    table.add_row(
        "Active delivery contract",
        "OK" if not delivery_issues else f"Needs attention ({len(delivery_issues)})",
    )
    table.add_row(
        "Wiki continuity",
        "not configured" if not (root / ".flg" / "wiki.json").exists()
        else ("OK" if not wiki_issues else f"Needs attention ({len(wiki_issues)})"),
    )
    table.add_row(
        "Source-backed work view",
        "not configured" if "work_source" not in state
        else ("OK" if not work_view_issues else f"Needs attention ({len(work_view_issues)})"),
    )
    if identity is None:
        table.add_row("Runtime identity", "not configured (no repo-map)")
    elif identity.get("error"):
        table.add_row(
            "Runtime identity",
            f"unavailable: {identity['error']}",
        )
    else:
        branch_result = identity["branch"]
        if identity.get("expected_branch"):
            branch_result += f" (expected {identity['expected_branch']})"
        head_result = identity["head"][:12]
        if identity.get("expected_head"):
            head_result += f" (expected {identity['expected_head'][:12]})"
        dirty_count = identity["dirty_count"]
        table.add_row("Runtime repo", identity["repo"])
        table.add_row("Runtime branch", branch_result)
        table.add_row("Runtime HEAD", head_result)
        table.add_row(
            "Runtime worktree",
            "clean" if not dirty_count else f"dirty ({dirty_count} change(s))",
        )
    console.print(table)

    for key in (
        "missing_index",
        "orphan_index",
        "broken_references",
        "missing_source_episodes",
        "broken_source_episodes",
        "legacy_paths",
        "merged_pending",
        "unparsed_decisions",
    ):
        values = report[key]
        if values:
            console.print(f"[yellow]{key}:[/yellow]")
            for value in values[:20]:
                console.print(f"  - {value}")

    if relation_issues:
        console.print("[yellow]decision_relations:[/yellow]")
        for issue in relation_issues[:20]:
            console.print(f"  - {issue}")

    if identity_issues:
        console.print("[yellow]runtime_identity:[/yellow]")
        for issue in identity_issues:
            console.print(f"  - {issue}")

    if delivery_issues:
        console.print("[yellow]active_delivery:[/yellow]")
        for issue in delivery_issues:
            console.print(f"  - {issue}")

    if wiki_issues:
        console.print("[yellow]wiki_continuity:[/yellow]")
        for issue in wiki_issues:
            console.print(f"  - {issue}")

    if work_view_issues:
        console.print("[yellow]source_backed_work_view:[/yellow]")
        for issue in work_view_issues:
            console.print(f"  - {issue}")

    if strict and not overall_ok:
        raise typer.Exit(1)


def reindex(
    project_path: str = typer.Argument(".", help="Path to a FLG project"),
) -> None:
    """Rebuild evidence_index.json from DECISIONS.md."""
    root = Path(project_path).resolve()
    if not root.exists() or not is_flg_project(root):
        console.print(f"[red]Not a FLG project: {root}[/red]")
        raise typer.Exit(1)

    index = rebuild_evidence_index(root)
    path = save_evidence_index(root, index)
    console.print(f"[green]Rebuilt evidence index:[/green] {path}")
    console.print(
        f"Indexed {len(index['items'])} formal decision(s) from DECISIONS.md."
    )
    source_count = sum(
        len(item.get("source_episodes", []))
        for item in index["items"].values()
    )
    console.print(f"Rebuilt {source_count} source episode(s).")
