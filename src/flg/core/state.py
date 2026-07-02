"""State management for FlowGrid state files."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .. import __version__


STATE_FILE = ".flg/state.json"
STATE_SCHEMA_VERSION = "1"


def create_initial_state(project_name: str, project_id: str = "") -> dict:
    """Create initial state dictionary."""
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "project_id": project_id or project_name.lower().replace(" ", "-"),
        "project_name": project_name,
        "flg_version": __version__,
        "created_at": now,
        "updated_at": now,
        "current_stage": "initialized",
        "last_closeout_at": None,
        "pending_patches": [],
        "next_actions": [],
        "active_agent": None,
        "dirty_files": [],
        "last_snapshot_hash": None,
    }


def normalize_state_dict(raw_state: dict) -> dict:
    """Normalize legacy/custom state files to a minimal common schema.

    Keep unknown keys intact so project-specific extensions survive.
    """
    now = datetime.now().isoformat(timespec="seconds")
    state = dict(raw_state)

    project_name = (
        state.get("project_name")
        or state.get("name")
        or "Unknown"
    )
    created_at = (
        state.get("created_at")
        or state.get("created")
        or state.get("date_created")
        or now
    )
    updated_at = (
        state.get("updated_at")
        or state.get("updated")
        or state.get("last_updated")
        or created_at
    )
    current_stage = (
        state.get("current_stage")
        or state.get("phase")
        or state.get("current_phase")
        or state.get("phase_status")
        or state.get("status")
        or "unknown"
    )
    pending_patches = state.get("pending_patches") or []
    if not isinstance(pending_patches, list):
        pending_patches = []
    next_actions = state.get("next_actions") or []
    if isinstance(next_actions, str):
        next_actions = [next_actions]
    elif not isinstance(next_actions, list):
        next_actions = []

    normalized_core = {
        "schema_version": state.get("schema_version", STATE_SCHEMA_VERSION),
        "project_id": state.get("project_id") or project_name.lower().replace(" ", "-"),
        "project_name": project_name,
        "flg_version": state.get("flg_version") or state.get("version") or __version__,
        "created_at": created_at,
        "updated_at": updated_at,
        "current_stage": current_stage,
        "last_closeout_at": state.get("last_closeout_at"),
        "pending_patches": pending_patches,
        "next_actions": next_actions,
        "active_agent": state.get("active_agent"),
        "dirty_files": state.get("dirty_files", []),
        "last_snapshot_hash": state.get("last_snapshot_hash"),
    }

    state.update(normalized_core)
    return state


def load_state(root: Path) -> Optional[dict]:
    """Load state from .flg/state.json."""
    state_path = root / STATE_FILE
    if not state_path.exists():
        return None
    raw_state = json.loads(state_path.read_text(encoding="utf-8"))
    return normalize_state_dict(raw_state)


def save_state(root: Path, state: dict) -> None:
    """Save state to .flg/state.json."""
    state_path = root / STATE_FILE
    state_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_state_dict(state)
    normalized["updated_at"] = datetime.now().isoformat(timespec="seconds")
    state_path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")


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
    state.setdefault("pending_patches", [])
    state["pending_patches"].append({
        "patch_id": patch_id,
        "path": patch_path,
        "risk_level": risk_level,
        "source_command": source_command,
        "status": "pending_review",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    save_state(root, state)
