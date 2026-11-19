"""Synthetic, IO-free tests for task-aware decision selection."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from flg.core.task_focus import select_decisions


def entry(number, title="neutral", status="confirmed", decision="retain", *,
          rationale="", alternatives="", rejected="", reversal=""):
    return (
        f"\n## D-{number:03d} | {title}\n\n"
        f"### Status\n{status}\n\n"
        f"### Final Decision\n{decision}\n\n"
        f"### Decision Rationale\n{rationale}\n\n"
        f"### Alternatives\n{alternatives}\n\n"
        f"### Rejected Alternatives\n{rejected}\n\n"
        f"### Reversal Conditions\n{reversal}\n"
    )


def recent_ledger():
    return "".join(entry(i) for i in range(2, 9))


def test_old_important_decision_survives_recent_five():
    ledger = entry(1, "portable evidence ledger") + recent_ledger()
    result = select_decisions(ledger, "portable evidence")
    assert result["current_ids"] == ["D-001", "D-005", "D-006", "D-007", "D-008"]
    assert [hit["id"] for hit in result["matches"]] == ["D-001"]
    assert "title overlap: evidence, portable" in result["matches"][0]["reason"]
    assert result["historical"] == []


@pytest.mark.parametrize("query", ["qzxvnoise", "!!!", "the and please this decision", "我", "当前相关决策"])
def test_no_hit_preserves_last_five_without_inventing_associations(query):
    result = select_decisions(recent_ledger(), query)
    assert result["current_ids"] == [f"D-{i:03d}" for i in range(4, 9)]
    assert result["matches"] == []
    assert result["historical"] == []


def test_english_words_are_case_insensitive_and_not_substrings():
    ledger = entry(1, "CLOUD portability") + entry(2, "cloudy portable")
    result = select_decisions(ledger, "cloud")
    assert [hit["id"] for hit in result["matches"]] == ["D-001"]
    assert "cloud" in result["matches"][0]["reason"]


def test_chinese_bigrams_not_single_character_or_semantic_matches():
    ledger = entry(1, "保留本地证据账本") + entry(2, "本次地点选择") + entry(3, "local ledger")
    result = select_decisions(ledger, "请问本地账本")
    assert [hit["id"] for hit in result["matches"]] == ["D-001"]
    assert "本地" in result["matches"][0]["reason"]
    assert "账本" in result["matches"][0]["reason"]


def test_explicit_ids_win_over_terms_and_missing_ids_keep_query_order():
    ledger = entry(1, "alpha beta gamma") + entry(2, "neutral") + recent_ledger().replace("D-002", "D-009")
    result = select_decisions(ledger, "alpha beta gamma d-002 D-999 D-888 D-999")
    assert result["current_ids"][:2] == ["D-002", "D-001"]
    assert result["matches"][0]["id"] == "D-002"
    assert "explicit ID: D-002" in result["matches"][0]["reason"]
    assert result["missing_ids"] == ["D-999", "D-888"]


def test_explicit_id_does_not_match_prefix_or_cross_reference():
    ledger = entry(1, "D-010 replacement") + entry(10, "replacement") + entry(100, "replacement")
    result = select_decisions(ledger, "D-010")
    assert [hit["id"] for hit in result["matches"]] == ["D-010"]
    result = select_decisions(ledger, "D-01")
    assert result["matches"] == []
    assert result["missing_ids"] == ["D-01"]


@pytest.mark.parametrize("status", ["rejected", "superseded", "pending_review", "candidate",
                                     "experimental_hold", "stale", "accepted_candidate", "active_proposal"])
def test_noncurrent_statuses_never_revive_or_promote(status):
    ledger = entry(1, "cloud", status, rejected="unsafe", reversal="portable evidence") + recent_ledger()
    result = select_decisions(ledger, "D-001 cloud portable evidence")
    assert "D-001" not in result["current_ids"]
    history = result["historical"]
    assert len(history) == 1
    assert history[0]["status"] == status
    assert history[0]["rejected"] == "unsafe"
    assert history[0]["reversal"] == "portable evidence"
    assert result["diagnostics"]["statuses"]["D-001"] == status


@pytest.mark.parametrize("status", ["confirmed", "accepted", "active", "Confirmed", "已确认", ""])
def test_current_and_legacy_statuses(status):
    result = select_decisions(entry(1, "cloud", status), "cloud")
    assert result["current_ids"] == ["D-001"]
    assert result["historical"] == []
    assert result["diagnostics"]["statuses"]["D-001"] == (status or "confirmed")


def test_original_historical_status_annotation_is_retained():
    result = select_decisions(entry(1, "cloud", "superseded by D-002"), "cloud")
    assert result["historical"][0]["status"] == "superseded by D-002"
    assert result["current_ids"] == []


def test_annotated_current_status_is_conservatively_history_only():
    result = select_decisions(entry(1, "cloud", "confirmed_candidate"), "cloud")
    assert result["current_ids"] == []
    assert result["historical"][0]["status"] == "confirmed_candidate"


def test_limits_and_stable_tie_order_and_recent_filler():
    ledger = "".join(entry(i, "cloud") for i in range(1, 10))
    ledger += "".join(entry(i, "cloud", "rejected") for i in range(10, 15))
    result = select_decisions(ledger, "cloud")
    assert result["current_ids"] == ["D-001", "D-002", "D-003", "D-008", "D-009"]
    assert [item["id"] for item in result["historical"]] == ["D-010", "D-011"]
    assert len(result["matches"]) == 5
    assert len(set(result["current_ids"])) == 5


def test_distinct_overlap_count_outranks_repetition():
    ledger = entry(1, "cloud cloud cloud") + entry(2, "cloud ledger")
    result = select_decisions(ledger, "cloud ledger")
    assert [hit["id"] for hit in result["matches"]] == ["D-002", "D-001"]


@pytest.mark.parametrize("field", ["title", "decision", "rationale", "alternatives", "rejected", "reversal"])
def test_each_ledger_field_can_supply_literal_evidence(field):
    kwargs = {field: "portability"}
    result = select_decisions(entry(1, **kwargs), "portability")
    assert result["matches"][0]["id"] == "D-001"


def test_reversal_terms_are_sorted_clues_not_satisfied_conditions():
    result = select_decisions(entry(1, reversal="Only if portable evidence exists"), "evidence portable")
    hit = result["matches"][0]
    assert hit["reversal_terms"] == ["evidence", "portable"]
    assert "clue only; conditions not established" in hit["reason"]
    assert select_decisions(entry(1, title="evidence", reversal="unsafe"), "evidence")["matches"][0]["reversal_terms"] == []


def test_unrelated_history_is_not_filled_and_dates_do_not_decay():
    ledger = entry(1, "cloud", "rejected") + entry(2, "ledger", "superseded")
    assert select_decisions(ledger, "noise")["historical"] == []
    ledger = entry(1, "cloud", decision="date 1900-01-01") + recent_ledger()
    assert select_decisions(ledger, "cloud")["current_ids"][0] == "D-001"


@pytest.mark.parametrize("second", [entry(1), entry(1, title="[title]"), entry(1, decision="[decision title]")])
def test_duplicate_id_rejects_entire_selection_even_if_template_skipped(second):
    with pytest.raises(ValueError, match="duplicate decision ID: D-001"):
        select_decisions(entry(1) + second, "noise")


@pytest.mark.parametrize("query", ["", "   ", "x" * 501, " " * 500 + "x",
                                  "cloud\n", "cloud\t", "cloud\x00", "cloud\x7f", "cloud\x85",
                                  "cloud\u200b", "cloud\u202e", "cloud\u2028", "\ud800"])
def test_invalid_queries_raise(query):
    with pytest.raises(ValueError):
        select_decisions("", query)


@pytest.mark.parametrize("query", ["x", "x" * 500, " 本地 ", "\u3000本地\u3000"])
def test_valid_query_boundaries(query):
    assert select_decisions("", query)["current_ids"] == []


@pytest.mark.parametrize("content,query", [(None, "a"), ("", None), (1, "a"), ("", ["a"]), (b"", "a")])
def test_nonstring_input_raises_type_error(content, query):
    with pytest.raises(TypeError):
        select_decisions(content, query)


def test_unparsed_explicit_id_is_distinct_from_missing():
    ledger = entry(1, title="[title]")
    result = select_decisions(ledger, "D-001 D-999")
    assert result["missing_ids"] == ["D-999"]
    assert result["diagnostics"]["unparsed_ids"] == ["D-001"]
    assert result["matches"] == []


def test_chinese_legacy_ledger_and_heading_formats():
    ledger = """### D-001 ｜ 本地账本
