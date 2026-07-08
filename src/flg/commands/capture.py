"""flg capture commands - Real-time judgment candidate capture and review."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from ..core.files import is_flg_project, read_file_safe

console = Console()
CAPTURES_DIR = ".flg/captures"
EVIDENCE_INDEX_PATH = Path(".flg") / "context" / "evidence_index.json"

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
    return ["judgment", "decision", "principle", "thought", "hypothesis"]


def capture_add(
    claim: str = typer.Option(
        ..., "-c", "--claim", help="判断主张（必填）"
    ),
    rationale: str = typer.Option(
        ..., "-r", "--rationale", help="判断理由（必填）"
    ),
    type_: Optional[str] = typer.Option(
        "judgment", "-t", "--type", help="判断类型: judgment | decision | principle | thought | hypothesis"
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
        None, "--type", help="Filter by type: judgment | decision | principle | thought | hypothesis"
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


def _write_frontmatter(filepath: Path, data: dict) -> None:
    """Update YAML frontmatter in a capture file, preserving body."""
    raw = filepath.read_text(encoding="utf-8")
    body = YAML_FRONTMATTER_RE.sub("", raw).strip()
    yaml_block = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    filepath.write_text(f"---\n{yaml_block}---\n\n{body}\n", encoding="utf-8")


# ── Review helpers ──────────────────────────────────────────────────────

def _next_decision_number(decisions_content: str) -> int:
    numbers = [int(m) for m in re.findall(r"## D-(\d+)", decisions_content)]
    return max(numbers, default=0) + 1


def _build_decision_entry(number: int, meta: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    claim = meta.get("claim", "")
    rationale = meta.get("rationale", "")
    question = meta.get("question", "项目推进中的关键判断")
    alternatives = meta.get("alternatives", [])
    alt_str = "、".join(alternatives) if alternatives else "未记录备选方案"
    risks = meta.get("risks", "待结合项目上下文补充")
    evidence = meta.get("raw_evidence", "")

    return f"""## D-{number:03d} | {claim[:50]}

### 决策时间
{today}

### 所属阶段
执行

### 决策背景
由 `flg capture review` 从候选判断中确认写入。

### 核心问题
{question}

### 备选方案
A. {alt_str}

### 最终决策
{claim}

### 决策理由
{rationale}

### 放弃理由
选择了当前方案，放弃其他备选方案。

### 风险判断
{risks}

### 后续验证
通过后续执行结果和项目反馈验证。

### 复盘入口
如果关键前提变化或出现新的替代方案，需要重新评估。

---

