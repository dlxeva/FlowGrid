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

from ..core.evidence import load_evidence_index, parse_decisions_ledger, validate_project
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
    # PROGRESS.md / CONSTRAINTS.md / GOAL_EVOLUTION.md template placeholders (发现 19)
    "(文件路径)",
    "(文档职责，自由填写)",
    "(创建日期)",
    '(被替代的文件路径，无则写\u201c无\u201d)',
    "(为什么生成这份文档？解决了什么问题？)",
    "(触发条件)",
    "(应采取的动作 / 判断)",
    "(例外条件；没有就写 none)",
    "(负责确认的人或角色)",
    "(什么情况下必须重新检查这条约束)",
    "(之前的目标)",
    "(现在的目标)",
    "(触发变化的事件 / 信息 / 约束)",
    "(影响了哪些文档 / 动作 / 边界)",
    "{created_at}",
    "{updated_at}",
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


def _first_section_line(text: str, headings: tuple[str, ...], default: str = "") -> str:
    """Return the first usable line from the first populated section alias."""
    for heading in headings:
        value = _first_meaningful_line(_section(text, heading), "")
        if value:
            return value
    return default


def _is_explicitly_obsolete(text: str) -> bool:
    """Return whether a source says it is no longer current project truth.

    A Context Pack may include historical files for traceability, but a file that
    explicitly says it was superseded must not fill current-state fields. This
    avoids reviving a pre-meeting framing when SNAPSHOT.md has already replaced it.
    """
    header = text[:1600].lower()
    markers = (
        "not current decision basis",
        "not the current decision basis",
        "current truth is in snapshot.md",
        "不作为当前决策依据",
        "当前真相见 snapshot.md",
        "当前真相见snapshot.md",
        "已被.*推翻",
    )
    return any(marker in header for marker in markers[:-1]) or bool(re.search(markers[-1], header))


def _list_items(text: str, limit: int = 8) -> list[str]:
    items: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("- "):
            continue
        item = line[2:].strip()
        if not item:
            continue
        # Skip if the item IS a placeholder, or ENDS with one (发现 19:
        # GOAL_EVOLUTION template items like '**When:** (日期)' leaked through)
        item_lower = item.lower()
        if item_lower in PLACEHOLDER_MARKERS:
            continue
        if any(item_lower.endswith(m.lower()) for m in PLACEHOLDER_MARKERS):
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


_CURRENT_DECISION_STATUSES = {"confirmed", "accepted", "active"}


def _parse_confirmed_decisions(
    decisions_content: str,
    evidence_items: Optional[dict] = None,
    limit: int = 5,
) -> list[dict[str, str]]:
    decisions = []
    evidence_items = evidence_items or {}
    for item in parse_decisions_ledger(decisions_content):
        if item.get("status") not in _CURRENT_DECISION_STATUSES:
            continue
        evidence = evidence_items.get(item["decision_id"], {})
        decisions.append(
            {
                "id": item["decision_id"],
                "title": item["title"],
                "status": item["status"],
                "authority": evidence.get("authority", "unknown"),
                "source_type": evidence.get("source_type", item.get("source_type", "unknown")),
                "decision": item["what_decided"],
                "rationale": item["rationale"] or "(rationale not recorded)",
                "alternatives": _compact_lines(item["alternatives"]) or "(not recorded)",
                "rejected": item["rejected_alternatives"] or "(not recorded)",
                "reversal": item["reversal_conditions"] or "(not recorded)",
            }
        )
    return decisions[-limit:]


def _is_template_noise(line: str) -> bool:
    """Return True if a line is init-template boilerplate, not real content (发现 19).

    Filters out: blockquote instructions (*/), HTML comments, placeholder
    headings like '### [文档名称]', horizontal rules, timestamps, and lines
    whose only content is a known placeholder marker.
    """
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith(">"):
        return True
    if stripped.startswith("<!--"):
        return True
    if stripped.startswith("---"):
        return True
    if stripped.startswith("*Created:") or stripped.startswith("*Last Updated"):
        return True
    # Placeholder headings like '### [文档名称]' or '### Constraint 001'
    if re.match(r"^#+\s*(\[|Constraint \d+|Goal Shift \d+)", stripped):
        return True
    # Lines that are entirely a placeholder marker
    if stripped in PLACEHOLDER_MARKERS:
        return True
    # Lines like '- **File:** (文件路径)' where value is a placeholder
    if any(stripped.endswith(m) for m in PLACEHOLDER_MARKERS):
        return True
    return False


