"""flg context command - Generate bounded agent startup context."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown

from ..core.files import is_flg_project, read_file_safe
from ..core.state import load_state
from .handoff import parse_patch_for_handoff

console = Console()


PLACEHOLDER_MARKERS = {
    "(日期)",
    "(立项/创意策划/执行/复盘)",
    "(为什么需要做这个判断？当时发生了什么？)",
    "(到底在问什么？)",
    "(方案A)",
    "(方案B)",
    "(方案C)",
    "(选了什么)",
    "(为什么选这个？依据是什么？)",
    "(为什么不选其他方案？)",
    "(这个选择有什么风险？)",
    "(怎么验证这个判断对不对？)",
    "(什么情况下需要重新审视这个决策？)",
    "(none yet)",
    "(none identified)",
    "none",
}


def _strip_frontmatter(text: str) -> str:
    return re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL).strip()


def _section(text: str, heading: str, level: int = 2) -> str:
    """Extract a markdown section by exact heading text."""
    lines = text.splitlines()
    prefix = "#" * level + " "
    start: Optional[int] = None
    for idx, line in enumerate(lines):
        if line.strip().lower() == f"{prefix}{heading}".lower():
            start = idx + 1
            break
    if start is None:
        return ""

    end = len(lines)
    for idx in range(start, len(lines)):
        if lines[idx].startswith(prefix):
            end = idx
            break
    return "\n".join(lines[start:end]).strip()


def _first_meaningful_line(text: str, default: str = "(not defined)") -> str:
    for raw in text.splitlines():
        line = raw.strip().strip("-").strip()
        if not line:
            continue
        if line.startswith("*") or line.startswith("---"):
            continue
        if line in PLACEHOLDER_MARKERS:
            continue
        return line
    return default


def _list_items(text: str, limit: int = 8) -> list[str]:
    items: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("- "):
            continue
        item = line[2:].strip()
        if not item or item.lower() in PLACEHOLDER_MARKERS:
            continue
        items.append(item)
        if len(items) >= limit:
            break
    return items


def _project_field(project_content: str, field: str, default: str = "") -> str:
    pattern = rf"^- \*\*{re.escape(field)}:\*\*\s*(.+)$"
    match = re.search(pattern, project_content, flags=re.MULTILINE)
    if not match:
        return default
    value = match.group(1).strip()
    if value in PLACEHOLDER_MARKERS:
        return default
    return value


def _decision_subsection(block: str, heading: str) -> str:
    lines = block.splitlines()
    start: Optional[int] = None
    for idx, line in enumerate(lines):
        if line.strip() == f"### {heading}":
            start = idx + 1
            break
    if start is None:
        return ""

    end = len(lines)
    for idx in range(start, len(lines)):
        if lines[idx].startswith("### ") or lines[idx].startswith("## "):
            end = idx
            break
    return "\n".join(lines[start:end]).strip()


def _parse_confirmed_decisions(decisions_content: str, limit: int = 5) -> list[dict[str, str]]:
    decisions: list[dict[str, str]] = []
    pattern = re.compile(r"^##\s+(D-\d+)\s*\|\s*(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(decisions_content))

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(decisions_content)
        block = decisions_content[start:end]

        decision_text = _first_meaningful_line(_decision_subsection(block, "最终决策"), "")
        rationale = _first_meaningful_line(_decision_subsection(block, "决策理由"), "")
        alternatives = _decision_subsection(block, "备选方案")
        rejected = _first_meaningful_line(_decision_subsection(block, "放弃理由"), "")
        reversal = _first_meaningful_line(_decision_subsection(block, "复盘入口"), "")

        # Skip the initial template placeholder decision.
        if not decision_text or decision_text in PLACEHOLDER_MARKERS or decision_text.startswith("("):
            continue

        decisions.append(
            {
                "id": match.group(1).strip(),
                "title": match.group(2).strip(),
                "decision": decision_text,
                "rationale": rationale or "(rationale not recorded)",
                "alternatives": _compact_lines(alternatives) or "(not recorded)",
                "rejected": rejected or "(not recorded)",
                "reversal": reversal or "(not recorded)",
            }
        )

    return decisions[-limit:]


def _compact_lines(text: str, limit_chars: int = 360) -> str:
    compact = " ".join(line.strip() for line in text.splitlines() if line.strip())
    compact = re.sub(r"\s+", " ", compact).strip()
    if len(compact) > limit_chars:
        return compact[: limit_chars - 1].rstrip() + "…"
    return compact


def _pending_patch_summaries(root: Path, limit: int = 5) -> list[dict]:
    patches_dir = root / ".flg" / "patches"
    if not patches_dir.exists():
        return []

    patches: list[dict] = []
    for patch_file in sorted(patches_dir.glob("*.patch.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        content = read_file_safe(patch_file) or ""
        if not content:
            continue
        patch_info = parse_patch_for_handoff(content)
        status = patch_info.get("status") or "unknown"
        # Keep unknown status because older patch files may not parse cleanly but still represent pending state.
        patches.append(
            {
                "filename": patch_file.name,
                "status": status,
                "source_command": patch_info.get("source_command", "unknown"),
                "risk_level": patch_info.get("risk_level", "unknown"),
                "generated_at": patch_info.get("generated_at", "unknown"),
                "decisions": patch_info.get("decisions", [])[:3],
                "risks": patch_info.get("risks", [])[:5],
                "questions": patch_info.get("questions", [])[:5],
                "next_actions": patch_info.get("next_actions", [])[:5],
            }
        )
        if len(patches) >= limit:
            break
    return patches


def _render_items(items: list[str], empty: str = "(none recorded)") -> str:
    if not items:
        return f"- {empty}\n"
    return "".join(f"- {item}\n" for item in items)


def _render_confirmed_decisions(decisions: list[dict[str, str]]) -> str:
    if not decisions:
        return "- (none recorded)\n"

    out = ""
    for decision in decisions:
        out += f"### {decision['id']} | {decision['title']}\n"
        out += "- Status: confirmed\n"
        out += "- Authority: high if accepted through review; otherwise check DECISIONS.md\n"
        out += f"- Decision: {decision['decision']}\n"
        out += f"- Rationale: {decision['rationale']}\n"
        out += f"- Rejected alternatives: {decision['rejected']}\n"
        out += f"- Reversal conditions: {decision['reversal']}\n"
        out += f"- Evidence: DECISIONS.md#{decision['id']}\n\n"
    return out


def _render_pending_patches(patches: list[dict]) -> str:
    if not patches:
        return "- (none recorded)\n"

    out = ""
    for patch in patches:
        out += f"### {patch['filename']}\n"
        out += f"- Status: pending_review\n"
        out += f"- Source command: {patch['source_command']}\n"
        out += f"- Risk level: {patch['risk_level']}\n"
        out += f"- Generated at: {patch['generated_at']}\n"
        decisions = patch.get("decisions", [])
        if decisions:
            out += "- Candidate judgments:\n"
            for decision in decisions:
                title = decision.get("title") or decision.get("what_decided") or "Untitled candidate"
                out += f"  - {title}\n"
        risks = patch.get("risks", [])
        if risks:
            out += "- Risks:\n"
            for risk in risks[:3]:
                out += f"  - {risk}\n"
        actions = patch.get("next_actions", [])
        if actions:
            out += "- Suggested next actions:\n"
            for action in actions[:3]:
                out += f"  - {action}\n"
        out += "\n"
    return out


def _render_evidence_refs(decisions: list[dict[str, str]], patches: list[dict]) -> str:
    refs: list[str] = []
    for decision in decisions:
        refs.append(f"- {decision['id']}: DECISIONS.md#{decision['id']} (source_type: review_action, status: confirmed)")
    for patch in patches:
        refs.append(f"- {patch['filename']}: .flg/patches/{patch['filename']} (source_type: closeout_patch, status: pending_review)")
    if not refs:
        return "- (none recorded)\n"
    return "\n".join(refs) + "\n"


def build_context_pack(root: Path, mode: str = "resume", budget: int = 4000) -> tuple[str, dict]:
    if mode != "resume":
        raise ValueError("v0 only supports --mode resume")

    state = load_state(root)
    if not state:
        raise ValueError("No readable state found. Run 'flg init' first.")

    project_content = read_file_safe(root / "PROJECT.md") or ""
    framing_content = read_file_safe(root / "FRAMING.md") or ""
    snapshot_content = _strip_frontmatter(read_file_safe(root / "SNAPSHOT.md") or "")
    decisions_content = read_file_safe(root / "DECISIONS.md") or ""
    progress_content = read_file_safe(root / "PROGRESS.md") or ""
    constraints_content = read_file_safe(root / "CONSTRAINTS.md") or ""
    goal_evolution_content = read_file_safe(root / "GOAL_EVOLUTION.md") or ""

    project_name = state.get("project_name", "Unknown")
    project_type = _project_field(project_content, "Project Type", "unknown")
    client = _project_field(project_content, "Client/Sponsor", "unknown")
    current_stage = state.get("current_stage") or _project_field(project_content, "Current Stage", "unknown")
    updated_at = datetime.now().isoformat(timespec="seconds")

    review_object = _first_meaningful_line(_section(framing_content, "Review Objects"), "(not defined)")
    proof_object = _first_meaningful_line(_section(framing_content, "Success Criteria"), "(not defined)")
    current_goal = _first_meaningful_line(_section(snapshot_content, "Current Core Goal"), "")
    if not current_goal:
        current_goal = _first_meaningful_line(_section(framing_content, "Goals"), "(not defined)")

    confirmed_decisions = _parse_confirmed_decisions(decisions_content)
    pending_patches = _pending_patch_summaries(root)

    assumptions = _list_items(_section(snapshot_content, "Unconfirmed"), limit=8)
    assumptions += _list_items(_section(framing_content, "Open Questions"), limit=5)
    assumptions = assumptions[:8]

    rejected_alternatives: list[str] = []
    for decision in confirmed_decisions:
        rejected = decision.get("rejected")
        if rejected and rejected != "(not recorded)":
            rejected_alternatives.append(f"{decision['id']}: {rejected}")
    for patch in pending_patches:
        for decision in patch.get("decisions", []):
            rejected = decision.get("rejected") or decision.get("alternatives")
            if rejected:
                rejected_alternatives.append(f"{patch['filename']}: {rejected}")
    rejected_alternatives = rejected_alternatives[:8]

    superseded = _list_items(goal_evolution_content, limit=8)
    risks = _list_items(_section(snapshot_content, "Current Risks"), limit=8)
    for patch in pending_patches:
        for risk in patch.get("risks", [])[:3]:
            if risk not in risks:
                risks.append(risk)
    risks = risks[:8]

    next_actions = []
    raw_next_actions = state.get("next_actions", [])
    if isinstance(raw_next_actions, list):
        next_actions.extend(str(item) for item in raw_next_actions[:8])
    snapshot_next = _first_meaningful_line(_section(snapshot_content, "Next Highest Priority Action"), "")
    if snapshot_next and snapshot_next not in next_actions:
        next_actions.append(snapshot_next)
    for patch in pending_patches:
        for action in patch.get("next_actions", [])[:3]:
            if action not in next_actions:
                next_actions.append(action)
    next_actions = next_actions[:10]

    recent_progress = _compact_lines(progress_content, limit_chars=900) or "(not recorded)"
    active_constraints = _compact_lines(constraints_content, limit_chars=700) or "(not recorded)"

    sources_included = [
        "PROJECT.md",
        "FRAMING.md",
        "SNAPSHOT.md",
        "DECISIONS.md",
        "PROGRESS.md",
        "CONSTRAINTS.md",
        "GOAL_EVOLUTION.md",
        ".flg/state.json",
        ".flg/patches/*.patch.md",
    ]

    content = f"""# FLG Context Pack

