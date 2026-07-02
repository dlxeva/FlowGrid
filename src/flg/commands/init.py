"""flg init command - Initialize a FlowGrid project."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..core.files import ensure_dir, is_flg_project, safe_write
from ..core.state import create_initial_state, save_state
from ..templates import (
    ANCHORS_MD,
    CONSTRAINTS_MD,
    CONTRACT_MD,
    DECISIONS_MD,
    FRAMING_MD,
    GOAL_EVOLUTION_MD,
    LESSONS_LEARNED_MD,
    PROGRESS_MD,
    PROJECT_MD,
    RATIONALE_TRAIL_MD,
    ROLE_TEMPLATES,
    SNAPSHOT_MD,
    get_iso_now,
)

console = Console()


def init_project(
    project_name: str = typer.Argument(..., help="Project name"),
    project_type: str = typer.Option("proposal", "--type", "-t", help="Project type"),
    client: str = typer.Option("", "--client", "-c", help="Client or sponsor"),
    background: str = typer.Option("", "--background", "-b", help="Project background"),
    template: Optional[str] = typer.Option(None, "--template", help="Optional role template: strategy, marketing, operations, solution"),
) -> None:
    """Initialize a new FlowGrid project in the current directory."""
    root = Path.cwd()
    
    # Check if already a FLG project
    if is_flg_project(root):
        console.print("[yellow]This directory is already a FLG project.[/yellow]")
        console.print("Use 'flg frame' or 'flg closeout' to continue.")
        raise typer.Exit(0)
    
    now = get_iso_now()
    results = []
    template_profile = None
    if template:
        normalized_template = template.lower().strip()
        template_profile = ROLE_TEMPLATES.get(normalized_template)
        if template_profile is None:
            console.print(f"[red]Unknown template: {template}[/red]")
            console.print("[dim]Supported templates: strategy, marketing, operations, solution[/dim]")
            raise typer.Exit(1)
        project_type = template_profile["project_type"]
    
    # Create core directories
    for subdir in [".flg/patches", ".flg/sessions", ".flg/memory"]:
        ensure_dir(root / subdir)
        results.append((f".flg/{subdir.split('/')[-1]}/", "created"))
    
    # Create PROJECT.md
    project_content = PROJECT_MD.format(
        project_name=project_name,
        project_type=project_type,
        client=client or "(to be confirmed)",
        current_stage="initialized",
        deliverables="(to be defined)",
        timeline="(to be defined)",
        constraints=(template_profile["constraints"] if template_profile else "(to be defined)"),
        background=background or "(to be filled)",
        created_at=now,
        updated_at=now,
    )
    written = safe_write(root / "PROJECT.md", project_content)
    results.append(("PROJECT.md", "created" if written else "skipped"))
    
    # Create FRAMING.md
    framing_content = FRAMING_MD.format(
        problem_statement="(to be defined)",
        explicit_requirements="(to be defined)",
        real_needs="(to be hypothesized)",
        goals="(to be defined)",
        non_goals="(to be defined)",
        user_objects="(to be defined)",
        review_objects="(to be defined)",
        success_criteria="(to be defined)",
        constraints="(to be defined)",
        open_questions="- (to be identified)",
        created_at=now,
        updated_at=now,
    )
    if template_profile:
        framing_content = FRAMING_MD.format(
            problem_statement=template_profile["problem_statement"],
            explicit_requirements=template_profile["explicit_requirements"],
            real_needs=template_profile["real_needs"],
            goals=template_profile["goals"],
            non_goals=template_profile["non_goals"],
            user_objects=template_profile["user_objects"],
            review_objects=template_profile["review_objects"],
            success_criteria=template_profile["success_criteria"],
            constraints=template_profile["constraints"],
            open_questions=template_profile["open_questions"],
            created_at=now,
            updated_at=now,
        )
    written = safe_write(root / "FRAMING.md", framing_content)
    results.append(("FRAMING.md", "created" if written else "skipped"))
    
    # Create DECISIONS.md
    decisions_content = DECISIONS_MD.format(created_at=now, updated_at=now)
    written = safe_write(root / "DECISIONS.md", decisions_content)
    results.append(("DECISIONS.md", "created" if written else "skipped"))
    
    # Create SNAPSHOT.md
    snapshot_content = SNAPSHOT_MD.format(
        updated_at=now,
        current_stage="Initialized - needs framing",
        current_goal=f"Define project scope and goals for {project_name}",
        judgments="- (none yet)",
        confirmed="- Project initialized",
        unconfirmed="- Everything else",
        risks="- (none identified yet)",
        next_action="Run 'flg frame' to define project goals and boundaries",
    )
    written = safe_write(root / "SNAPSHOT.md", snapshot_content)
    results.append(("SNAPSHOT.md", "created" if written else "skipped"))
    
    # Create PROGRESS.md
    progress_content = PROGRESS_MD.format(created_at=now, updated_at=now)
    written = safe_write(root / "PROGRESS.md", progress_content)
    results.append(("PROGRESS.md", "created" if written else "skipped"))

    goal_evolution_content = GOAL_EVOLUTION_MD.format(created_at=now, updated_at=now)
    if template_profile:
        goal_evolution_content = GOAL_EVOLUTION_MD.format(created_at=now, updated_at=now).replace(
            "<!-- 复制以下模板，每次目标变化一条 -->",
            f"<!-- 复制以下模板，每次目标变化一条 -->\n\n{template_profile['goal_evolution']}"
        )
    written = safe_write(root / "GOAL_EVOLUTION.md", goal_evolution_content)
    results.append(("GOAL_EVOLUTION.md", "created" if written else "skipped"))

    constraints_content = CONSTRAINTS_MD.format(created_at=now, updated_at=now)
    if template_profile:
        constraints_content = CONSTRAINTS_MD.format(created_at=now, updated_at=now).replace(
            "<!-- 复制以下模板，每条约束一个 -->",
            f"<!-- 复制以下模板，每条约束一个 -->\n\n{template_profile['constraint_block']}"
        )
    written = safe_write(root / "CONSTRAINTS.md", constraints_content)
    results.append(("CONSTRAINTS.md", "created" if written else "skipped"))
    
    # Create .flg/CONTRACT.md
    written = safe_write(root / ".flg" / "CONTRACT.md", CONTRACT_MD)
    results.append((".flg/CONTRACT.md", "created" if written else "skipped"))

    # Create rationale/ directory and RATIONALE_TRAIL.md
    ensure_dir(root / "rationale")
    results.append(("rationale/", "created"))
    rationale_content = RATIONALE_TRAIL_MD.format(created_at=now, updated_at=now)
    written = safe_write(root / "RATIONALE_TRAIL.md", rationale_content)
    results.append(("RATIONALE_TRAIL.md", "created" if written else "skipped"))
    
    # Create LESSONS_LEARNED.md
    lessons_content = LESSONS_LEARNED_MD.format(created_at=now, updated_at=now)
    written = safe_write(root / "LESSONS_LEARNED.md", lessons_content)
    results.append(("LESSONS_LEARNED.md", "created" if written else "skipped"))
    
    # Create ANCHORS.md
    anchors_content = ANCHORS_MD.format(created_at=now, updated_at=now)
    written = safe_write(root / "ANCHORS.md", anchors_content)
    results.append(("ANCHORS.md", "created" if written else "skipped"))
    
    # Create .flg/state.json
    state = create_initial_state(project_name)
    state_path = root / ".flg" / "state.json"
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    results.append((".flg/state.json", "created"))
    
    # Create .flg/index.json
    index = {"files": [], "last_indexed_at": now}
    index_path = root / ".flg" / "index.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    results.append((".flg/index.json", "created"))
    
    # Display results
    console.print()
    console.print(f"[bold green]✓ FlowGrid project initialized: {project_name}[/bold green]")
    console.print()
    
    table = Table(title="Files Created")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")
    
    for filename, status in results:
        table.add_row(filename, status)
    
    console.print(table)
    console.print()
    console.print("Next steps:")
    console.print("  1. Edit [cyan]FRAMING.md[/cyan] to define your project")
    console.print("  2. Review [cyan]GOAL_EVOLUTION.md[/cyan] and [cyan]CONSTRAINTS.md[/cyan]")
    console.print("  3. Run [cyan]flg frame[/cyan] to check framing completeness")
    console.print("  4. Run [cyan]flg closeout --transcript <file>[/cyan] to close a session")
