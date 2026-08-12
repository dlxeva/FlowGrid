"""Deterministic, read-only search over FlowGrid decision evidence.

The formal ledger remains authoritative.  This module only ranks evidence
leads that already exist in ``DECISIONS.md`` and its rebuildable evidence
index; it never promotes a search hit into current project state.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable


CURRENT_STATUSES = frozenset({"confirmed", "accepted", "active"})
PENDING_STATUSES = frozenset({"pending_review", "needs_review", "needs_recheck", "contested"})
HISTORY_STATUSES = frozenset({"stale", "superseded", "rejected", "archived"})
KNOWN_STATUSES = CURRENT_STATUSES | PENDING_STATUSES | HISTORY_STATUSES

FIELD_WEIGHTS: tuple[tuple[str, float], ...] = (
    ("title", 8.0),
    ("what_decided", 6.0),
    ("rationale", 4.0),
    ("source_excerpt", 3.0),
    ("alternatives", 2.0),
    ("rejected_alternatives", 2.0),
    ("reversal_conditions", 1.5),
    ("source_references", 1.0),
)

_LATIN_OR_NUMBER = re.compile(r"[a-z0-9]+(?:[._:/-][a-z0-9]+)*", re.IGNORECASE)
_CJK_RUN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]+")


def _normalize(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).lower().strip()


def tokenize_evidence_text(value: Any) -> tuple[str, ...]:
    """Return stable Latin/number tokens plus CJK unigrams and bigrams."""
    text = _normalize(value)
    tokens: set[str] = set(_LATIN_OR_NUMBER.findall(text))
    for run in _CJK_RUN.findall(text):
        tokens.update(run)
        tokens.update(run[index : index + 2] for index in range(len(run) - 1))
    return tuple(sorted(token for token in tokens if token))


def _source_references(item: dict[str, Any]) -> str:
    refs: list[str] = []
    for field in ("source_patch", "source_session", "source_capture"):
        value = item.get(field)
        if value:
            refs.append(str(value))
    episodes = item.get("source_episodes")
    if isinstance(episodes, list):
        for episode in episodes:
            if isinstance(episode, dict) and episode.get("source_ref"):
                refs.append(str(episode["source_ref"]))
    return " ".join(dict.fromkeys(refs))


def _allowed_statuses(
    *,
    include_pending: bool,
    include_history: bool,
    include_all: bool,
) -> frozenset[str] | None:
    if include_all:
        return None
    allowed = set(CURRENT_STATUSES)
    if include_pending:
        allowed.update(PENDING_STATUSES)
    if include_history:
        allowed.update(HISTORY_STATUSES)
    return frozenset(allowed)


def _score_field(query: str, query_tokens: set[str], value: Any, weight: float) -> tuple[float, bool]:
    normalized = _normalize(value)
    if not normalized:
        return 0.0, False
    field_tokens = set(tokenize_evidence_text(normalized))
    hits = query_tokens & field_tokens
    if not hits and query not in normalized:
        return 0.0, False

    score = weight * (len(hits) / max(1, len(query_tokens)))
    if query and query in normalized:
        score += weight * 4.0
    if query_tokens and query_tokens.issubset(field_tokens):
        score += weight * 2.0
    return score, True


def _decision_number(decision_id: str) -> int:
    match = re.fullmatch(r"D-(\d+)", decision_id.upper())
    return int(match.group(1)) if match else -1


def search_evidence_records(
    decisions: Iterable[dict[str, Any]],
    evidence_items: dict[str, Any],
    query: str,
    *,
    top_k: int = 5,
    include_pending: bool = False,
    include_history: bool = False,
    include_all: bool = False,
    include_unindexed: bool = False,
) -> list[dict[str, Any]]:
    """Rank evidence leads without reading or writing project files.

    Status is a filter, never a relevance signal.  Historical and pending
    judgments therefore cannot outrank current truth unless the caller
    explicitly includes their status class, and every result retains its
    ledger status for downstream display.
    """
    normalized_query = _normalize(query)
    query_tokens = set(tokenize_evidence_text(normalized_query))
    if not normalized_query or not query_tokens:
        raise ValueError("Evidence query must contain searchable text.")
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")
    limit = min(int(top_k), 50)
    allowed = _allowed_statuses(
        include_pending=include_pending,
        include_history=include_history,
        include_all=include_all,
    )

    leads: list[dict[str, Any]] = []
    for decision in decisions:
        decision_id = str(decision.get("decision_id") or "").upper()
        if not decision_id:
            continue
        indexed_item = evidence_items.get(decision_id)
        indexed = isinstance(indexed_item, dict)
        if not indexed and not include_unindexed:
            continue
        item = indexed_item if indexed else {}
        status = _normalize(decision.get("status")) or "unknown"
        if allowed is not None and status not in allowed:
            continue

        source_references = _source_references(item)
        fields: dict[str, Any] = {
            "title": decision.get("title"),
            "what_decided": decision.get("what_decided"),
            "rationale": decision.get("rationale"),
            "source_excerpt": item.get("source_excerpt"),
            "alternatives": decision.get("alternatives"),
            "rejected_alternatives": decision.get("rejected_alternatives"),
            "reversal_conditions": decision.get("reversal_conditions"),
            "source_references": source_references,
        }

        score = 0.0
        matched_fields: list[str] = []
        if normalized_query == _normalize(decision_id):
            score += 100.0
            matched_fields.append("decision_id")
        elif _normalize(decision_id).startswith(normalized_query):
            score += 25.0
            matched_fields.append("decision_id")
        for field, weight in FIELD_WEIGHTS:
            field_score, matched = _score_field(normalized_query, query_tokens, fields[field], weight)
            score += field_score
            if matched:
                matched_fields.append(field)
        if score <= 0.0:
            continue

        excerpt = str(item.get("source_excerpt") or decision.get("what_decided") or "").strip()
        leads.append(
            {
                "decision_id": decision_id,
                "title": str(decision.get("title") or ""),
                "status": status,
                "authority": str(item.get("authority") or "unknown"),
                "score": round(score, 6),
                "matched_fields": matched_fields,
                "excerpt": excerpt,
                "source_references": source_references,
                "indexed": indexed,
            }
        )

    leads.sort(
        key=lambda lead: (
            -float(lead["score"]),
            -_decision_number(str(lead["decision_id"])),
            str(lead["decision_id"]),
        )
    )
    return leads[:limit]


__all__ = [
    "CURRENT_STATUSES",
    "PENDING_STATUSES",
    "HISTORY_STATUSES",
    "KNOWN_STATUSES",
    "search_evidence_records",
    "tokenize_evidence_text",
]
