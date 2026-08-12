"""File-backed decision relations for the formal FLG ledger."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

RELATION_TYPES: Final[tuple[str, ...]] = (
    "supersedes",
    "supports",
    "conflicts_with",
    "depends_on",
)

_RELATION_LABELS: Final[dict[str, tuple[str, ...]]] = {
    "supersedes": (
        "Supersedes",
        "Superseded Decisions",
        "替代决策",
        "取代决策",
    ),
    "supports": (
        "Supports",
        "Supported Decisions",
        "支持决策",
    ),
    "conflicts_with": (
        "Conflicts With",
        "Conflicts With Decisions",
        "冲突决策",
        # Explicit legacy labels accepted for existing human-edited ledgers.
        "Contradicts",
        "Conflicting Decisions",
        "矛盾决策",
    ),
    "depends_on": (
        "Depends On",
        "Dependencies",
        "依赖决策",
    ),
}


@dataclass(frozen=True)
class RelationParseIssue:
    """A non-empty relation declaration that was not fully parseable."""

    source: str
    relation: str
    raw_value: str

    def diagnostic(self) -> str:
        """Return a stable, human-readable doctor diagnostic."""
        return f"{self.source}:{self.relation}:{self.raw_value}:malformed_value"


_DECISION_HEADING = re.compile(
    r"^#{2,3}\s+(D-\d+)\s*[|｜]\s*(.+)$",
    re.MULTILINE | re.IGNORECASE,
)
_DECISION_ID = re.compile(r"(?i)\bD\s*-\s*(\d+)\b")
_EMPTY_MARKERS = {
    "",
    "-",
    "none",
    "n/a",
    "na",
    "无",
    "暂无",
    "未记录",
}


def normalize_decision_id(value: str) -> str | None:
    """Normalize a decision ID to the canonical D-001 form."""
    match = re.fullmatch(r"(?i)\s*D\s*-\s*(\d+)\s*", value)
    if not match:
        return None
    return f"D-{int(match.group(1)):03d}"


def parse_relation_argument(value: str | None) -> list[str]:
    """Parse a strict comma/space-separated CLI relation argument."""
    raw = (value or "").strip()
    if raw.lower() in _EMPTY_MARKERS:
        return []

    targets: list[str] = []
    seen: set[str] = set()
    for token in re.split(r"[,，、;；\s]+", raw):
        if not token:
            continue
        normalized = normalize_decision_id(token)
        if normalized is None:
            raise ValueError(f"Invalid decision id: {token}")
        if normalized not in seen:
            targets.append(normalized)
            seen.add(normalized)
    return targets


def decision_ids(content: str) -> set[str]:
    """Return canonical IDs for all formal decision headings."""
    ids: set[str] = set()
    for match in _DECISION_HEADING.finditer(content):
        normalized = normalize_decision_id(match.group(1))
        if normalized:
            ids.add(normalized)
    return ids


def _parse_relation_value(value: str) -> tuple[list[str], bool]:
    raw = value.strip()
    if raw.lower() in _EMPTY_MARKERS:
        return [], False

    targets: list[str] = []
    seen: set[str] = set()
    spans: list[tuple[int, int]] = []
    for match in _DECISION_ID.finditer(raw):
        normalized = f"D-{int(match.group(1)):03d}"
        if normalized not in seen:
            targets.append(normalized)
            seen.add(normalized)
        spans.append(match.span())

    remainder_parts: list[str] = []
    cursor = 0
    for start, end in spans:
        remainder_parts.append(raw[cursor:start])
        cursor = end
    remainder_parts.append(raw[cursor:])
    remainder = "".join(remainder_parts)
    remainder = re.sub(r"[,，、;；\s]+", "", remainder)
    return targets, bool(remainder)


def _relation_value(block: str, labels: Sequence[str]) -> str:
    label_pattern = "|".join(re.escape(label) for label in labels)

    inline = re.search(
        rf"^(?:-\s*)?\*\*(?:{label_pattern})(?:[：:])?\*\*(?:[：:])?\s*(.*?)\s*$",
        block,
        re.MULTILINE | re.IGNORECASE,
    )
    if inline:
        return inline.group(1).strip()

    bare = re.search(
        rf"^(?:-\s*)?(?:{label_pattern})[：:]\s*(.*?)\s*$",
        block,
        re.MULTILINE | re.IGNORECASE,
    )
    if bare:
        return bare.group(1).strip()

    heading = re.search(
        rf"^###\s+(?:{label_pattern})\s*$\n([\s\S]*?)(?=^###\s|^##\s|\Z)",
        block,
        re.MULTILINE | re.IGNORECASE,
    )
    return heading.group(1).strip() if heading else ""


def parse_decision_relations(
    content: str,
) -> dict[str, dict[str, list[str]]]:
    """Parse explicit relations from each decision block in DECISIONS.md."""
    graph, _ = _parse_decision_relations(content)
    return graph


def _parse_decision_relations(
    content: str,
) -> tuple[dict[str, dict[str, list[str]]], list[RelationParseIssue]]:
    matches = list(_DECISION_HEADING.finditer(content))
    graph: dict[str, dict[str, list[str]]] = {}
    issues: list[RelationParseIssue] = []

    for index, match in enumerate(matches):
        source = normalize_decision_id(match.group(1))
        if source is None:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        block = content[match.start():end]
        graph[source] = {}
        for relation, labels in _RELATION_LABELS.items():
            raw_value = _relation_value(block, labels)
            targets, malformed = _parse_relation_value(raw_value)
            graph[source][relation] = targets
            if malformed:
                issues.append(RelationParseIssue(source, relation, raw_value))

    return graph, issues


def relation_parse_issues(content: str) -> list[RelationParseIssue]:
    """Return malformed non-empty declarations without discarding their text."""
    _, issues = _parse_decision_relations(content)
    return issues


def incoming_relations(
    graph: Mapping[str, Mapping[str, Sequence[str]]],
    decision_id: str,
) -> list[tuple[str, str]]:
    """Return (relation, source_id) edges that point to decision_id."""
    target = normalize_decision_id(decision_id)
    if target is None:
        return []

    incoming: list[tuple[str, str]] = []
    for relation in RELATION_TYPES:
        for source in sorted(graph):
            if target in graph[source].get(relation, ()):
                incoming.append((relation, source))
    return incoming


def validate_decision_relations(content: str) -> list[str]:
    """Report broken explicit relations without mutating the ledger."""
    graph, parse_issues = _parse_decision_relations(content)
    known_ids = set(graph)
    issues = [issue.diagnostic() for issue in parse_issues]

    for source in sorted(graph):
        for relation in RELATION_TYPES:
            for target in graph[source].get(relation, ()):
                if target == source:
                    issues.append(f"{source}:{relation}:{target}:self_relation")
                elif target not in known_ids:
                    issues.append(f"{source}:{relation}:{target}:unknown_target")
    return issues


def format_relation_section(
    relations: Mapping[str, Sequence[str]],
    language: str = "zh",
) -> str:
    """Render the canonical human-editable relation block."""
    if language == "en":
        heading = "### Decision Relations"
        labels = {
            "supersedes": "Supersedes",
            "supports": "Supports",
            "conflicts_with": "Conflicts With",
            "depends_on": "Depends On",
        }
    else:
        heading = "### 决策关系"
        labels = {
            "supersedes": "替代决策",
            "supports": "支持决策",
            "conflicts_with": "冲突决策",
            "depends_on": "依赖决策",
        }

    lines = [heading]
    for relation in RELATION_TYPES:
        targets = ", ".join(relations.get(relation, ())) or "none"
        lines.append(f"- **{labels[relation]}:** {targets}")
    return "\n".join(lines)
