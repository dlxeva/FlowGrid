"""flg merge command - Merge pending patches into formal ledger."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from ..core.files import is_flg_project, read_file_safe, safe_write
from ..core.patches import list_patches
from ..core.state import load_state, save_state
from ..templates import get_iso_now
from .patch_cmd import _update_patch_file_status

console = Console()


def parse_patch_sections(content: str) -> dict:
    """Parse patch content into sections."""
    sections = {}
    current_section = None
    current_content = []
    
    for line in content.split("\n"):
        # Detect section headers
        if line.startswith("## "):
            # Save previous section
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            
            # Start new section
            current_section = line[3:].strip()
            current_content = []
        elif current_section:
            current_content.append(line)
    
    # Save last section
    if current_section:
        sections[current_section] = "\n".join(current_content).strip()
    
    return sections


def extract_progress_entry(sections: dict) -> Optional[str]:
    """Extract PROGRESS.md entry from patch."""
    # New format: look for Session Summary
    for key, content in sections.items():
        if "Session Summary" in key or "session summary" in key.lower():
            # Generate a simple progress entry
            date = datetime.now().strftime("%Y-%m-%d")
            return f"""### {date}: Session Progress

- **What happened:** {content[:200] if content else '(to be filled)'}
- **What was produced:** Closeout patch generated
- **What was modified:** Pending patches updated
- **What problems arose:** (none identified)
- **Next step:** Review pending patches and continue
"""
    
    # Old format: look for PROGRESS section
    for key, content in sections.items():
        if "PROGRESS" in key or "progress" in key.lower():
            # Extract markdown block
            match = re.search(r"```markdown\n(.*?)```", content, re.DOTALL)
            if match:
                return match.group(1).strip()
    
    # Fallback: generate from summary
    for key, content in sections.items():
        if "Summary" in key or "summary" in key.lower():
            date = datetime.now().strftime("%Y-%m-%d")
            return f"""### {date}: Session Progress