## Project Identity

- Project: {project_name}
- Project type: {project_type}
- Client/Sponsor: {client}
- Stage: {current_stage}
- Mode: {mode}
- Generated: {updated_at}

## Review Object

{review_object}

## Proof Object

{proof_object}

## Current Goal

{current_goal}

## Confirmed Decisions

{_render_confirmed_decisions(confirmed_decisions)}
## Pending Judgments

{_render_pending_patches(pending_patches)}
## Active Assumptions

{_render_items(assumptions)}
## Rejected Alternatives

{_render_items(rejected_alternatives)}
## Superseded Judgments

{_render_items(superseded)}
## Current Risks

{_render_items(risks)}
## Recent Progress

{recent_progress}

## Active Constraints

{active_constraints}

## Next Actions

{_render_items(next_actions)}
## Evidence References

{_render_evidence_refs(confirmed_decisions, pending_patches)}
## Agent Instructions

- Read this Context Pack before acting.
- Treat confirmed decisions as inheritable current project truth.
- Treat pending judgments as candidates, not confirmed facts.
- Surface assumptions when using them to support recommendations.
- Do not revive rejected alternatives unless new evidence exists.
- Do not rely on superseded judgments as current truth.
- Ask for review before changing goals, boundaries, review objects, proof objects, or core judgments.
- Retrieve evidence when asked why a judgment was made.
- Do not load raw sessions by default.

