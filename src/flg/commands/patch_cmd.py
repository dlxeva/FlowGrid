"""flg patch command - Manage patch lifecycle (supersede / discard).

发现 2: previously the only patch lifecycle transitions were
pending_review → merged (via `flg merge`). Stale patches — e.g. a
frame patch generated before FRAMING.md was rewritten by hand — had
no official retirement path. Users had to hand-edit state.json to
mark them superseded, which is error-prone.

This adds two transitions:
  flg patch supersede <patch_id>  — superseded by a newer patch
  flg patch discard  <patch_id>  — rejected / discarded

Both update state.json status AND the status: line inside the patch
file, so `flg status` (which scans both) consistently hides them
from the pending-review warning (见发现 16/4).
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..core.files import is_flg_project, read_file_safe
from ..core.state import load_state, save_state

console = Console()

# Valid lifecycle transitions: what status a patch must be in to apply
# supersede/discard. We allow acting on pending_review and unknown
# (orphan patches not in state.json). Acting on already-merged/rejected
# patches is allowed but warns, since the user may be correcting a mistake.
_ACTIVE_STATUSES = {"pending_review", "unknown", ""}


def _resolve_patch(root: Path, patch_id: str) -> Optional[Path]:
    """Find a patch file by patch_id, filename, or path, in .flg/patches/.

    Accepts:
    - Full path (e.g. ".flg/patches/closeout-xxx.patch.md")
    - Filename (e.g. "closeout-xxx.patch.md")
    - Patch ID (e.g. "closeout-xxx")
    """
    patches_dir = root / ".flg" / "patches"
    if not patches_dir.exists():
        return None

    # 1. If the input itself is an existing path, use it directly
    as_path = Path(patch_id)
    if as_path.exists():
        return as_path

    # 2. Try exact filename match in .flg/patches/
    candidates = [
        patches_dir / patch_id,
        patches_dir / f"{patch_id}.patch.md",
    ]
    for c in candidates:
        if c.exists():
            return c

    # 3. Search by patch_id field inside file content
    for f in patches_dir.glob("*.patch.md"):
        content = read_file_safe(f)
        if content:
            for line in content.split("\n"):
                if line.startswith("patch_id:"):
                    if line.split(":", 1)[1].strip() == patch_id:
                        return f
                    break
    return None


def _update_patch_file_status(patch_path: Path, new_status: str, reason: str) -> None:
    """Update the status: line inside a patch file.

    Also appends a lifecycle note so the audit trail is visible in the
    patch file itself, not just in state.json.
    """
    content = read_file_safe(patch_path)
    if not content:
        return

    now = datetime.now().isoformat(timespec="seconds")

    # Replace the first status: line (frontmatter)
    updated = re.sub(
        r"^status:\s*.+$",
        f"status: {new_status}",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    # Append a lifecycle trail at the end
    trail = f"\n---\n\n## Lifecycle Note\n\n- **{new_status}** at {now}"
    if reason:
        trail += f"\n- **Reason:** {reason}"
    trail += "\n"

    patch_path.write_text(updated.rstrip() + trail, encoding="utf-8")


def _update_state_status(root: Path, patch_id: str, new_status: str) -> bool:
    """Update a patch's status in state.json. Returns True if found."""
    state = load_state(root)
    if not state:
        return False

    found = False
    for p in state.get("pending_patches", []):
        if p.get("patch_id") == patch_id:
            p["status"] = new_status
            p[f"{new_status}_at"] = datetime.now().isoformat(timespec="seconds")
            found = True
            break

    if found:
        save_state(root, state)
    return found


def patch_supersede(
    patch_id: str = typer.Argument(..., help="Patch ID or filename to supersede"),
    reason: str = typer.Option("", "--reason", "-r", help="Why this patch is superseded"),
) -> None:
    """Mark a patch as superseded (replaced by a newer patch)."""
    _apply_lifecycle(patch_id, "superseded", reason)


def patch_discard(
    patch_id: str = typer.Argument(..., help="Patch ID or filename to discard"),
    reason: str = typer.Option("", "--reason", "-r", help="Why this patch is discarded"),
) -> None:
    """Mark a patch as discarded (rejected / no longer relevant)."""
    _apply_lifecycle(patch_id, "rejected", reason)


def _apply_lifecycle(patch_id: str, new_status: str, reason: str) -> None:
    root = Path.cwd()

    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    patch_path = _resolve_patch(root, patch_id)
    if patch_path is None:
        console.print(f"[red]Patch not found: {patch_id}[/red]")
        console.print("[dim]Checked .flg/patches/ by filename and patch_id field.[/dim]")
        raise typer.Exit(1)

    # Read current status from the patch file
    content = read_file_safe(patch_path) or ""
    current_status = "unknown"
    actual_patch_id = patch_id
    for line in content.split("\n"):
        if line.startswith("patch_id:") and actual_patch_id == patch_id:
            actual_patch_id = line.split(":", 1)[1].strip()
        if line.startswith("status:"):
            current_status = line.split(":", 1)[1].strip()
            break

    # Warn if acting on an already-closed patch
    if current_status in {"merged", "rejected", "superseded"}:
        console.print(
            f"[yellow]⚠ Patch is already {current_status}. "
            f"Updating to {new_status} anyway.[/yellow]"
        )

    # Update both state.json and the patch file
    in_state = _update_state_status(root, actual_patch_id, new_status)
    _update_patch_file_status(patch_path, new_status, reason)

    console.print()
    console.print(f"[bold green]✓ Patch marked as {new_status}[/bold green]")
    console.print(f"  Patch: {patch_path.name}")
    console.print(f"  Previous status: {current_status}")
    if not in_state:
        console.print("  [dim](patch was not in state.json — file updated only)[/dim]")
    if reason:
        console.print(f"  Reason: {reason}")
    console.print()
    console.print(
        "[dim]This patch will no longer trigger the 'pending patches' warning in `flg status`.[/dim]"
    )