def _compact_lines(text: str, limit_chars: int = 360) -> str:
    """Compact a file's content into one line, skipping template noise."""
    meaningful = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not _is_template_noise(line)
    ]
    compact = " ".join(meaningful)
    compact = re.sub(r"\s+", " ", compact).strip()
    if not compact:
        return ""
    if len(compact) > limit_chars:
        return compact[: limit_chars - 1].rstrip() + "…"
    return compact


def _pending_patch_summaries(root: Path, limit: int = 5) -> list[dict]:
    """Summarize patches that are still pending review.

    Filters out merged/rejected/superseded patches (发现 25) and patches
    whose decisions were already accepted via `flg review` (发现 20) —
    those decisions already appear in Confirmed Decisions, showing them
    again in Pending Judgments is redundant.
    """
    patches_dir = root / ".flg" / "patches"
    if not patches_dir.exists():
        return []

    # Build a set of patch_ids whose decisions were already reviewed+accepted
    # in state.json, so we can skip them here (发现 20).
    reviewed_accepted_ids: set[str] = set()
    state = load_state(root)
    if state:
        for p in state.get("pending_patches", []):
            if p.get("decision_review_status") == "accepted":
                pid = p.get("patch_id")
                if pid:
                    reviewed_accepted_ids.add(pid)

    _CLOSED_STATUSES = {"merged", "rejected", "superseded"}

    patches: list[dict] = []
    for patch_file in sorted(patches_dir.glob("*.patch.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        content = read_file_safe(patch_file) or ""
        if not content:
            continue
        patch_info = parse_patch_for_handoff(content)
        status = (patch_info.get("status") or "unknown").lower()

        # Skip closed patches (发现 25)
        if status in _CLOSED_STATUSES:
            continue

        # Skip patches already reviewed+accepted — their decisions are in
        # Confirmed Decisions already (发现 20)
        patch_id = patch_info.get("patch_id", "")
        if patch_id in reviewed_accepted_ids:
            continue

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
        out += f"- Authority: {decision['authority']}\n"
        out += f"- Decision: {decision['decision']}\n"
        out += f"- Rationale: {decision['rationale']}\n"
        out += f"- Alternatives considered: {decision['alternatives']}\n"
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
        refs.append(
            f"- {decision['id']}: DECISIONS.md#{decision['id']} "
            f"(source_type: {decision['source_type']}, status: confirmed)"
        )
    for patch in patches:
        refs.append(f"- {patch['filename']}: .flg/patches/{patch['filename']} (source_type: closeout_patch, status: pending_review)")
    if not refs:
        return "- (none recorded)\n"
    return "\n".join(refs) + "\n"


def _render_source_health(report: dict) -> str:
    """Expose ledger/index drift so a bounded pack cannot look fully clean."""
    lines = [
        f"- Status: {report['status']}",
        f"- Formal decisions: {report['decision_count']}",
        f"- Indexed decisions: {report['index_count']}",
        f"- Missing index entries: {len(report['missing_index'])}",
        f"- Orphan index entries: {len(report['orphan_index'])}",
        f"- Broken evidence references: {len(report['broken_references'])}",
        f"- Legacy paths: {len(report['legacy_paths'])}",
        f"- Closed patches still pending: {len(report['merged_pending'])}",
    ]
    if report["issues"]:
        lines.append(f"- Issues: {', '.join(report['issues'])}")
        lines.append("- Required action: run `flg doctor` and repair or rebuild before treating the pack as complete.")
    else:
        lines.append("- Required action: none; continue to monitor source health.")
    return "\n".join(lines) + "\n"


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
    framing_is_obsolete = _is_explicitly_obsolete(framing_content)

    project_name = state.get("project_name", "Unknown")
    project_type = _project_field(project_content, "Project Type", "unknown")
    client = _project_field(project_content, "Client/Sponsor", "unknown")
    current_stage = state.get("current_stage") or _project_field(project_content, "Current Stage", "unknown")
    updated_at = datetime.now().isoformat(timespec="seconds")

    current_framing = "" if framing_is_obsolete else framing_content
    review_object = _first_section_line(
        current_framing,
        ("Review Objects", "审核对象", "Core Observation Questions", "核心观察问题"),
        "(not defined)",
    )
    proof_object = _first_section_line(current_framing, ("Success Criteria", "成功标准"), "(not defined)")
    current_goal = _first_section_line(snapshot_content, ("Current Core Goal", "Current Goal", "当前核心目标", "当前目标"))
    if not current_goal:
        current_goal = _first_section_line(current_framing, ("Goals", "目标"), "(not defined)")

    # A project can have a useful governing frame even when no current execution
    # goal is declared. Keep the two concepts separate so an observation frame
    # is not silently promoted into a formal goal.
    project_frame = _first_section_line(
        snapshot_content,
        ("Project Positioning", "项目定位", "Primary Question", "主问题"),
    )
    if not project_frame:
        project_frame = _first_section_line(
            current_framing,
            ("Project Positioning", "项目定位", "Primary Question", "主问题", "Problem Statement", "问题陈述"),
            "(not defined)",
        )

    evidence_items = load_evidence_index(root).get("items", {})
    confirmed_decisions = _parse_confirmed_decisions(decisions_content, evidence_items)
    pending_patches = _pending_patch_summaries(root)
    source_health = validate_project(root)

    assumptions = _list_items(_section(snapshot_content, "Unconfirmed"), limit=8)
    assumptions += _list_items(_section(snapshot_content, "未确认"), limit=8)
    assumptions += _list_items(_section(current_framing, "Open Questions"), limit=5)
    assumptions += _list_items(_section(current_framing, "未确认问题"), limit=5)
    assumptions = assumptions[:8]

    # Do not infer contradictions from arbitrary prose. A project or host must
    # mark a signal for recheck before it becomes startup-state guidance.
    needs_recheck = _list_items(_section(snapshot_content, "Needs Recheck"), limit=8)
    needs_recheck += _list_items(_section(snapshot_content, "待复查"), limit=8)
    needs_recheck += _list_items(_section(snapshot_content, "待核验"), limit=8)
    needs_recheck = needs_recheck[:8]

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
    risks = risks[:8]

    next_actions = []
    raw_next_actions = state.get("next_actions", [])
    if isinstance(raw_next_actions, list):
        next_actions.extend(str(item) for item in raw_next_actions[:8])
    snapshot_next = ""
    for heading in (
        "Next Highest Priority Action",
        "Next Highest Priority Actions",
        "Next Highest-Priority Actions",
        "Next Actions",
        "下一步最高优先级",
        "下一步行动",
        "下一步",
    ):
        snapshot_next = _first_meaningful_line(_section(snapshot_content, heading), "")
        if snapshot_next:
            break
    if snapshot_next and snapshot_next not in next_actions:
        next_actions.append(snapshot_next)
    next_actions = next_actions[:10]

    recent_progress = _compact_lines(progress_content, limit_chars=900) or "(not recorded)"
    snapshot_constraints = _list_items(_section(snapshot_content, "Hard Constraints"), limit=6)
    snapshot_constraints += _list_items(_section(snapshot_content, "硬约束"), limit=6)
    snapshot_non_goals = _list_items(_section(snapshot_content, "Current Non-Goals"), limit=6)
    snapshot_non_goals += _list_items(_section(snapshot_content, "当前不做什么"), limit=6)
    if snapshot_constraints or snapshot_non_goals:
        active_constraints = _render_items(snapshot_constraints[:6])
        if snapshot_non_goals:
            active_constraints += "\nCurrent non-goals:\n" + _render_items(snapshot_non_goals[:6])
    else:
        active_constraints = _compact_lines(constraints_content, limit_chars=700) or "(not recorded)"

    sources_included = [
        "PROJECT.md",
        "SNAPSHOT.md",
        "DECISIONS.md",
        "PROGRESS.md",
        "CONSTRAINTS.md",
        "GOAL_EVOLUTION.md",
        ".flg/state.json",
        ".flg/patches/*.patch.md",
    ]
    if not framing_is_obsolete:
        sources_included.insert(1, "FRAMING.md")

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

## Project Frame

{project_frame}

## Confirmed Decisions

{_render_confirmed_decisions(confirmed_decisions)}
## Pending Judgments

{_render_pending_patches(pending_patches)}
## Active Assumptions

{_render_items(assumptions)}
## Needs Recheck

{_render_items(needs_recheck)}
## Rejected Alternatives

{_render_items(rejected_alternatives)}
## Goal Evolution

{_render_items(superseded)}
## Current Risks

{_render_items(risks)}
## Recent Progress

{recent_progress}

## Active Constraints

{active_constraints}

## Source Health

{_render_source_health(source_health)}
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
- Surface the boundary before changing goals, boundaries, review objects, proof
  objects, or core judgments; interrupt the user only when an external,
  irreversible action depends on that change.
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
        "source_health": source_health,
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
