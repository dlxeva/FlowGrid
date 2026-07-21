"""Evidence index rebuilding and cross-file consistency checks."""

from __future__ import annotations

import json
import re
from hashlib import sha256
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


def _source_id(source_type: str, source_ref: str, content_hash: str) -> str:
    """Create a stable ID for an evidence episode without depending on a path alone."""
    digest = sha256(f"{source_type}\0{source_ref}\0{content_hash}".encode("utf-8")).hexdigest()
    return f"S-{digest[:12]}"


def _episode_content_hash(root: Path, source_ref: str, excerpt: str) -> str:
    """Prefer the archived source bytes; fall back to the retained excerpt."""
    path = Path(source_ref)
    if source_ref and not source_ref.startswith("DECISIONS.md#"):
        if not path.is_absolute():
            path = root / path
        try:
            return sha256(path.read_bytes()).hexdigest()
        except OSError:
            pass
    return sha256(excerpt.encode("utf-8")).hexdigest()


def build_source_episodes(root: Path, decision_id: str, item: dict[str, Any]) -> list[dict[str, str]]:
    """Build source episodes for a decision from durable evidence references.

    The formal ledger remains the source of truth. Episodes are a rebuildable
    index that lets a caller walk from a reviewed judgment to the raw material
    and the review event that made it usable project state.
    """
    excerpt = str(item.get("source_excerpt") or item.get("what_decided") or "")
    candidates: list[tuple[str, str, str]] = []
    for field, source_type in (
        ("source_session", "raw_session"),
        ("source_capture", "capture"),
        ("source_patch", "closeout_patch"),
    ):
        value = str(item.get(field) or "").strip()
        if value and value != "unknown":
            candidates.append((source_type, value, "derived_from"))

    patch_id = str(item.get("patch_id") or "").strip()
    reviewed_at = str(item.get("reviewed_at") or "").strip()
    if patch_id or reviewed_at:
        candidates.append(("review_action", f"review:{patch_id or decision_id}", "confirmed_by"))

    # Every decision has at least an inspectable ledger anchor, even when an
    # older manual entry has no archived raw discussion.
    candidates.append(("formal_ledger", f"DECISIONS.md#{decision_id}", "recorded_in"))

    episodes: list[dict[str, str]] = []
    seen: set[str] = set()
    for source_type, source_ref, relation in candidates:
        content_hash = _episode_content_hash(root, source_ref, excerpt)
        source_id = _source_id(source_type, source_ref, content_hash)
        if source_id in seen:
            continue
        seen.add(source_id)
        episode = {
            "source_id": source_id,
            "source_type": source_type,
            "source_ref": source_ref,
            "relation": relation,
            "content_hash": content_hash,
        }
        if excerpt:
            episode["excerpt"] = excerpt
        if reviewed_at and source_type == "review_action":
            episode["recorded_at"] = reviewed_at
        episodes.append(episode)
    return episodes


def enrich_source_episodes(root: Path, index: dict[str, Any]) -> dict[str, Any]:
    """Attach rebuildable, multi-source provenance to every indexed decision."""
    items = index.setdefault("items", {})
    for decision_id, item in items.items():
        if isinstance(item, dict):
            item["source_episodes"] = build_source_episodes(root, decision_id, item)
    index["version"] = max(int(index.get("version", 1)), 2)
    return index


def normalize_decision_status(value: str) -> str:
    """Normalize ledger status text without discarding historical annotations."""
    normalized = value.strip().lower()
    for status in (
        "pending_review",
        "needs_recheck",
        "needs_review",
        "superseded",
        "rejected",
        "contested",
        "stale",
        "confirmed",
        "accepted",
        "active",
        "archived",
    ):
        if normalized.startswith(status):
            return status
    return normalized or "confirmed"


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
        status = normalize_decision_status(_section(block, ("决策状态", "Status")))
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
                "status": status,
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
    enrich_source_episodes(root, index)
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
            "status": decision["status"],
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

    return enrich_source_episodes(root, {
        "version": 2,
        "rebuilt_from": "DECISIONS.md",
        "items": items,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    })


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
    missing_source_episodes: list[str] = []
    broken_source_episodes: list[str] = []
    for decision_id, item in index_items.items():
        for field in ("source_patch", "source_session", "source_capture"):
            value = item.get(field)
            if value and not _path_exists(root, str(value)):
                broken_references.append(f"{decision_id}:{field}={value}")
        episodes = item.get("source_episodes")
        if not isinstance(episodes, list) or not episodes:
            missing_source_episodes.append(decision_id)
            continue
        for episode in episodes:
            if not isinstance(episode, dict):
                broken_source_episodes.append(f"{decision_id}:invalid_episode")
                continue
            source_ref = str(episode.get("source_ref") or "")
            source_type = str(episode.get("source_type") or "")
            if source_type in {"raw_session", "capture", "closeout_patch"} and source_ref and not _path_exists(root, source_ref):
                broken_source_episodes.append(f"{decision_id}:{source_type}={source_ref}")

    state_path = root / ".flg" / "state.json"
    state_text = state_path.read_text(encoding="utf-8") if state_path.exists() else ""
    legacy_paths = sorted(set(re.findall(r"(?:/mnt/c/|/root/|[A-Za-z]:\\)[^\"\n]*", state_text)))
    merged_pending = []
    closed_statuses = {"merged", "rejected", "superseded"}
    try:
        state = json.loads(state_text) if state_text else {}
    except json.JSONDecodeError:
        state = {}
    for patch in state.get("pending_patches", []) if isinstance(state, dict) else []:
        if not isinstance(patch, dict):
            continue

        # Closed entries are retained in state.json for audit history. They
        # are healthy; only a state/file disagreement should be actionable.
        state_status = str(patch.get("status") or "").lower()
        if state_status in closed_statuses:
            continue

        patch_path = patch.get("path")
        if not patch_path:
            continue
        path = Path(str(patch_path))
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            continue

        file_status = ""
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("status:"):
                    file_status = line.split(":", 1)[1].strip().lower()
                    break
        except OSError:
            continue

        if file_status in closed_statuses:
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
    if missing_source_episodes:
        issues.append("missing_source_episodes")
    if broken_source_episodes:
        issues.append("broken_source_episodes")
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
        "missing_source_episodes": missing_source_episodes,
        "broken_source_episodes": broken_source_episodes,
        "legacy_paths": legacy_paths,
        "merged_pending": merged_pending,
    }
