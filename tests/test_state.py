"""Tests for state compatibility and normalization."""

import json
from pathlib import Path

from flg.core.state import load_state, save_state


def test_load_state_normalizes_legacy_state_schema(tmp_path):
    """Legacy skill-written state files should normalize into the common schema."""
    flg_dir = tmp_path / ".flg"
    flg_dir.mkdir()
    legacy_state = {
        "project_name": "Legacy Project",
        "created": "2026-07-01",
        "updated": "2026-07-02",
        "phase": "v0定义阶段",
        "status": "active",
        "version": "0.1.0",
        "linked_projects": [{"name": "Example"}],
    }
    (flg_dir / "state.json").write_text(json.dumps(legacy_state, ensure_ascii=False), encoding="utf-8")

    state = load_state(tmp_path)
    assert state is not None
    assert state["project_name"] == "Legacy Project"
    assert state["created_at"] == "2026-07-01"
    assert state["updated_at"] == "2026-07-02"
    assert state["current_stage"] == "v0定义阶段"
    assert state["flg_version"] == "0.1.0"
    assert state["pending_patches"] == []
    assert state["linked_projects"] == [{"name": "Example"}]


def test_save_state_preserves_custom_fields(tmp_path):
    """Saving normalized state should keep project-specific extensions."""
    flg_dir = tmp_path / ".flg"
    flg_dir.mkdir()
    state = {
        "project_name": "Custom Project",
        "created_at": "2026-07-01T00:00:00",
        "updated_at": "2026-07-01T00:00:00",
        "current_stage": "active",
        "pending_patches": [],
        "brand_identity": {"type": "lab"},
    }

    save_state(tmp_path, state)
    reloaded = load_state(tmp_path)
    assert reloaded is not None
    assert reloaded["project_name"] == "Custom Project"
    assert reloaded["brand_identity"] == {"type": "lab"}
    assert reloaded["schema_version"] == "1"
