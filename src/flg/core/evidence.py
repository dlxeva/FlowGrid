"""Evidence index rebuilding and cross-file consistency checks."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

EVIDENCE_INDEX_PATH = Path(".flg") / "context" / "evidence_index.json"

# Accept both the ASCII separator emitted by current templates and the fullwidth
# separator used by existing Chinese ledgers.
_DECISION_HEADING = re.compile(r"^##\s+(D-\d+)\s*[|｜]\s*(.+)$", re.MULTILINE)
_PLACEHOLDER_MARKERS = ("标题", "d-xxx", "[title]", "[decision title]")
_PROVENANCE_FIELDS = (
    "source_patch",
    "source_session",
    "source_capture",
    "patch_id",
    "source_command",
    "reviewed_at",
)


def _section(block: str, headings: tuple[str, ...]) -> str:
    heading_pattern = "|".join(re.escape(heading) for heading in headings)
    match = re.search(
        rf"^###\s+(?:{heading_pattern})\s*$\n([\s\S]*?)(?=^###\s|^##\s|\Z)",
        block,
        re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def _is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or any(marker.lower() in lowered for marker in _PLACEHOLDER_MARKERS)


def parse_decisions_ledger(content: str) -> list[dict[str, str]]:
    """Parse real decision entries from DECISIONS.md.

    DECISIONS.md is the formal source of truth. Entries with only template
    placeholders are ignored, while direct `flg decision add` entries are
    included even when they have no explicit `accepted` marker.
    """
    matches = list(_DECISION_HEADING.finditer(content))
    decisions: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        block = content[match.start():end]
        decision_id = match.group(1)
        title = match.group(2).strip()
        what_decided = _section(block, ("最终决策", "Final Decision"))
        rationale = _section(block, ("决策理由", "Decision Rationale"))
        alternatives = _section(block, ("备选方案", "Alternatives"))
        rejected = _section(block, ("放弃理由", "Rejected Alternatives"))
        reversal = _section(block, ("复盘入口", "Reversal Conditions"))
        if _is_placeholder(title) or _is_placeholder(what_decided):
            continue

        source_match = re.search(r"^\*.*?\|\s*Source:\s*(.*?)\*\s*$", block, re.MULTILINE)
        source = source_match.group(1).strip() if source_match else ""
        if "用户明确指令" in source or "user_confirmation" in source:
            source_type = "user_confirmation"
        elif "capture" in source.lower():
            source_type = "capture_review"
        elif "closeout" in source.lower() or "review" in source.lower():
            source_type = "review_action"
        else:
            source_type = "ledger_rebuild"

        decisions.append(
            {
                "decision_id": decision_id,
                "title": title,
                "what_decided": what_decided,
                "rationale": rationale,
                "alternatives": alternatives,
                "rejected_alternatives": rejected,
                "reversal_conditions": reversal,
                "source_type": source_type,
                "source": source,
            }
        )
    return decisions


def _unparsed_decision_ids(content: str, parsed_ids: set[str]) -> list[str]:
    """Find non-template decision headings that the structured parser skipped."""
    headings = _DECISION_HEADING.finditer(content)
    return sorted(
        {
            match.group(1)
            for match in headings
            if not _is_placeholder(match.group(2)) and match.group(1) not in parsed_ids
        }
    )


def load_evidence_index(root: Path) -> dict[str, Any]:
    path = root / EVIDENCE_INDEX_PATH
    if not path.exists():
        return {"version": 1, "items": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "items": {}}
    if not isinstance(data, dict) or not isinstance(data.get("items"), dict):
        return {"version": 1, "items": {}}
    return data


def save_evidence_index(root: Path, index: dict[str, Any]) -> Path:
    path = root / EVIDENCE_INDEX_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    index["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def rebuild_evidence_index(root: Path) -> dict[str, Any]:
    decisions_path = root / "DECISIONS.md"
    content = decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""
    old_items = load_evidence_index(root).get("items", {})
    items: dict[str, dict[str, Any]] = {}

    for decision in parse_decisions_ledger(content):
        decision_id = decision["decision_id"]
        old = old_items.get(decision_id, {})
        item: dict[str, Any] = {
            "decision_id": decision_id,
            "status": "confirmed",
            "authority": old.get("authority", "high"),
            "source_type": old.get("source_type") or decision["source_type"],
            "source_excerpt": old.get("source_excerpt") or decision["what_decided"],
            "title": decision["title"],
            "rationale": decision["rationale"],
            "alternatives": decision["alternatives"],
            "rejected_alternatives": decision["rejected_alternatives"],
            "reversal_conditions": decision["reversal_conditions"],
        }
        for field in _PROVENANCE_FIELDS:
            if old.get(field):
                item[field] = old[field]
        items[decision_id] = item

    return {
        "version": 1,
        "rebuilt_from": "DECISIONS.md",
        "items": items,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def _path_exists(root: Path, value: str) -> bool:
    path = Path(value)
    return path.exists() if path.is_absolute() else (root / path).exists()


def validate_project(root: Path) -> dict[str, Any]:
    """Return deterministic cross-file health information without writing."""
    decisions_path = root / "DECISIONS.md"
    decisions = parse_decisions_ledger(
        decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""
    )
    decision_ids = {item["decision_id"] for item in decisions}
    ledger_content = decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""
    unparsed_decisions = _unparsed_decision_ids(ledger_content, decision_ids)
    index_path = root / EVIDENCE_INDEX_PATH
    index_exists = index_path.exists()
    index = load_evidence_index(root)
    index_items = index.get("items", {})
    index_ids = set(index_items)

    missing_index = sorted(decision_ids - index_ids)
    orphan_index = sorted(index_ids - decision_ids)
    broken_references: list[str] = []
    for decision_id, item in index_items.items():
        for field in ("source_patch", "source_session", "source_capture"):
            value = item.get(field)
            if value and not _path_exists(root, str(value)):
                broken_references.append(f"{decision_id}:{field}={value}")

    state_path = root / ".flg" / "state.json"
    state_text = state_path.read_text(encoding="utf-8") if state_path.exists() else ""
    legacy_paths = sorted(set(re.findall(r"(?:/mnt/c/|/root/|[A-Za-z]:\\)[^\"\n]*", state_text)))
    merged_pending = []
    try:
        state = json.loads(state_text) if state_text else {}
    except json.JSONDecodeError:
        state = {}
    for patch in state.get("pending_patches", []) if isinstance(state, dict) else []:
        if isinstance(patch, dict) and patch.get("status") in {"merged", "rejected", "superseded"}:
            merged_pending.append(str(patch.get("patch_id", "unknown")))

    issues = []
    if not index_exists:
        issues.append("evidence_index_missing")
    if missing_index:
        issues.append("decisions_missing_from_index")
    if orphan_index:
        issues.append("orphan_index_entries")
    if broken_references:
        issues.append("broken_evidence_references")
    if legacy_paths:
        issues.append("legacy_paths")
    if merged_pending:
        issues.append("closed_patches_in_pending_state")
    if unparsed_decisions:
        issues.append("unparsed_decision_entries")

    return {
        "status": "ok" if not issues else "needs_attention",
        "issues": issues,
        "decision_count": len(decision_ids),
        "unparsed_decisions": unparsed_decisions,
        "index_count": len(index_ids),
        "missing_index": missing_index,
        "orphan_index": orphan_index,
        "broken_references": broken_references,
        "legacy_paths": legacy_paths,
        "merged_pending": merged_pending,
    }