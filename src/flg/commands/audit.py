"""flg audit command - Audit existing project directories."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown

from ..core.files import is_flg_project, read_file_safe
from ..core.evidence_quality import assess_evidence_basis
from ..templates import get_iso_now

console = Console()


# Required files for a complete FLG project
REQUIRED_FILES = [
    "PROJECT.md",
    "FRAMING.md",
    "DECISIONS.md",
    "SNAPSHOT.md",
    "PROGRESS.md",
]

# Optional files
OPTIONAL_FILES = [
    ".flg/CONTRACT.md",
    ".flg/state.json",
    ".flg/index.json",
]

# Generated dependencies and build outputs are not competing project documents.
IGNORED_AUDIT_DIRECTORIES = {
    ".flg",
    ".git",
    ".venv",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "venv",
}


def calculate_maturity(existing_files: list[str]) -> tuple[int, str]:
    """Calculate project maturity score (0-5)."""
    score = 0
    for f in REQUIRED_FILES:
        if f in existing_files:
            score += 1
    
    if score == 5:
        return score, "Complete"
    elif score >= 3:
        return score, "Partial"
    elif score >= 1:
        return score, "Basic"
    else:
        return score, "None"


def _parse_anchors_for_audit(root: Path) -> list[dict]:
    """Parse ANCHORS.md to extract anchor entries for conflict detection."""
    anchors_content = read_file_safe(root / "ANCHORS.md") or ""
    if not anchors_content:
        return []
    
    entries = []
    blocks = re.split(r"(?=^### )", anchors_content, flags=re.MULTILINE)
    
    for block in blocks:
        topic_match = re.match(r"^### (.+)", block, re.MULTILINE)
        if not topic_match:
            continue
        topic = topic_match.group(1).strip()
        if topic.startswith("[") and topic.endswith("]"):
            continue
        
        def _extract(field: str) -> str:
            m = re.search(rf"\*\*{re.escape(field)}:\*\*\s*(.+)", block)
            return m.group(1).strip() if m else ""
        
        file_path = _extract("File").strip("`")
        if file_path and not (file_path.startswith("(") and file_path.endswith(")")):
            entries.append({
                "topic": topic,
                "file": file_path,
                "role": _extract("Role"),
                "authority": _extract("Authority"),
            })
    
    return entries


def _resolve_anchor_path(root: Path, anchor_file: str) -> Path:
    """Resolve a ledger-relative or absolute anchor path for validation."""
    path = Path(anchor_file).expanduser()
    return path if path.is_absolute() else root / path


def _find_missing_anchors(root: Path, anchors: list[dict]) -> list[dict]:
    """Return authoritative anchors whose target path no longer exists."""
    return [
        anchor
        for anchor in anchors
        if anchor.get("authority") == "authoritative"
        and not _resolve_anchor_path(root, anchor["file"]).exists()
    ]


def _detect_multi_version_conflicts(root: Path, anchors: list[dict]) -> list[dict]:
    """Detect potential multi-version conflicts based on file naming patterns."""
    conflicts = []
    
    # Collect all doc files, excluding generated/internal directories and docs/.
    # docs/ is the user's free zone for project materials (见 CONTRACT.md Rule 13).
    # FLG does not audit docs/ — materials there are reference, not truth.
    all_docs = []
    for pattern in ("*.md", "*.docx", "*.html"):
        for f in root.rglob(pattern):
            rel = f.relative_to(root)
            if rel.parts and (rel.parts[0] == "docs" or any(part in IGNORED_AUDIT_DIRECTORIES for part in rel.parts[:-1])):
                continue
            all_docs.append(rel)
    
    # Group by similar names (fuzzy match on base name)
    from collections import defaultdict
    name_groups = defaultdict(list)
    
    for doc in all_docs:
        stem = doc.stem.lower()
        # Normalize: remove dates, versions, suffixes
        normalized = re.sub(r'[_-]?(v\d+|v\d+\.\d+|\d{4}[-_]?\d{2}[-_]?\d{2}|精简|完整|汇报版|技术版|基线版)', '', stem)
        normalized = normalized.strip('_- ')
        if normalized:
            name_groups[normalized].append(str(doc))
    
    # Find groups with multiple files (potential conflicts)
    for group_name, files in name_groups.items():
        if len(files) > 1:
            # Check if any file is an anchor
            anchored_files = [a["file"] for a in anchors]
            has_anchor = any(f in anchored_files for f in files)
            
            conflicts.append({
                "group": group_name,
                "files": files,
                "has_anchor": has_anchor,
                "risk": "low" if has_anchor else "high",
            })
    
    return conflicts


def audit_project(
    project_path: str = typer.Argument(".", help="Path to project directory"),
    report_only: bool = typer.Option(True, "--report-only", "-r", help="Only generate report, don't modify"),
    deep: bool = typer.Option(False, "--deep", "-d", help="Deep quality audit with LLM (requires API key)"),
) -> None:
    """Audit an existing project directory for FLG compatibility.

    Modes:
      - Default: check file structure, existence, and multi-version conflicts
      - Deep: check content quality with LLM (--deep flag)
    """
    root = Path(project_path).resolve()
    
    if not root.exists():
        console.print(f"[red]Path not found: {root}[/red]")
        raise typer.Exit(1)
    
    console.print()
    console.print(f"[bold]Auditing: {root}[/bold]")
    console.print()
    
    # Check if already a FLG project
    is_flg = is_flg_project(root)
    
    # Scan for files
    existing_files = []
    missing_files = []
    
    for f in REQUIRED_FILES:
        if (root / f).exists():
            existing_files.append(f)
        else:
            missing_files.append(f)
    
    # Check for optional files
    optional_existing = []
    for f in OPTIONAL_FILES:
        if (root / f).exists():
            optional_existing.append(f)
    
    # Check for Chinese-named files
    chinese_files = []
    for f in root.glob("*.md"):
        if any('\u4e00' <= c <= '\u9fff' for c in f.name):
            chinese_files.append(f.name)
    
    # Calculate maturity
    maturity_score, maturity_level = calculate_maturity(existing_files)
    
    # Display results
    table = Table(title="Project Audit Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")
    
    table.add_row("Is FLG Project", "✓ Yes" if is_flg else "✗ No", "")
    table.add_row("Maturity Score", f"{maturity_score}/5", maturity_level)
    
    for f in REQUIRED_FILES:
        status = "✓ exists" if f in existing_files else "✗ missing"
        style = "green" if f in existing_files else "red"
        table.add_row(f, f"[{style}]{status}[/{style}]", "")
    
    console.print(table)

    framing_content = read_file_safe(root / "FRAMING.md") or ""
    evidence_basis = assess_evidence_basis(framing_content)
    console.print()
    if evidence_basis["warning"]:
        console.print(f"[yellow]Evidence basis warning:[/yellow] {evidence_basis['message']}")
    else:
        console.print(f"[green]Evidence basis:[/green] {evidence_basis['label']}")
    
    # Display missing files
    if missing_files:
        console.print()
        console.print("[yellow]Missing Files:[/yellow]")
        for f in missing_files:
            console.print(f"  - {f}")
    
    # Display Chinese files
    if chinese_files:
        console.print()
        console.print("[yellow]Chinese-named Files (may cause encoding issues):[/yellow]")
        for f in chinese_files:
            console.print(f"  - {f}")
    
    # --- Multi-version conflict detection ---
    console.print()
    console.print("[bold]Multi-version Conflict Detection:[/bold]")
    
    anchors = _parse_anchors_for_audit(root)
    missing_anchors = _find_missing_anchors(root, anchors)
    conflicts = _detect_multi_version_conflicts(root, anchors)

    console.print()
    console.print("[bold]Anchor Health:[/bold]")
    if missing_anchors:
        console.print(f"  [red]{len(missing_anchors)} authoritative anchor(s) point to missing files.[/red]")
        for anchor in missing_anchors:
            console.print(f"    ✗ {anchor['topic']}: {anchor['file']}")
    elif anchors:
        console.print(f"  [green]✓ {len(anchors)} anchor(s) resolve to existing files.[/green]")
    else:
        console.print("  [yellow]No anchors defined.[/yellow]")
    
    if not conflicts:
        console.print("  [green]No multi-version conflicts detected.[/green]")
    else:
        for conflict in conflicts:
            risk_color = "red" if conflict["risk"] == "high" else "yellow"
            anchor_status = "✓ anchored" if conflict["has_anchor"] else "✗ no anchor"
            
            console.print(f"\n  [{risk_color}]{conflict['group']}[/{risk_color}] ({anchor_status})")
            for f in conflict["files"]:
                is_anchored = f in [a["file"] for a in anchors]
                marker = "◆" if is_anchored else "◇"
                console.print(f"    {marker} {f}")
            
            if conflict["risk"] == "high":
                console.print(f"    [red]⚠ 高风险：多版本无锚点，Agent可能混淆哪个是真相[/red]")
                console.print(f"    [dim]建议：在 ANCHORS.md 中指定权威版本[/dim]")
    
    # Display recommendations
    console.print()
    console.print("[bold]Recommendations:[/bold]")
    
    if not is_flg:
        console.print("  1. Run [cyan]flg init[/cyan] to initialize FLG project structure")
    
    if missing_files:
        console.print(f"  2. Create missing core files: {', '.join(missing_files)}")
    
    if chinese_files:
        console.print("  3. Consider renaming Chinese files to English for cross-platform compatibility")
    
    high_risk = [c for c in conflicts if c["risk"] == "high"]
    if high_risk:
        console.print(f"  4. [red]Fix {len(high_risk)} high-risk multi-version conflict(s)[/red]")
        console.print("     Edit ANCHORS.md to specify authoritative versions")

    if missing_anchors:
        console.print(f"  5. [red]Repair {len(missing_anchors)} missing authoritative anchor(s)[/red]")
        console.print("     Update ANCHORS.md or restore the referenced file before relying on handoff output")

    if maturity_score == 5 and not high_risk and not missing_anchors:
        console.print("  [green]Project has complete core files and no conflicts. Ready for FLG workflow.[/green]")
    
    # Generate report if requested
    if report_only:
        console.print()
        console.print("[dim]Report-only mode. No changes made.[/dim]")
    
    # Deep audit mode
    if deep:
        console.print()
        console.print("[bold blue]Deep quality audit mode[/bold blue]")
        console.print("[dim]This feature is planned but not yet implemented.[/dim]")
        console.print()
        console.print("Planned capabilities:")
        console.print("  1. Check SNAPSHOT.md content quality")
        console.print("  2. Check FRAMING.md completeness")
        console.print("  3. Check DECISIONS.md 9-field integrity")
        console.print("  4. Check PROGRESS.md milestone coverage")
        console.print("  5. Cross-validate information consistency")
        console.print()
        console.print("To enable deep audit:")
        console.print("  1. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        console.print("  2. Run: [cyan]flg audit --deep[/cyan]")
        console.print()
        console.print("[yellow]Note: Deep audit will be implemented in a future version.[/yellow]")
        console.print("[dim]For now, use flg-quality-audit skill for manual deep audit.[/dim]")
    
    console.print()
