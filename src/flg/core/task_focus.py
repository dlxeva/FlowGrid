"""Pure, lexical task focus over a decision ledger (task-aware-context-v1).

No inference, status promotion, timestamp scoring, or IO is performed here.
Ledger order supplies the recent fallback; relevance ties keep ledger order.
"""

from __future__ import annotations

import re
import unicodedata

from .evidence import _DECISION_HEADING, _section, parse_decisions_ledger


_CURRENT = frozenset({"confirmed", "accepted", "active"})
_ID = re.compile(r"(?<![a-z0-9_-])D-[0-9]+(?![a-z0-9_-])", re.IGNORECASE)
_WORD = re.compile(r"[a-z][a-z0-9]*", re.IGNORECASE)
_HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]+")
_STOP = frozenset(
    "a an and are as at be been but by can could did do does for from had has "
    "have how i if in into is it its may me my not of on or our please should "
    "so than that the their them there these they this those to us was we were "
    "what when where which who why will with would you your "
    "decision decisions history historical current task project related show find "
    "about review revisit "
    "我们 你们 他们 这个 那个 这些 那些 什么 如何 怎么 是否 可以 需要 请问 帮我 "
    "一下 以及 或者 因为 所以 如果 目前 当前 相关 历史 决策 判断 任务 项目 方案 "
    "查看 查找 复查 重新".split()
)
_FIELDS = (
    "title", "what_decided", "rationale", "alternatives",
    "rejected_alternatives", "reversal_conditions",
)
_TRUNCATED = "… [truncated]"
_FIELD_LIMIT = 500


def _terms(text: str) -> set[str]:
    # Remove IDs before tokenizing: a reference to D-123 must not become a
    # generic 'd' or '123' hit on another entry. No substring English matching.
    text = _ID.sub(" ", text).casefold()
    terms = {word for word in _WORD.findall(text) if len(word) > 1}
    for run in _HAN.findall(text):
        terms.update(run[i:i + 2] for i in range(len(run) - 1))
    return terms - _STOP


def _clip(text: str) -> str:
    if len(text) <= _FIELD_LIMIT:
        return text
    return text[:_FIELD_LIMIT - len(_TRUNCATED)] + _TRUNCATED


def select_decisions(content: str, query: str) -> dict:
    """Select at most three relevant current judgments plus recent fallback.

    ``matches`` explains only selected query hits (up to three current and two
    historical). Fallback entries have no invented match explanation. Every
    non-current status, including candidates and unknowns, is history-only.
    ``diagnostics.statuses`` retains the source status for every returned ID.

    Explicit IDs outrank lexical hits, then unique overlapping terms decide;
    equal scores keep ledger order. The recent filler keeps ledger order too,
    so a query with no hits returns exactly the last five current IDs.
    Reversal overlaps are leads only and never establish satisfied conditions.

    Invalid types raise TypeError; invalid queries and duplicate ledger IDs
    raise ValueError. Duplicate checking includes headings skipped as templates
    by the parser, so a duplicate cannot silently point to another entry.
    """
    if not isinstance(content, str) or not isinstance(query, str):
        raise TypeError("content and query must be strings")
    if not 1 <= len(query) <= 500 or not query.strip():
        raise ValueError("query must contain 1..500 characters and not be blank")
    if any(unicodedata.category(c) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for c in query):
        raise ValueError("query must not contain control characters")

    headings = list(_DECISION_HEADING.finditer(content))
    blocks: dict[str, str] = {}
    for index, heading in enumerate(headings):
        decision_id = heading.group(1)
        if decision_id in blocks:
            raise ValueError(f"duplicate decision ID: {decision_id}")
        end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
        blocks[decision_id] = content[heading.start():end]

    decisions = parse_decisions_ledger(content)
    by_id = {item["decision_id"]: item for item in decisions}
    explicit_ids = list(dict.fromkeys(match.group().upper() for match in _ID.finditer(query)))
    query_terms = _terms(query)
    current_ids: list[str] = []
    statuses: dict[str, str] = {}
    hits: list[dict] = []
    for index, item in enumerate(decisions):
        decision_id = item["decision_id"]
        raw_status = _section(blocks[decision_id], ("决策状态", "Status", "状态"))
        statuses[decision_id] = raw_status or item["status"]
        # The shared parser normalizes by prefix (e.g. accepted_candidate ->
        # accepted). Only exact current labels may enter current context. Keep
        # its legacy implicit-confirmed and Chinese 已确认 compatibility.
        is_current = item["status"] in _CURRENT and (
            not raw_status or raw_status.casefold() in _CURRENT or raw_status == "已确认"
        )
        if is_current:
            current_ids.append(decision_id)

        overlaps = {
            field: sorted(query_terms & _terms(item[field])) for field in _FIELDS
        }
        terms = sorted({term for values in overlaps.values() for term in values})
        explicit = decision_id in explicit_ids
        if not explicit and not terms:
            continue
        reasons = [f"status={statuses[decision_id]}"]
        if explicit:
            reasons.append(f"explicit ID: {decision_id}")
        for field, values in overlaps.items():
            if values:
                reasons.append(f"{field} overlap: {', '.join(values)}")
        reversal_terms = overlaps["reversal_conditions"]
        if reversal_terms:
            reasons.append("reversal overlap is a clue only; conditions not established")
        hits.append({
            "id": decision_id,
            "reason": "; ".join(reasons),
            "reversal_terms": reversal_terms,
            "current": is_current,
            "rank": (-int(explicit), -len(terms), index),
        })

    hits.sort(key=lambda hit: hit["rank"])
    current_hits = [hit for hit in hits if hit["current"]][:3]
    historical_hits = [hit for hit in hits if not hit["current"]][:2]
    selected = [hit["id"] for hit in current_hits]
    filler = [decision_id for decision_id in current_ids if decision_id not in selected]
    selected.extend(filler[-(5 - len(selected)):])
    selected_hits = sorted(current_hits + historical_hits, key=lambda hit: hit["rank"])

    historical = []
    for hit in historical_hits:
        item = by_id[hit["id"]]
        historical.append({
            "id": hit["id"],
            "title": _clip(item["title"]),
            "status": statuses[hit["id"]],
            "reason": hit["reason"],
            "decision": _clip(item["what_decided"]),
            "rejected": _clip(item["rejected_alternatives"]),
            "reversal": _clip(item["reversal_conditions"]),
        })
    returned_ids = set(selected) | {hit["id"] for hit in selected_hits}
    return {
        "current_ids": selected,
        "matches": [
            {key: hit[key] for key in ("id", "reason", "reversal_terms")}
            for hit in selected_hits
        ],
        "historical": historical,
        # A syntactically present but unparsed/template ID is not missing;
        # report it separately so callers cannot mistake it for a usable hit.
        "missing_ids": [decision_id for decision_id in explicit_ids if decision_id not in blocks],
        "diagnostics": {
            "statuses": {key: statuses[key] for key in statuses if key in returned_ids},
            "unparsed_ids": [key for key in explicit_ids if key in blocks and key not in by_id],
            "ranking": "explicit ID, unique lexical overlap count, ledger order",
            "reversal_notice": "overlap clues only; conditions not established",
        },
    }
