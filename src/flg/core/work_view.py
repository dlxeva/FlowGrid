"""Build and inspect a bounded view over a declared current-work source."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORK_VIEW_MANIFEST = ".flg/context/work-view.json"
WORK_VIEW_SCHEMA_VERSION = "1"
_MAX_SOURCE_CHARS = 1_000_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _one_line(value: Any, limit: int = 240) -> str:
    compact = re.sub(r"\s+", " ", str(value or "")).strip()
    return compact.replace("`", "'")[:limit]


def _resolve_source(root: Path, value: Any) -> tuple[Path, str]:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("work_source.path must be a non-empty project-relative path.")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"work_source.path must stay inside the project: {value}")

    root = root.resolve()
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Symlinked work sources are not supported: {value}")
    try:
        resolved = (root / relative).resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"Declared work source does not exist: {value}") from exc
    if root not in resolved.parents:
        raise ValueError(f"work_source.path must stay inside the project: {value}")
    if not resolved.is_file():
        raise ValueError(f"Declared work source must be a file: {value}")
    return resolved, resolved.relative_to(root).as_posix()


def _marker(config: dict[str, Any], key: str) -> str | None:
    value = config.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"work_source.{key} must be a non-empty string when provided.")
    if "\n" in value or "\r" in value:
        raise ValueError(f"work_source.{key} must be a single-line marker.")
    if len(value) > 200:
        raise ValueError(f"work_source.{key} must be at most 200 characters.")
    return value


def load_work_source(root: Path, state: dict[str, Any] | None) -> dict[str, Any] | None:
    """Validate the optional declaration stored as a state extension."""
    if not state or "work_source" not in state:
        return None
    raw = state["work_source"]
    if not isinstance(raw, dict):
        raise ValueError("work_source must be an object in .flg/state.json.")
    schema = str(raw.get("schema_version", WORK_VIEW_SCHEMA_VERSION))
    if schema != WORK_VIEW_SCHEMA_VERSION:
        raise ValueError(f"Unsupported work_source schema version: {schema}")
    source, relative = _resolve_source(root, raw.get("path"))
    start = _marker(raw, "start_marker")
    end = _marker(raw, "end_marker")
    if (start is None) != (end is None):
        raise ValueError("work_source.start_marker and end_marker must be provided together.")
    if start is not None and start == end:
        raise ValueError("work_source start_marker and end_marker must be different.")
    return {
        "schema_version": schema,
        "path": relative,
        "resolved_path": source,
        "start_marker": start,
        "end_marker": end,
    }


def _source_block(config: dict[str, Any]) -> dict[str, Any]:
    path: Path = config["resolved_path"]
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise ValueError(
            f"Declared work source must be UTF-8 text: {config['path']}"
        ) from exc
    if len(text) > _MAX_SOURCE_CHARS:
        raise ValueError(
            f"Declared work source exceeds {_MAX_SOURCE_CHARS} characters: {config['path']}"
        )
    lines = text.splitlines(keepends=True)
    start = config["start_marker"]
    end = config["end_marker"]
    if start is None:
        block = text
        start_line = 1
        end_line = max(1, len(text.splitlines()))
        locator = config["path"]
    else:
        start_hits = [idx for idx, line in enumerate(lines) if line.rstrip("\r\n") == start]
        end_hits = [idx for idx, line in enumerate(lines) if line.rstrip("\r\n") == end]
        if len(start_hits) != 1:
            raise ValueError(
                f"start_marker must occur exactly once in {config['path']}; "
                f"found {len(start_hits)}."
            )
        if len(end_hits) != 1:
            raise ValueError(
                f"end_marker must occur exactly once in {config['path']}; found {len(end_hits)}."
            )
        if start_hits[0] >= end_hits[0]:
            raise ValueError(f"work_source markers are out of order in {config['path']}.")
        block = "".join(lines[start_hits[0] + 1 : end_hits[0]])
        start_line = start_hits[0] + 2
        end_line = max(start_line, end_hits[0])
        locator = f"{config['path']}#L{start_line}-L{end_line}"
    return {
        "text": block,
        "sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
        "locator": locator,
        "start_line": start_line,
        "end_line": end_line,
    }


def _section(text: str, aliases: tuple[str, ...]) -> str:
    lines = text.splitlines()
    aliases_lower = {alias.casefold() for alias in aliases}
    start: int | None = None
    level = 0
    for idx, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match and match.group(2).casefold() in aliases_lower:
            start = idx + 1
            level = len(match.group(1))
            break
    if start is None:
        return ""
    end = len(lines)
    for idx in range(start, len(lines)):
        match = re.match(r"^(#{1,6})\s+", lines[idx])
        if match and len(match.group(1)) <= level:
            end = idx
            break
    return "\n".join(lines[start:end]).strip()


def _items(text: str, *, limit: int, item_chars: int) -> list[str]:
    items: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", raw).strip()
        line = re.sub(r"^#+\s+", "", line).strip()
        if not line or line.startswith("<!--"):
            continue
        item = _one_line(line, item_chars)
        if item and item not in items:
            items.append(item)
        if len(items) >= limit:
            break
    return items


def _extract_fields(block: str, compact: bool = False) -> dict[str, Any]:
    item_limit = 1 if compact else 6
    item_chars = 100 if compact else 220
    action_chars = 140 if compact else 360
    action_items = _items(
        _section(
            block,
            (
                "Current Action",
                "Next Action",
                "Current Work",
                "当前行动",
                "下一步行动",
                "当前工作",
            ),
        ),
        limit=1,
        item_chars=action_chars,
    )
    blockers = _items(
        _section(block, ("Blockers", "Current Blockers", "阻塞项", "当前阻塞")),
        limit=item_limit,
        item_chars=item_chars,
    )
    constraints = _items(
        _section(
            block,
            (
                "Constraints",
                "Hard Constraints",
                "Necessary Constraints",
                "约束",
                "硬约束",
                "必要约束",
            ),
        ),
        limit=item_limit,
        item_chars=item_chars,
    )
    missing = []
    if not action_items:
        missing.append("current action")
    if not blockers:
        missing.append("blockers (record an explicit 'none' item when there are none)")
    if not constraints:
        missing.append("necessary constraints (record an explicit 'none' item when there are none)")
    return {
        "current_action": action_items[0] if action_items else None,
        "blockers": blockers,
        "constraints": constraints,
        "missing": missing,
    }


def _render_list(items: list[str], empty: str) -> str:
    return "\n".join(f"- {item}" for item in items) if items else f"- {empty}"


def _render(
    config: dict[str, Any],
    block: dict[str, Any],
    fields: dict[str, Any],
    *,
    compacted: bool,
) -> str:
    action_status = "current" if fields["current_action"] else "not_defined"
    note = (
        "\n<!-- Work View compacted to preserve required sections. -->\n"
        if compacted
        else ""
    )
    return f"""# FLG Source-backed Work View

