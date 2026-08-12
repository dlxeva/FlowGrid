"""Read-only project evidence retrieval tests."""

from __future__ import annotations

import hashlib
import json
import os

import pytest
from typer.testing import CliRunner

from flg.cli import app
from flg.core.evidence import parse_decisions_ledger
from flg.core.evidence_search import search_evidence_records, tokenize_evidence_text


runner = CliRunner()


LEDGER = """# Decision Ledger

## D-001 | Keep the local evidence ledger

### Status
confirmed

### Final Decision
Keep a rebuildable local ledger as the source of project truth.

### Decision Rationale
Different agents must resume from the same audited state.

### Alternatives
Use chat history only.

### Rejected Alternatives
Chat history can revive stale directions.

### Reversal Conditions
Revisit if a safer portable source replaces local files.

## D-002 | 暂缓云端发布

### 决策状态
pending_review

### 最终决策
等待 2026-09-22 的正式核验后再决定云端发布。

### 决策理由
当前证据不足。

### 备选方案
立即发布。

### 放弃理由
尚未确认。

### 复盘入口
收到正式结果后复查。

## D-003 | Retire the old memory platform

### Status
superseded

### Final Decision
Build a generic memory platform in the cloud.

### Decision Rationale
Historical experiment only.

### Alternatives
Use a local project ledger.

### Rejected Alternatives
This direction was replaced.

### Reversal Conditions
None.

## D-004 | Custom review state

### Status
experimental_hold

### Final Decision
Keep the custom review state out of current project truth.

### Decision Rationale
The status is not part of the governed vocabulary.

### Alternatives
Treat it as confirmed.

### Rejected Alternatives
Unsafe.

### Reversal Conditions
Normalize the status first.
"""


INDEX_ITEMS = {
    "D-001": {
        "status": "confirmed",
        "authority": "high",
        "source_excerpt": "用户确认保留本地证据账本。 User confirmed the local evidence ledger.",
        "source_session": ".flg/sessions/local-ledger.md",
    },
    "D-002": {
        "status": "pending_review",
        "authority": "medium",
        "source_excerpt": "用户要求等待 2026-09-22 再核验。",
        "source_capture": ".flg/captures/wait-release.md",
    },
    "D-003": {
        "status": "superseded",
        "authority": "high",
        "source_excerpt": "The generic memory platform was retired.",
    },
    "D-004": {
        "status": "experimental_hold",
        "authority": "unknown",
        "source_excerpt": "Custom state remains non-current.",
    },
}


def _decisions():
    return parse_decisions_ledger(LEDGER)


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_project(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Evidence Search Test"]).exit_code == 0
    finally:
        os.chdir(old_cwd)
    (tmp_path / "DECISIONS.md").write_text(LEDGER, encoding="utf-8")
    index_path = tmp_path / ".flg" / "context" / "evidence_index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps({"version": 2, "items": INDEX_ITEMS}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return index_path


def test_tokenizer_supports_chinese_latin_numbers_and_dates():
    tokens = set(tokenize_evidence_text("本地 Ledger 2026-09-22"))
    assert {"本", "本地", "ledger", "2026-09-22"} <= tokens


def test_search_prefers_title_match_and_is_deterministic():
    first = search_evidence_records(_decisions(), INDEX_ITEMS, "local evidence ledger")
    second = search_evidence_records(_decisions(), INDEX_ITEMS, "local evidence ledger")
    assert first == second
    assert first[0]["decision_id"] == "D-001"
    assert first[0]["matched_fields"][0] == "title"


def test_default_pending_history_and_custom_status_filters():
    assert search_evidence_records(_decisions(), INDEX_ITEMS, "云端发布") == []
    pending = search_evidence_records(
        _decisions(), INDEX_ITEMS, "云端发布", include_pending=True
    )
    assert [lead["decision_id"] for lead in pending] == ["D-002"]

    assert search_evidence_records(_decisions(), INDEX_ITEMS, "memory platform") == []
    history = search_evidence_records(
        _decisions(), INDEX_ITEMS, "memory platform", include_history=True
    )
    assert [lead["decision_id"] for lead in history] == ["D-003"]

    assert search_evidence_records(_decisions(), INDEX_ITEMS, "custom review") == []
    custom = search_evidence_records(
        _decisions(), INDEX_ITEMS, "custom review", include_all=True
    )
    assert [lead["decision_id"] for lead in custom] == ["D-004"]


def test_unindexed_requires_explicit_opt_in():
    items = dict(INDEX_ITEMS)
    items.pop("D-001")
    assert search_evidence_records(_decisions(), items, "local evidence ledger") == []
    leads = search_evidence_records(
        _decisions(), items, "local evidence ledger", include_unindexed=True
    )
    assert leads[0]["decision_id"] == "D-001"
    assert leads[0]["indexed"] is False


def test_top_k_and_invalid_query():
    decisions = _decisions()
    leads = search_evidence_records(
        decisions, INDEX_ITEMS, "decision", top_k=2, include_all=True
    )
    assert len(leads) <= 2
    with pytest.raises(ValueError):
        search_evidence_records(decisions, INDEX_ITEMS, "   ")
    with pytest.raises(ValueError):
        search_evidence_records(decisions, INDEX_ITEMS, "ledger", top_k=0)


def test_cli_old_id_and_new_query_are_compatible_and_read_only(tmp_path):
    index_path = _write_project(tmp_path)
    ledger_path = tmp_path / "DECISIONS.md"
    before = (_hash(index_path), _hash(ledger_path))
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        legacy = runner.invoke(app, ["evidence", "D-001"])
        query = runner.invoke(app, ["evidence", "--query", "本地账本"])
    finally:
        os.chdir(old_cwd)
    assert legacy.exit_code == 0
    assert "Evidence for D-001" in legacy.output
    assert query.exit_code == 0
    assert "Evidence leads for" in query.output
    assert "not an answer" in query.output
    assert "current" in query.output
    assert "D-001" in query.output
    assert before == (_hash(index_path), _hash(ledger_path))


def test_cli_requires_exactly_one_lookup_mode(tmp_path):
    _write_project(tmp_path)
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        neither = runner.invoke(app, ["evidence"])
        both = runner.invoke(app, ["evidence", "D-001", "--query", "ledger"])
    finally:
        os.chdir(old_cwd)
    assert neither.exit_code == 2
    assert "Provide a decision id" in neither.output
    assert both.exit_code == 2
    assert "either a decision id or --query" in both.output
