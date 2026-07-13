"""flg frame command - Check framing completeness."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..core.files import is_flg_project, read_file_safe
from ..core.patches import create_patch, generate_patch_id
from ..core.state import add_pending_patch, load_state
from ..templates import FRAME_PATCH_MD, get_iso_now

console = Console()

# Required fields in FRAMING.md
# Explicit Requirements and Real Needs Hypothesis ship as H3 (###) under
# "## Requirements" in the default template, but users often write them as
# H2 (##). Accept either level so frame doesn't false-positive on H2 usage.
REQUIRED_FIELDS = [
    ("Problem Statement", r"##\s+Problem\s+Statement"),
    ("Explicit Requirements", r"#{2,3}\s+Explicit\s+Requirements"),
    ("Real Needs Hypothesis", r"#{2,3}\s+Real\s+Needs\s+Hypothesis"),
    ("Goals", r"##\s+Goals"),
    ("Non-Goals", r"##\s+Non-Goals"),
    ("User Objects", r"##\s+User\s+Objects"),
    ("Review Objects", r"##\s+Review\s+Objects"),
    ("Success Criteria", r"##\s+Success\s+Criteria"),
    ("Constraints", r"##\s+Constraints"),
    ("Open Questions", r"##\s+Open\s+Questions"),
]

# Suggested questions for each field
FIELD_QUESTIONS = {
    "Problem Statement": [
        "What specific problem is this project solving?",
        "Who is experiencing this problem?",
        "What happens if this problem is not solved?",
    ],
    "Explicit Requirements": [
        "What did the client/stakeholder explicitly ask for?",
        "What are the stated deliverables?",
        "What are the stated deadlines?",
    ],
    "Real Needs Hypothesis": [
        "What do you think the real need is behind the explicit request?",
        "What would success look like for the client?",
        "What is the client not saying?",
    ],
    "Goals": [
        "What are the top 3 goals for this project?",
        "How will you measure success?",
        "What is the primary outcome?",
    ],
    "Non-Goals": [
        "What is explicitly out of scope?",
        "What are you choosing not to do?",
        "What would be nice but is not required?",
    ],
    "User Objects": [
        "Who is the end user?",
        "Who is the decision maker?",
        "Who are the reviewers?",
    ],
    "Review Objects": [
        "Who will evaluate the final deliverable?",
        "What are their criteria?",
        "What is their priority?",
    ],
    "Success Criteria": [
        "How will you know this project is successful?",
        "What specific outcomes indicate success?",
        "What metrics matter?",
    ],
    "Constraints": [
        "What are the time constraints?",
        "What are the budget constraints?",
        "What are the resource constraints?",
        "What are the technical constraints?",
    ],
    "Open Questions": [
        "What questions need to be answered before proceeding?",
        "What information is missing?",
        "What assumptions need to be validated?",
    ],
}


def check_field_content(content: str, field_name: str, pattern: str) -> bool:
    """Check if a field has meaningful content (not just placeholder)."""
    match = re.search(pattern, content, re.IGNORECASE)
    if not match:
        return False
    
    # Get content after the heading
    start = match.end()
    next_heading = re.search(r"^##\s+", content[start:], re.MULTILINE)
    if next_heading:
        field_content = content[start:start + next_heading.start()]
    else:
        field_content = content[start:]
    
    # Check if it's just placeholder
    placeholders = ["(to be defined)", "(to be filled)", "(to be confirmed)", 
                    "(to be identified)", "(none yet)", "- (to be"]
    
    stripped = field_content.strip()
    if not stripped:
        return False
    
    for placeholder in placeholders:
        if placeholder in stripped:
            return False
    
    return True


def frame_project() -> None:
    """Check FRAMING.md completeness and generate frame patch if needed."""
    root = Path.cwd()
    
    # Check if this is a FLG project
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)
    
    # Load state
    state = load_state(root)
    project_name = state["project_name"] if state else "Unknown"
    
    # Read FRAMING.md
    framing_path = root / "FRAMING.md"
    framing_content = read_file_safe(framing_path)
    
    if framing_content is None:
        console.print("[red]FRAMING.md not found. Run 'flg init' first.[/red]")
        raise typer.Exit(1)
    
    # Check each required field
    missing_fields = []
    filled_fields = []
    
    for field_name, pattern in REQUIRED_FIELDS:
        if check_field_content(framing_content, field_name, pattern):
            filled_fields.append(field_name)
        else:
            missing_fields.append(field_name)
    
    # Display results
    console.print()
    
    if not missing_fields:
        console.print("[bold green]✓ FRAMING.md is complete![/bold green]")
        console.print(f"All {len(filled_fields)} required fields are filled.")
        console.print()
        console.print("You can proceed with [cyan]flg closeout[/cyan] after your session.")
        return
    
    # Generate patch
    console.print(f"[yellow]Found {len(missing_fields)} missing fields in FRAMING.md[/yellow]")
    console.print()
    
    # Build missing fields list
    missing_fields_text = ""
    for field in missing_fields:
        missing_fields_text += f"- **{field}**\n"
    
    # Build suggested questions
    questions_text = ""
    for field in missing_fields:
        questions_text += f"\n### {field}\n\n"
        for q in FIELD_QUESTIONS.get(field, []):
            questions_text += f"- {q}\n"
    
    # Build draft content
    draft_text = ""
    for field in missing_fields:
        draft_text += f"\n## {field}\n\n(to be filled)\n"
    
    # Create patch
    patch_id = generate_patch_id("frame")
    now = get_iso_now()
    
    patch_content = FRAME_PATCH_MD.format(
        patch_id=patch_id,
        project_name=project_name,
        generated_at=now,
        summary=f"FRAMING.md has {len(filled_fields)}/{len(REQUIRED_FIELDS)} fields filled. "
                f"{len(missing_fields)} fields need attention.",
        missing_fields=missing_fields_text,
        suggested_questions=questions_text,
        draft_content=draft_text,
    )
    
    patch_path = create_patch(root, patch_id, patch_content)
    
    # Update state
    add_pending_patch(root, patch_id, str(patch_path), "medium", source_command="flg frame")
    
    # Display results
    table = Table(title="FRAMING.md Analysis")
    table.add_column("Field", style="cyan")
    table.add_column("Status", style="green")
    
    for field in filled_fields:
        table.add_row(field, "✓ filled")
    for field in missing_fields:
        table.add_row(field, "✗ missing")
    
    console.print(table)
    console.print()
    console.print(f"[yellow]Patch generated:[/yellow] {patch_path}")
    console.print()
    console.print("Next steps:")
    console.print("  1. Review the patch file")
    console.print("  2. Answer the suggested questions")
    console.print("  3. Update FRAMING.md with your answers")
    console.print("  4. Run [cyan]flg frame[/cyan] again to verify")