- **What happened:** {content[:200] if content else '(to be filled)'}
- **What was produced:** Closeout patch generated
- **What was modified:** Pending patches updated
- **What problems arose:** (none identified)
- **Next step:** Review pending patches and continue
"""
    
    return None


def extract_decisions(sections: dict) -> list[dict]:
    """Extract candidate decisions from patch."""
    decisions = []
    
    for key, content in sections.items():
        if "decision" in key.lower() or "Decision" in key:
            blocks = re.split(r"(?=###\s+Candidate Decision \d+:)", content)
            for block in blocks:
                if not block.strip().startswith("### Candidate Decision"):
                    continue
                title_match = re.search(r"###\s+Candidate Decision \d+:\s*(.*)", block)
                content_match = re.search(r"\*\*What was decided:\*\*\s*(.*)", block)
                source_match = re.search(r"source_excerpt:\s*>\s*(.*)", block)
                status_match = re.search(r"status:\s*(.*)", block)
                if content_match:
                    decisions.append({
                        "title": title_match.group(1).strip() if title_match else "Candidate decision",
                        "content": content_match.group(1).strip(),
                        "source": source_match.group(1).strip() if source_match else "transcript excerpt",
                        "status": status_match.group(1).strip() if status_match else "needs_background_processing",
                    })
    
    return decisions


def extract_risks(sections: dict) -> list[str]:
    """Extract risks from patch."""
    risks = []
    
    for key, content in sections.items():
        if "risk" in key.lower() or "Risk" in key:
            # Find risk items
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("- ") and line != "- (none identified)":
                    risks.append(line[2:])
    
    return risks


def extract_open_questions(sections: dict) -> list[str]:
    """Extract open questions from patch."""
    questions = []
    
    for key, content in sections.items():
        if "question" in key.lower() or "Question" in key:
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("- ") and line != "- (none identified)":
                    questions.append(line[2:])
    
    return questions


def extract_next_actions(sections: dict) -> list[str]:
    """Extract suggested next actions from a closeout patch."""
    actions = []
    for key, content in sections.items():
        if "suggested next actions" not in key.lower():
            continue
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- ") and line != "- (none identified)":
                actions.append(line[2:])
    return actions


def _patch_header_status(content: str) -> str:
    """Return the lifecycle status declared in a patch header."""
    for line in content.split("\n"):
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip().lower()
    return ""


def merge_patch(
    patch_file: str = typer.Option(..., "--patch", "-p", help="Patch file to merge"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview merge without changes"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "--autonomous",
        help="Merge without an interactive prompt for an AI host background flow",
    ),
) -> None:
    """Merge a pending patch into the formal ledger."""
    root = Path.cwd()
    
    # Check if this is a FLG project
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)
    
    # Find patch file
    patch_path = Path(patch_file)
    if not patch_path.exists():
        # Try in .flg/patches/
        patch_path = root / ".flg" / "patches" / patch_file
        if not patch_path.exists():
            console.print(f"[red]Patch not found: {patch_file}[/red]")
            raise typer.Exit(1)
    
    # Read patch content
    content = read_file_safe(patch_path)
    if not content:
        console.print("[red]Patch is empty.[/red]")
        raise typer.Exit(1)

    patch_status = _patch_header_status(content)
    if patch_status and patch_status != "pending_review":
        console.print(f"[red]Patch is closed ({patch_status}) and cannot be merged.[/red]")
        raise typer.Exit(1)
    
    # Parse patch
    sections = parse_patch_sections(content)
    
    # Load state
    state = load_state(root)
    if not state:
        console.print("[red]No state found. Run 'flg init' first.[/red]")
        raise typer.Exit(1)
    
    # Extract content
    progress_entry = extract_progress_entry(sections)
    decisions = extract_decisions(sections)
    risks = extract_risks(sections)
    questions = extract_open_questions(sections)
    next_actions = extract_next_actions(sections)
    reviewed_decisions_already_accepted = False
    merge_patch_id = ""
    for line in content.split("\n"):
        if line.startswith("patch_id:"):
            merge_patch_id = line.split(":", 1)[1].strip()
            break
    if state.get("pending_patches"):
        for pending in state["pending_patches"]:
            if pending.get("patch_id") == merge_patch_id and pending.get("decision_review_status") == "accepted":
                reviewed_decisions_already_accepted = True
                break
    
    # Display merge preview
    console.print()
    console.print("[bold]Merge Preview[/bold]")
    console.print(f"Patch: {patch_path.name}")
    console.print()
    
    # Low risk: PROGRESS.md
    if progress_entry:
        console.print("[green]Low Risk - PROGRESS.md:[/green]")
        console.print("  Will append session progress entry")
        console.print()
    
    # Medium risk: decisions, risks, questions
    if decisions:
        console.print("[yellow]Medium Risk - DECISIONS.md:[/yellow]")
        if reviewed_decisions_already_accepted:
            console.print(f"  {len(decisions)} candidate decisions already accepted via flg review")
        else:
            console.print(f"  {len(decisions)} candidate decisions (background processing pending)")
        for d in decisions[:3]:
            console.print(f"    - {d['content'][:60]}...")
        console.print()
    
    if risks or next_actions:
        console.print("[yellow]Candidate risks/actions remain in the patch until separately confirmed.[/yellow]")
        console.print("  They will not update SNAPSHOT.md during background merge.")
        console.print()
    
    if questions:
        console.print("[yellow]Medium Risk - Open Questions:[/yellow]")
        console.print(f"  {len(questions)} new open questions")
        console.print()
    
    # Dry run mode
    if dry_run:
        console.print("[dim]Dry run mode - no changes made[/dim]")
        console.print()
        return
    
    # Host-integrated flows can complete routine ledger maintenance without
    # turning the internal write step into a user-facing approval ceremony.
    if not yes and not Confirm.ask("Proceed with merge?"):
        console.print("[yellow]Merge cancelled.[/yellow]")
        return
    
    # Execute merge
    now = get_iso_now()
    merge_log = {
        "patch_id": "",
        "merged_files": [],
        "skipped_sections": [],
        "high_risk_sections": [],
        "timestamp": now,
    }
    
    merge_log["patch_id"] = merge_patch_id
    
    # 1. Append to PROGRESS.md (low risk)
    if progress_entry:
        progress_path = root / "PROGRESS.md"
        if progress_path.exists():
            progress_content = read_file_safe(progress_path)
            # Append before last line
            progress_content += f"\n\n{progress_entry}\n"
            progress_path.write_text(progress_content, encoding="utf-8")
            merge_log["merged_files"].append("PROGRESS.md")
            console.print("[green]✓ Appended to PROGRESS.md[/green]")
    
    # 2. High risk: decisions - generate report only
    if decisions:
        if reviewed_decisions_already_accepted:
            merge_log["skipped_sections"].append("Candidate decisions (already accepted via review)")
            console.print("[green]✓ Candidate decisions already accepted via flg review[/green]")
        else:
            merge_log["high_risk_sections"].append("Candidate decisions")
            console.print("[yellow]⚠ Candidate decisions require background processing[/yellow]")
            console.print("  Keep them pending until the host has sufficient source context")
    # 3. SNAPSHOT.md is formal state. Refresh it only after this merge, and
    # never surface unreviewed candidate decisions as confirmed judgments.
    from .closeout import _refresh_snapshot

    snapshot_decisions = decisions if reviewed_decisions_already_accepted else []
    if snapshot_decisions:
        # A candidate patch is evidence, not formal project state. Risks and
        # next actions need their own confirmation path before they can steer a
        # future agent through SNAPSHOT.md.
        _refresh_snapshot(root, snapshot_decisions, [], [], state)
        merge_log["merged_files"].append("SNAPSHOT.md")
        console.print("[green]✓ Refreshed SNAPSHOT.md from merged patch state[/green]")
    
    # 4. Update patch status
    # Find patch in state and mark as merged
    if state.get("pending_patches"):
        for p in state["pending_patches"]:
            if p.get("patch_id") == merge_log["patch_id"]:
                p["status"] = "merged"
                p["merged_at"] = now
                break

    # Keep the audit artifact's lifecycle in sync with state.json. Handoff and
    # Context Pack read patch headers so a state-only merge would resurrect a
    # closed patch as active work for the next host.
    _update_patch_file_status(
        patch_path,
        "merged",
        "Merged into formal project state by flg merge.",
    )
    save_state(root, state)
    
    # 5. Generate merge log
    merge_logs_dir = root / ".flg" / "merge_logs"
    merge_logs_dir.mkdir(parents=True, exist_ok=True)
    
    merge_log_content = f"""# Merge Log

patch_id: {merge_log['patch_id']}
source_patch: {patch_path.name}
merged_at: {now}
operator: user

## Merged Files

{chr(10).join(f'- {f}' for f in merge_log['merged_files']) if merge_log['merged_files'] else '- (none)'}

## Skipped Sections

{chr(10).join(f'- {s}' for s in merge_log['skipped_sections']) if merge_log['skipped_sections'] else '- (none)'}

## High Risk Sections (require background processing)

{chr(10).join(f'- {s}' for s in merge_log['high_risk_sections']) if merge_log['high_risk_sections'] else '- (none)'}

---

*Merged at {now}*
"""
    
    log_filename = f"{now.replace(':', '-')}-merge.md"
    log_path = merge_logs_dir / log_filename
    log_path.write_text(merge_log_content, encoding="utf-8")
    
    console.print()
    console.print(f"[bold green]✓ Merge complete[/bold green]")
    console.print(f"Merge log: {log_path}")
    console.print()
    
    if merge_log["high_risk_sections"]:
        console.print("[yellow]⚠ High risk sections require background processing:[/yellow]")
        for s in merge_log["high_risk_sections"]:
            console.print(f"  - {s}")