*Source: {evidence if evidence else '用户判断'}*
"""


def _load_evidence_index(root: Path) -> dict:
    path = root / EVIDENCE_INDEX_PATH
    if not path.exists():
        return {"version": 1, "items": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "items": {}}
    if not isinstance(data, dict) or "items" not in data:
        return {"version": 1, "items": {}}
    return data


def _save_evidence_index(root: Path, index: dict) -> Path:
    path = root / EVIDENCE_INDEX_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    index["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ── capture review command ──────────────────────────────────────────────

def capture_review(
    auto_confirm: bool = typer.Option(
        False, "--auto-confirm", help="Auto-confirm all pending captures (use with caution)"
    ),
) -> None:
    """逐条审核候选判断，确认的写入 DECISIONS.md，拒绝的标记为 rejected。"""
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    captures_dir = _captures_root(root)
    if not captures_dir.exists():
        console.print("[dim]No captures to review. Use 'flg capture add' first.[/dim]")
        return

    files = sorted(captures_dir.glob("cap-*.md"))
    pending = []
    for f in files:
        meta = _read_frontmatter(f)
        if meta and meta.get("status") == "pending_review":
            pending.append((f, meta))

    if not pending:
        console.print("[green]No pending captures to review.[/green]")
        return

    decisions_path = root / "DECISIONS.md"
    decisions_content = read_file_safe(decisions_path) or "# Decision Log\n"
    next_num = _next_decision_number(decisions_content)
    evidence_index = _load_evidence_index(root)
    reviewed_at = datetime.now().isoformat(timespec="seconds")

    accepted: list = []
    rejected: list = []

    console.print()
    console.print(f"[bold]Reviewing {len(pending)} pending capture(s)[/bold]")
    console.print()

    for filepath, meta in pending:
        capture_id = meta.get("id", filepath.stem)
        console.print(f"[bold cyan]{capture_id}[/bold cyan]")
        console.print(f"  Type: {meta.get('type', '?')}  |  Confidence: {meta.get('confidence', '?')}")
        console.print(f"  Claim: [white]{meta.get('claim', '')}[/white]")
        if meta.get("rationale"):
            console.print(f"  Rationale: [dim]{meta['rationale'][:100]}[/dim]")
        if meta.get("raw_evidence"):
            console.print(f"  Evidence: [dim]{meta['raw_evidence'][:80]}[/dim]")
        console.print()

        if auto_confirm:
            choice = "a"
        else:
            console.print("  [a]ccept  [r]eject  [s]kip")
            choice = typer.prompt("  Choice", default="a", show_default=False).strip().lower()

        if choice == "a":
            decision_id = f"D-{next_num:03d}"
            entry = _build_decision_entry(next_num, meta)
            decisions_content = decisions_content.rstrip() + "\n\n" + entry
            evidence_index["items"][decision_id] = {
                "decision_id": decision_id,
                "status": "confirmed",
                "authority": "high",
                "source_type": "capture_review",
                "source_capture": str(filepath.relative_to(root)),
                "source_excerpt": meta.get("raw_evidence", meta.get("claim", "")),
                "reviewed_at": reviewed_at,
                "title": meta.get("claim", "")[:60],
                "rationale": meta.get("rationale", ""),
                "rejected_alternatives": ", ".join(meta.get("alternatives", [])),
            }
            meta["status"] = "confirmed"
            meta["reviewed_at"] = reviewed_at
            _write_frontmatter(filepath, meta)
            accepted.append((capture_id, decision_id))
            next_num += 1
            console.print(f"  [green]✓ Accepted → {decision_id}[/green]")
        elif choice == "r":
            meta["status"] = "rejected"
            meta["reviewed_at"] = reviewed_at
            _write_frontmatter(filepath, meta)
            rejected.append(capture_id)
            console.print(f"  [red]✗ Rejected[/red]")
        else:
            console.print(f"  [dim]⊙ Skipped[/dim]")
        console.print()

    if accepted:
        decisions_path.write_text(decisions_content, encoding="utf-8")
        _save_evidence_index(root, evidence_index)
        console.print(f"[bold green]✓ {len(accepted)} decision(s) written to DECISIONS.md[/bold green]")
        for cap_id, dec_id in accepted:
            console.print(f"  {cap_id} → [cyan]{dec_id}[/cyan]")
    if rejected:
        console.print(f"[yellow]{len(rejected)} rejected[/yellow]")

    remaining = len(pending) - len(accepted) - len(rejected)
    if remaining:
        console.print(f"[dim]{remaining} skipped[/dim]")
    if not accepted and not rejected:
        console.print("[dim]No changes made.[/dim]")
    console.print()


# ── judgment profile command ────────────────────────────────────────────

PROFILE_FILE = "_profile.yaml"


def capture_profile(
    add_phrase: str | None = typer.Option(
        None, "--add", help="添加项目特有的判断触发词"
    ),
    remove_phrase: str | None = typer.Option(
        None, "--remove", help="移除触发词"
    ),
) -> None:
    """管理项目的判断语言特征（judgment profile），帮助 Agent 识别你的判断信号。"""
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    captures_dir = _ensure_captures_dir(root)
    profile_path = captures_dir / PROFILE_FILE
    profile: dict = {"trigger_phrases": []}

    if profile_path.exists():
        try:
            profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            pass
    if not isinstance(profile, dict):
        profile = {"trigger_phrases": []}
    profile.setdefault("trigger_phrases", [])

    if add_phrase:
        if add_phrase not in profile["trigger_phrases"]:
            profile["trigger_phrases"].append(add_phrase)
            console.print(f"[green]✓ Added:[/green] {add_phrase}")
        else:
            console.print(f"[dim]Already exists: {add_phrase}[/dim]")
    elif remove_phrase:
        if remove_phrase in profile["trigger_phrases"]:
            profile["trigger_phrases"].remove(remove_phrase)
            console.print(f"[yellow]Removed: {remove_phrase}[/yellow]")
        else:
            console.print(f"[dim]Not found: {remove_phrase}[/dim]")
    else:
        console.print()
        console.print("[bold]Judgment Profile[/bold]")
        console.print(f"  {profile_path}")
        console.print()
        if profile["trigger_phrases"]:
            console.print("[bold cyan]Custom Trigger Phrases:[/bold cyan]")
            for p in profile["trigger_phrases"]:
                console.print(f"  • {p}")
        else:
            console.print("[dim]No custom trigger phrases.[/dim]")
            console.print("Add: [cyan]flg capture profile --add \"你的惯用表达\"[/cyan]")
        console.print()

    if add_phrase or remove_phrase:
        profile_path.write_text(
            yaml.dump(profile, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