**状态**：已确认
**决策**：保留证据。
**复盘入口**：云端可迁移时复查。
## D-002 | 云端方案
### 决策状态
拒绝
### 最终决策
暂缓云端方案。
"""
    result = select_decisions(ledger, "本地账本 云端")
    assert result["current_ids"] == ["D-001"]
    assert result["historical"][0]["status"] == "拒绝"
    assert result["diagnostics"]["statuses"]["D-001"] == "已确认"


def test_historical_fields_truncate_with_visible_marker():
    long_text = "cloud " + "x" * 600
    result = select_decisions(entry(1, long_text, "rejected", long_text,
                                    rejected=long_text, reversal=long_text), "cloud")
    history = result["historical"][0]
    for field in ("title", "decision", "rejected", "reversal"):
        assert len(history[field]) == 500
        assert history[field].endswith("… [truncated]")
    assert history["status"] == "rejected"
    assert select_decisions(entry(1, "cloud", "rejected", "x" * 500), "cloud")["historical"][0]["decision"] == "x" * 500


def test_deterministic_fresh_results_and_no_io(monkeypatch):
    ledger = entry(1, "cloud ledger", reversal="cloud evidence") + recent_ledger()
    def forbidden(*args, **kwargs):
        raise AssertionError("selection must not perform IO")
    monkeypatch.setattr("builtins.open", forbidden)
    first = select_decisions(ledger, "cloud evidence ledger")
    expected = json.dumps(first, ensure_ascii=False)
    for _ in range(5):
        assert json.dumps(select_decisions(ledger, "cloud evidence ledger"), ensure_ascii=False) == expected
    first["matches"][0]["reversal_terms"].append("mutated")
    assert json.dumps(select_decisions(ledger, "cloud evidence ledger"), ensure_ascii=False) == expected


def test_deterministic_across_hash_seeds():
    ledger = entry(1, "cloud ledger", reversal="cloud evidence") + recent_ledger()
    code = (
        "import json; from flg.core.task_focus import select_decisions; "
        f"print(json.dumps(select_decisions({ledger!r}, 'cloud evidence ledger'), ensure_ascii=False))"
    )
    results = []
    for seed in ("1", "42"):
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1")
        results.append(subprocess.check_output([sys.executable, "-B", "-c", code], env=env))
    assert results[0] == results[1]
