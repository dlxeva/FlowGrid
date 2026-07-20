"""State management for FlowGrid state files."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from .. import __version__


STATE_FILE = ".flg/state.json"
STATE_SCHEMA_VERSION = "1"

# ── Core Schema ──────────────────────────────────────────────────────────
# Fields that FLG CLI depends on. Must be present in every state.json.
# When schema_version bumps, this set may grow — never shrinks without a
# migration path.

STATE_CORE_KEYS: frozenset[str] = frozenset({
    "schema_version",
    "project_id",
    "project_name",
    "flg_version",
    "created_at",
    "updated_at",
    "current_stage",
    "last_closeout_at",
    "pending_patches",
    "next_actions",
    "active_agent",
    "dirty_files",
    "last_snapshot_hash",
})

# ── Variant Field Map ────────────────────────────────────────────────────
# Maps core field names → alternative keys found in legacy/custom states.
# normalize_state_dict() uses this to read older schemas without forcing a
# rewrite.

STATE_VARIANT_MAP: dict[str, list[str]] = {
    "project_name": ["name"],
    "created_at":   ["created", "date_created"],
    "updated_at":   ["updated", "last_updated"],
    "current_stage": ["phase", "current_phase", "phase_status", "status"],
    "flg_version":  ["version"],
}

# Fields that are safe to auto-generate when missing (don't affect project
# semantics).
STATE_AUTOFILL_DEFAULTS: dict[str, object] = {
    "schema_version": "1",
    "last_closeout_at": None,
    "pending_patches": [],
    "next_actions": [],
    "active_agent": None,
    "dirty_files": [],
    "last_snapshot_hash": None,
}


def create_initial_state(project_name: str, project_id: str = "", language: str = "zh") -> dict:
    """Create initial state dictionary."""
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "project_id": project_id or project_name.lower().replace(" ", "-"),
        "project_name": project_name,
        "language": language,
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
    try:
        raw_state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"State file is corrupt: {state_path}") from exc
    return normalize_state_dict(raw_state)


def save_state(root: Path, state: dict) -> None:
    """Atomically save state to .flg/state.json.

    ``os.replace`` prevents a process crash from leaving a truncated JSON file.
    Higher-level multi-file operations still need a transaction boundary, but
    every individual state write is now all-or-nothing.
    """
    state_path = root / STATE_FILE
    state_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_state_dict(state)
    normalized["updated_at"] = datetime.now().isoformat(timespec="seconds")
    payload = json.dumps(normalized, indent=2, ensure_ascii=False)
    fd, temp_name = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=state_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, state_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


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
    if any(item.get("patch_id") == patch_id for item in state["pending_patches"]):
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


def get_state_schema_info(state: dict) -> dict:
    """Return schema classification for a state dict.

    Returns a dict with:
      - core_fields: keys that match STATE_CORE_KEYS
      - extension_fields: keys not in core (project-specific)
      - legacy_key_mappings: variant→canonical mappings used
      - missing_core: core keys absent (after autofill)
      - schema_health: "ok" | "legacy" | "degraded"
    """
    core = set(STATE_CORE_KEYS)
    actual = set(state.keys())
    extension = actual - core

    # Detect variant mappings
    legacy_mappings = {}
    for canonical, variants in STATE_VARIANT_MAP.items():
        for v in variants:
            if v in state and canonical not in state:
                legacy_mappings[v] = canonical

    # Check missing core (accounting for variant fallback)
    missing_core = set()
    for ck in core:
        if ck in state:
            continue
        # Check if any variant covers it
        variants = STATE_VARIANT_MAP.get(ck, [])
        if not (actual & set(variants)):
            if ck in STATE_AUTOFILL_DEFAULTS:
                continue  # autofill-safe
            missing_core.add(ck)

    if not missing_core and not legacy_mappings:
        health = "ok"
    elif not missing_core:
        health = "legacy"
    else:
        health = "degraded"

    return {
        "core_fields": sorted(core & actual),
        "extension_fields": sorted(extension),
        "legacy_key_mappings": legacy_mappings,
        "missing_core": sorted(missing_core),
        "schema_health": health,
        "schema_version": state.get("schema_version", "none"),
        "total_fields": len(actual),
        "core_count": len(core & actual),
        "extension_count": len(extension),
    }
