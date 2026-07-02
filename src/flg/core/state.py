"""State management for Framing Ledger."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .. import __version__


STATE_FILE = ".flg/state.json"


def create_initial_state(project_name: str, project_id: str = "") -> dict:
    """Create initial state dictionary."""
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "project_id": project_id or project_name.lower().replace(" ", "-"),
        "project_name": project_name,
        "flg_version": __version__,
        "created_at": now,
        "current_stage": "initialized",
        "last_closeout_at": None,
        "pending_patches": [],
        "active_agent": None,
        "dirty_files": [],
        "last_snapshot_hash": None,
    }


def load_state(root: Path) -> Optional[dict]:
    """Load state from .flg/state.json."""
    state_path = root / STATE_FILE
    if not state_path.exists():
        return None
    return json.loads(state_path.read_text(encoding="utf-8"))


def save_state(root: Path, state: dict) -> None:
    """Save state to .flg/state.json."""
    state_path = root / STATE_FILE
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def update_state(root: Path, **kwargs) -> dict:
    """Update state with given key-value pairs."""
    state = load_state(root)
    if state is None:
        raise ValueError("No FLG project found. Run 'flg init' first.")
    state.update(kwargs)
    save_state(root, state)
    return state


def add_pending_patch(
    root: Path,
    patch_id: str,
    patch_path: str,
    risk_level: str,
    source_command: str = "unknown",
) -> None:
    """Add a pending patch to state."""
    state = load_state(root)
    if state is None:
        return
    state["pending_patches"].append({
        "patch_id": patch_id,
        "path": patch_path,
        "risk_level": risk_level,
        "source_command": source_command,
        "status": "pending_review",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    save_state(root, state)
