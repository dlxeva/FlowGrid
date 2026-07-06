"""Tests for state compatibility and normalization."""

import json
from pathlib import Path

from flg.core.state import load_state, save_state, get_state_schema_info, STATE_CORE_KEYS


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


def test_get_state_schema_info_standard_state():
    """A standard CLI-created state should report 'ok' health."""
    state = {
        "schema_version": "1",
        "project_id": "test-proj",
        "project_name": "Test Project",
        "flg_version": "0.2.1",
        "created_at": "2026-07-01T00:00:00",
        "updated_at": "2026-07-01T00:00:00",
        "current_stage": "active",
        "last_closeout_at": None,
        "pending_patches": [],
        "next_actions": [],
        "active_agent": None,
        "dirty_files": [],
        "last_snapshot_hash": None,
    }
    info = get_state_schema_info(state)
    assert info["schema_health"] == "ok"
    assert info["core_count"] == len(STATE_CORE_KEYS)
    assert info["extension_count"] == 0
    assert info["legacy_key_mappings"] == {}
    assert info["missing_core"] == []


def test_get_state_schema_info_legacy_with_variants():
    """A legacy state with variant field names should report 'legacy' health."""
    state = {
        "project_name": "Legacy",
        "created": "2026-06-01",
        "updated": "2026-06-02",
        "status": "active",
        "phase": "planning",
        "version": "0.1.0",
        "project_id": "legacy-proj",
        "pending_patches": [],
        "next_actions": [],
        "custom_field": "still here",
    }
    info = get_state_schema_info(state)
    assert info["schema_health"] == "legacy"
    assert info["legacy_key_mappings"] != {}
    assert "created" in info["legacy_key_mappings"]
    assert info["legacy_key_mappings"]["created"] == "created_at"
    assert "custom_field" in info["extension_fields"]
    assert info["missing_core"] == []


def test_get_state_schema_info_degraded_missing_critical():
    """A state missing non-autofillable core fields should report 'degraded'."""
    state = {
        "project_name": "Broken",
        "project_id": "broken",
        "schema_version": "1",
        "flg_version": "0.2.1",
        # missing: created_at, updated_at, current_stage
    }
    info = get_state_schema_info(state)
    assert info["schema_health"] == "degraded"
    assert "created_at" in info["missing_core"]
    assert "updated_at" in info["missing_core"]
    assert "current_stage" in info["missing_core"]


def test_get_state_schema_info_extension_fields_preserved():
    """Project-specific fields should appear in extension_fields."""
    state = {
        "project_name": "Extended",
        "project_id": "ext-1",
        "created_at": "2026-07-01",
        "updated_at": "2026-07-01",
        "current_stage": "active",
        "flg_version": "0.2.1",
        "schema_version": "1",
        "pending_patches": [],
        "next_actions": [],
        "platforms_tracked": ["bilibili", "youtube"],
        "database_path": "/tmp/data.db",
        "decision_log_format": "dual_track",
    }
    info = get_state_schema_info(state)
    assert info["schema_health"] == "ok"
    assert "platforms_tracked" in info["extension_fields"]
    assert "database_path" in info["extension_fields"]
    assert "decision_log_format" in info["extension_fields"]
    assert "platforms_tracked" not in info["core_fields"]


def test_get_state_schema_info_autofill_fields_not_missing():
    """Autofill-safe fields (last_closeout_at, pending_patches, etc.) should not count as missing."""
    state = {
        "project_name": "Minimal",
        "project_id": "min-1",
        "created_at": "2026-07-01",
        "updated_at": "2026-07-01",
        "current_stage": "active",
        "flg_version": "0.2.1",
        "schema_version": "1",
        # missing: last_closeout_at, pending_patches, next_actions,
        #          active_agent, dirty_files, last_snapshot_hash
    }
    info = get_state_schema_info(state)
    assert info["schema_health"] == "ok"
    assert "last_closeout_at" not in info["missing_core"]
    assert "pending_patches" not in info["missing_core"]
    assert "active_agent" not in info["missing_core"]