## Freshness

- Status: fresh
- Block SHA-256: {block['sha256']}
- Generated: {_now()}

## Source

- Path: {config['path']}
- Locator: {_one_line(block['locator'], 320)}
- Authority: declared current-work source; this view does not create or review formal decisions.

## Current Action

- Status: {action_status}
- Action: {fields['current_action'] or '(not defined)'}

## Blockers

{_render_list(fields['blockers'], '(not recorded)')}

## Necessary Constraints

{_render_list(fields['constraints'], '(not recorded)')}

## Missing Information

{_render_list(fields['missing'], '(none detected)')}

## Expand On Demand

- Inspect the declared source at the path and locator above before rebuilding.
- Full FlowGrid context: `flg context --mode resume --budget 4000`

## Boundary

- Rebuild with `flg context --mode work` after reviewing a changed source block.
- Candidate judgments still require the normal report-only review and review/merge gate.
{note}"""


def build_work_view(
    root: Path,
    state: dict[str, Any] | None,
    budget: int = 1500,
) -> tuple[str, dict[str, Any]]:
    config = load_work_source(root, state)
    if config is None:
        raise ValueError(
            "No work source declared. Add work_source.path and optional "
            "start_marker/end_marker to .flg/state.json."
        )
    block = _source_block(config)
    fields = _extract_fields(block["text"])
    max_chars = max(1200, min(max(1, budget) * 4, 6000))
    content = _render(config, block, fields, compacted=False)
    truncated = False
    if len(content) > max_chars:
        fields = _extract_fields(block["text"], compact=True)
        content = _render(config, block, fields, compacted=True)
        truncated = True
    if len(content) > max_chars:
        raise ValueError(
            f"Work View required fields exceed the {max_chars}-character budget; increase --budget."
        )
    metadata = {
        "schema_version": WORK_VIEW_SCHEMA_VERSION,
        "generated_at": _now(),
        "source": {
            "path": config["path"],
            "start_marker": config["start_marker"],
            "end_marker": config["end_marker"],
            "locator": block["locator"],
            "block_sha256": block["sha256"],
            "start_line": block["start_line"],
            "end_line": block["end_line"],
        },
        "current_action": fields["current_action"],
        "blockers": fields["blockers"],
        "constraints": fields["constraints"],
        "missing": fields["missing"],
        "status": "fresh",
        "chars": len(content),
        "estimated_tokens": len(content) // 4,
        "truncated": truncated,
    }
    return content, metadata


def write_work_view_manifest(root: Path, metadata: dict[str, Any]) -> Path:
    path = root / WORK_VIEW_MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def inspect_work_view(root: Path, state: dict[str, Any] | None) -> dict[str, Any] | None:
    """Compare the generated view's block SHA with the current declared block."""
    config = load_work_source(root, state)
    if config is None:
        return None
    block = _source_block(config)
    path = root / WORK_VIEW_MANIFEST
    base = {
        "configured": True,
        "source_path": config["path"],
        "locator": block["locator"],
        "current_block_sha256": block["sha256"],
    }
    if not path.exists():
        return {
            **base,
            "status": "unbuilt",
            "action_status": "needs_recheck",
            "current_action": None,
            "blockers": [],
            "constraints": [],
            "missing": ["generated work view"],
            "reason": "Run `flg context --mode work` to create the first SHA-backed view.",
        }
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Work View manifest is corrupt: {path}") from exc
    if previous.get("schema_version") != WORK_VIEW_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported Work View manifest schema: {previous.get('schema_version')}"
        )
    old_source = previous.get("source") or {}
    config_changed = any(
        old_source.get(key) != config.get(key)
        for key in ("path", "start_marker", "end_marker")
    )
    stale = config_changed or old_source.get("block_sha256") != block["sha256"]
    return {
        **base,
        "status": "stale" if stale else "fresh",
        "action_status": (
            "needs_recheck"
            if stale
            else ("current" if previous.get("current_action") else "not_defined")
        ),
        "current_action": previous.get("current_action"),
        "blockers": previous.get("blockers") or [],
        "constraints": previous.get("constraints") or [],
        "missing": previous.get("missing") or [],
        "recorded_block_sha256": old_source.get("block_sha256"),
        "generated_at": previous.get("generated_at", "unknown"),
        "config_changed": config_changed,
        "reason": (
            "Declared source configuration or marked block changed; rebuild only "
            "after rechecking the source."
            if stale
            else "The declared source block matches the generated Work View SHA."
        ),
    }


def work_view_health_issues(root: Path, state: dict[str, Any] | None) -> list[str]:
    """Return opt-in work-view issues for ``flg doctor``."""
    if not state or "work_source" not in state:
        return []
    try:
        status = inspect_work_view(root, state)
    except (OSError, UnicodeError, ValueError) as exc:
        return [f"source-backed work view invalid: {exc}"]
    if status is None:
        return []
    if status["status"] == "unbuilt":
        return [
            "source-backed work view is unbuilt; review the source and run "
            "`flg context --mode work`"
        ]
    if status["status"] == "stale":
        return [
            "source-backed work view is stale; the declared source block changed "
            "and requires recheck"
        ]
    return []
