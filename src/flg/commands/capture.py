"""flg capture commands - Real-time judgment candidate capture."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.files import is_flg_project

console = Console()
CAPTURES_DIR = ".flg/captures"

YAML_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _captures_root(root: Path) -> Path:
    return root / CAPTURES_DIR


def _ensure_captures_dir(root: Path) -> Path:
    d = _captures_root(root)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _generate_id() -> str:
    now = datetime.now()
    ts = now.strftime("%Y%m%d-%H%M%S")
    rand = hashlib.md5(str(now.timestamp()).encode()).hexdigest()[:6]
    return f"cap-{ts}-{rand}"


def _valid_types() -> list[str]:
    return ["judgment", "decision", "principle"]


def capture_add(
    claim: str = typer.Option(
        ..., "-c", "--claim", help="判断主张（必填）"
    ),
    rationale: str = typer.Option(
        ..., "-r", "--rationale", help="判断理由（必填）"
    ),
    type_: Optional[str] = typer.Option(
        "judgment", "-t", "--type", help="判断类型: judgment | decision | principle"
    ),
    question: Optional[str] = typer.Option(
        None, "-q", "--question", help="这条判断回答什么问题"
    ),
    evidence: Optional[str] = typer.Option(
        None, "-e", "--evidence", help="用户原话引用"
    ),
    alternatives: Optional[str] = typer.Option(
        None, "-a", "--alternatives", help="备选方案（逗号分隔）"
    ),
    risks: Optional[str] = typer.Option(
        None, "-k", "--risks", help="风险判断"
    ),
    confidence: str = typer.Option(
        "inferred", "--confidence", help="inferred | confirmed"
    ),
    source: str = typer.Option(
        "user_text", "--source", help="user_text | agent_summary"
    ),
) -> None:
    """捕获一条候选判断（Judgment Candidate）."""
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    if type_ not in _valid_types():
        console.print(f"[red]Invalid type: {type_}. Must be one of: {', '.join(_valid_types())}[/red]")
        raise typer.Exit(1)

    if confidence not in ("inferred", "confirmed"):
        console.print("[red]Confidence must be 'inferred' or 'confirmed'.[/red]")
        raise typer.Exit(1)

    if source not in ("user_text", "agent_summary"):
        console.print("[red]Source must be 'user_text' or 'agent_summary'.[/red]")
        raise typer.Exit(1)

    # Auto-calculate review_required
    review_required = (type_ == "judgment" and confidence == "inferred")

    # Build frontmatter
    now = datetime.now().isoformat(timespec="seconds")
    capture_id = _generate_id()

    alt_list = None
    if alternatives:
        alt_list = [a.strip() for a in alternatives.split(",") if a.strip()]

    frontmatter = {
        "id": capture_id,
        "created_at": now,
        "type": type_,
        "status": "pending_review",
        "confidence": confidence,
        "source": source,
        "review_required": review_required,
        "question": question or "(not specified)",
        "claim": claim,
        "rationale": rationale,
    }
    if alt_list:
        frontmatter["alternatives"] = alt_list
    if risks:
        frontmatter["risks"] = risks
    if evidence:
        frontmatter["raw_evidence"] = evidence

    yaml_block = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False, sort_keys=False)

    content = f"---\n{yaml_block}---\n\n# {capture_id}\n\n**Claim:** {claim}\n\n**Rationale:** {rationale}\n"

    _ensure_captures_dir(root)
    filepath = _captures_root(root) / f"{capture_id}.md"
    filepath.write_text(content, encoding="utf-8")

    console.print()
    console.print(f"[green]✓ Capture recorded:[/green] [bold cyan]{capture_id}[/bold cyan]")
    console.print(f"  Type: {type_}  |  Status: pending_review  |  Confidence: {confidence}")
    console.print(f"  File: {filepath}")
    if review_required:
        console.print(f"  [yellow]⚠ Review required before this becomes a formal decision.[/yellow]")
    console.print()


def capture_list(
    status_filter: Optional[str] = typer.Option(
        None, "--status", help="Filter by status: pending_review | confirmed | rejected"
    ),
    type_filter: Optional[str] = typer.Option(
        None, "--type", help="Filter by type: judgment | decision | principle"
    ),
) -> None:
    """列出所有候选判断."""
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    captures_dir = _captures_root(root)
    if not captures_dir.exists():
        console.print("[dim]No captures yet. Use 'flg capture add' to capture a judgment.[/dim]")
        return

    files = sorted(captures_dir.glob("cap-*.md"), reverse=True)
    if not files:
        console.print("[dim]No captures yet.[/dim]")
        return

    items = []
    for f in files:
        meta = _read_frontmatter(f)
        if not meta:
            continue
        # Apply filters
        if status_filter and meta.get("status") != status_filter:
            continue
        if type_filter and meta.get("type") != type_filter:
            continue
        items.append(meta)

    if not items:
        console.print(f"[dim]No captures match filters (status={status_filter}, type={type_filter}).[/dim]")
        return

    table = Table(title="Judgment Candidates")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Claim", style="white")

    for item in items:
        claim_short = item.get("claim", "")[:60]
        if item.get("claim", "") and len(item.get("claim", "")) > 60:
            claim_short += "..."
        table.add_row(
            item.get("id", "?"),
            item.get("type", "?"),
            item.get("status", "?"),
            claim_short,
        )

    console.print()
    console.print(table)
    console.print(f"\n[dim]{len(items)} capture(s)[/dim]")
    pending = sum(1 for i in items if i.get("status") == "pending_review")
    if pending:
        console.print(f"[yellow]{pending} pending review[/yellow]")
    console.print()


def capture_show(
    capture_id: str = typer.Argument(..., help="Capture ID, e.g. cap-20260708-153000-a1b2c3"),
) -> None:
    """查看单条候选判断的完整内容."""
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    # Support short form: if user passes just the hex suffix or partial ID
    captures_dir = _captures_root(root)
    filepath = captures_dir / f"{capture_id}.md"

    if not filepath.exists():
        # Try fuzzy match
        matches = list(captures_dir.glob(f"{capture_id}*.md"))
        if len(matches) == 1:
            filepath = matches[0]
        elif len(matches) > 1:
            console.print(f"[yellow]Multiple matches for '{capture_id}':[/yellow]")
            for m in sorted(matches):
                console.print(f"  {m.stem}")
            raise typer.Exit(1)
        else:
            console.print(f"[red]Capture not found: {capture_id}[/red]")
            console.print("[dim]Use 'flg capture list' to see all captures.[/dim]")
            raise typer.Exit(1)

    meta = _read_frontmatter(filepath)
    if not meta:
        console.print(f"[red]Failed to read capture: {filepath}[/red]")
        raise typer.Exit(1)

    console.print()
    console.print(f"[bold]Capture: {meta.get('id', capture_id)}[/bold]")
    console.print()

    # Metadata table
    mt = Table(show_header=False, box=None)
    mt.add_column("Field", style="cyan")
    mt.add_column("Value", style="white")
    mt.add_row("Created", str(meta.get("created_at", "")))
    mt.add_row("Type", str(meta.get("type", "")))
    mt.add_row("Status", str(meta.get("status", "")))
    mt.add_row("Confidence", str(meta.get("confidence", "")))
    mt.add_row("Source", str(meta.get("source", "")))
    mt.add_row("Review Required", str(meta.get("review_required", "")))
    console.print(mt)
    console.print()

    # Content
    if meta.get("question"):
        console.print(f"[bold cyan]Question:[/bold cyan] {meta['question']}")
        console.print()
    console.print(f"[bold]Claim:[/bold] {meta.get('claim', '')}")
    console.print()
    console.print(f"[bold]Rationale:[/bold] {meta.get('rationale', '')}")
    console.print()

    if meta.get("alternatives"):
        console.print("[bold yellow]Alternatives:[/bold yellow]")
        for alt in meta["alternatives"]:
            console.print(f"  • {alt}")
        console.print()

    if meta.get("risks"):
        console.print(f"[bold red]Risks:[/bold red] {meta['risks']}")
        console.print()

    if meta.get("raw_evidence"):
        console.print(Panel(
            meta["raw_evidence"],
            title="Raw Evidence",
            border_style="green",
        ))
        console.print()


def _read_frontmatter(filepath: Path) -> dict | None:
    """Read YAML frontmatter from a capture file."""
    try:
        raw = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    m = YAML_FRONTMATTER_RE.match(raw)
    if not m:
        return None

    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None

    if not isinstance(data, dict):
        return None

    return data