## Sources Included

{_render_items(sources_included)}"""

    max_chars = max(1200, budget * 4)
    truncated = False
    if len(content) > max_chars:
        content = content[: max_chars - 120].rstrip() + "\n\n<!-- Context Pack truncated to budget. Increase --budget for a larger pack. -->\n"
        truncated = True

    metadata = {
        "path": str(root / ".flg" / "context" / "startup.md"),
        "chars": len(content),
        "estimated_tokens": len(content) // 4,
        "sources_included": sources_included,
        "pending_patches_count": len(pending_patches),
        "confirmed_decisions_count": len(confirmed_decisions),
        "truncated": truncated,
    }
    return content, metadata


def context_command(
    mode: str = typer.Option("resume", "--mode", help="Context mode. v0 supports only 'resume'."),
    budget: int = typer.Option(4000, "--budget", help="Approximate token budget for the generated context pack."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Optional output path. Defaults to .flg/context/startup.md."),
    print_pack: bool = typer.Option(False, "--print", help="Print the generated context pack after writing it."),
) -> None:
    """Generate a bounded Context Pack for agent startup."""
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    try:
        content, metadata = build_context_pack(root, mode=mode, budget=budget)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    output_path = Path(output) if output else root / ".flg" / "context" / "startup.md"
    if not output_path.is_absolute():
        output_path = root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    console.print()
    console.print("[bold green]✓ Context Pack generated[/bold green]")
    console.print(f"[bold]Path:[/bold] {output_path}")
    console.print(f"[bold]Size:[/bold] {metadata['chars']} chars (~{metadata['estimated_tokens']} tokens)")
    console.print(f"[bold]Sources included:[/bold] {len(metadata['sources_included'])}")
    console.print(f"[bold]Pending patches:[/bold] {metadata['pending_patches_count']}")
    console.print(f"[bold]Confirmed decisions:[/bold] {metadata['confirmed_decisions_count']}")
    if metadata["confirmed_decisions_count"] == 0:
        console.print("[yellow]Warning: no reviewed decisions found. Context Pack will rely on current state and pending material.[/yellow]")
    if metadata["truncated"]:
        console.print("[yellow]Warning: Context Pack was truncated to fit the requested budget.[/yellow]")
    console.print("[dim]Raw sessions were not loaded by default.[/dim]")

    if print_pack:
        console.print()
        console.print(Markdown(content))
