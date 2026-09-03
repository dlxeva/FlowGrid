"""Opt-in project wiki indexing for FlowGrid continuity."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

WIKI_CONFIG = ".flg/wiki.json"
WIKI_MANIFEST = ".flg/context/wiki_manifest.json"
WIKI_SCHEMA_VERSION = "1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _inside_project(root: Path, candidate: Path) -> Path:
    project = root.resolve()
    resolved = candidate.resolve()
    if resolved != project and project not in resolved.parents:
        raise ValueError(f"Wiki path must stay inside the project: {candidate}")
    return resolved


def _relative_project_path(root: Path, value: str, *, must_exist: bool = False) -> Path:
    raw = Path(value).expanduser()
    candidate = raw if raw.is_absolute() else root / raw
    resolved = _inside_project(root, candidate)
    if must_exist and not resolved.exists():
        raise ValueError(f"Wiki path does not exist: {value}")
    return resolved


def load_wiki_config(root: Path) -> dict[str, Any] | None:
    path = root / WIKI_CONFIG
    if not path.exists():
        return None
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Wiki config is corrupt: {path}") from exc
    if config.get("schema_version") != WIKI_SCHEMA_VERSION:
        raise ValueError(f"Unsupported wiki schema version: {config.get('schema_version')}")
    wiki_root = _relative_project_path(root, str(config.get("root", "")), must_exist=True)
    if not wiki_root.is_dir():
        raise ValueError(f"Wiki root is not a directory: {config.get('root')}")
    home = _relative_project_path(root, str(config.get("home", "")), must_exist=True)
    if not home.is_file() or home.suffix.lower() != ".md":
        raise ValueError(f"Wiki home must be a Markdown file: {config.get('home')}")
    if wiki_root != home.parent and wiki_root not in home.parents:
        raise ValueError("Wiki home must be inside the configured wiki root.")
    return config


def init_wiki(root: Path, wiki_root: str = "docs", home: str = "docs/README.md") -> dict[str, Any]:
    root = root.resolve()
    if not (root / ".flg" / "state.json").exists():
        raise ValueError("No FLG project found. Run 'flg init' first.")
    resolved_root = _relative_project_path(root, wiki_root, must_exist=True)
    resolved_home = _relative_project_path(root, home, must_exist=True)
    if not resolved_root.is_dir():
        raise ValueError(f"Wiki root is not a directory: {wiki_root}")
    if not resolved_home.is_file() or resolved_home.suffix.lower() != ".md":
        raise ValueError(f"Wiki home must be a Markdown file: {home}")
    if resolved_root != resolved_home.parent and resolved_root not in resolved_home.parents:
        raise ValueError("Wiki home must be inside the configured wiki root.")

    config = {
        "schema_version": WIKI_SCHEMA_VERSION,
        "root": resolved_root.relative_to(root).as_posix(),
        "home": resolved_home.relative_to(root).as_posix(),
        "include": ["**/*.md"],
        "authority": "reference",
        "created_at": _now(),
    }
    # Validate the full source tree before publishing configuration. A failed
    # initialization must not leave a config that blocks every future context run.
    scan_wiki(root, config)

    path = root / WIKI_CONFIG
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return config


def _frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    closing = text.find("\n---\n", 4)
    if closing < 0:
        return {}, text
    try:
        parsed = yaml.safe_load(text[4:closing]) or {}
    except yaml.YAMLError:
        parsed = {}
    return (parsed if isinstance(parsed, dict) else {}), text[closing + 5 :]


def _bounded_line(value: Any, limit: int = 160) -> str:
    """Normalize untrusted page metadata to bounded single-line text."""
    compact = re.sub(r"\s+", " ", str(value or "")).strip()
    compact = compact.replace("|", "\\|")
    return compact[:limit]


def _as_list(value: Any, *, limit: int = 12, item_limit: int = 80) -> list[str]:
    if value is None:
        raw: list[Any] = []
    elif isinstance(value, list):
        raw = value
    elif isinstance(value, str):
        raw = value.split(",")
    else:
        raw = [value]
    return [item for item in (_bounded_line(value, item_limit) for value in raw) if item][:limit]


def _page_id(path: str, metadata: dict[str, Any]) -> str:
    explicit = _bounded_line(metadata.get("id", ""), 80)
    if explicit:
        return explicit
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:10]
    return f"W-{digest}"


def _title(body: str, path: Path) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", body, flags=re.MULTILINE)
    return match.group(1).strip() if match else path.stem


def _page_record(root: Path, path: Path) -> dict[str, Any]:
    resolved = _inside_project(root, path)
    text = resolved.read_text(encoding="utf-8")
    metadata, body = _frontmatter(text)
    rel = resolved.relative_to(root.resolve()).as_posix()
    return {
        "id": _page_id(rel, metadata),
        "path": rel,
        "title": _bounded_line(metadata.get("title") or _title(body, resolved), 160),
        "type": _bounded_line(metadata.get("type", "page"), 40),
        "status": _bounded_line(metadata.get("status", "active"), 40),
        "authority": _bounded_line(metadata.get("authority", "reference"), 40),
        "owner": _bounded_line(metadata.get("owner", ""), 80),
        "related_decisions": _as_list(metadata.get("related_decisions")),
        "related_outcomes": _as_list(metadata.get("related_outcomes")),
        "source_ids": _as_list(metadata.get("source_ids")),
        "last_reviewed": _bounded_line(metadata.get("last_reviewed", ""), 40),
        "review_after": _bounded_line(metadata.get("review_after", ""), 40),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "size": len(text.encode("utf-8")),
        "modified_at": datetime.fromtimestamp(resolved.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
    }


def scan_wiki(root: Path, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    config = config or load_wiki_config(root)
    if config is None:
        return []
    wiki_root = _relative_project_path(root, config["root"], must_exist=True)
    pages: list[dict[str, Any]] = []
    seen_ids: dict[str, str] = {}
    for path in sorted(wiki_root.rglob("*.md")):
        if path.is_symlink():
            raise ValueError(f"Symlinked wiki pages are not supported: {path.relative_to(root)}")
        if path.is_file():
            page = _page_record(root, path)
            previous = seen_ids.get(page["id"])
            if previous:
                raise ValueError(f"Duplicate wiki page id {page['id']}: {previous}, {page['path']}")
            seen_ids[page["id"]] = page["path"]
            pages.append(page)
    return pages


def load_wiki_manifest(root: Path) -> dict[str, Any] | None:
    path = root / WIKI_MANIFEST
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Wiki manifest is corrupt: {path}") from exc


def _config_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": config.get("schema_version"),
        "root": config.get("root"),
        "home": config.get("home"),
        "include": config.get("include", ["**/*.md"]),
        "authority": config.get("authority", "reference"),
    }


def compare_wiki(root: Path) -> dict[str, Any]:
    config = load_wiki_config(root)
    if config is None:
        return {"configured": False, "status": "not_configured", "added": [], "changed": [], "removed": [], "pages": []}
    pages = scan_wiki(root, config)
    old = load_wiki_manifest(root)
    if old is None:
        return {"configured": True, "status": "unbuilt", "added": [p["path"] for p in pages], "changed": [], "removed": [], "pages": pages}
    previous = {page["path"]: page for page in old.get("pages", [])}
    current = {page["path"]: page for page in pages}
    added = sorted(set(current) - set(previous))
    removed = sorted(set(previous) - set(current))
    changed = sorted(path for path in set(current) & set(previous) if current[path].get("sha256") != previous[path].get("sha256"))
    config_changed = old.get("config") != _config_snapshot(config)
    status = "fresh" if not (added or changed or removed or config_changed) else "stale"
    return {
        "configured": True,
        "status": status,
        "added": added,
        "changed": changed,
        "removed": removed,
        "config_changed": config_changed,
        "pages": pages,
    }


def wiki_health_issues(root: Path) -> list[str]:
    """Return actionable opt-in Wiki continuity issues for doctor."""
    if not (root / WIKI_CONFIG).exists():
        return []
    try:
        comparison = compare_wiki(root)
    except (OSError, ValueError) as exc:
        return [f"wiki continuity invalid: {exc}"]
    if comparison["status"] == "unbuilt":
        return ["wiki manifest is missing; run wiki build after validating sources"]
    if comparison["status"] == "stale":
        return [
            "wiki manifest is stale: "
            f"{len(comparison['added'])} added, "
            f"{len(comparison['changed'])} changed, "
            f"{len(comparison['removed'])} removed, "
            f"config_changed={bool(comparison.get('config_changed'))}"
        ]
    return []


def build_wiki_manifest(root: Path) -> dict[str, Any]:
    config = load_wiki_config(root)
    if config is None:
        raise ValueError("Wiki is not configured. Run 'flg wiki init' first.")
    pages = scan_wiki(root, config)
    manifest = {
        "schema_version": WIKI_SCHEMA_VERSION,
        "generated_at": _now(),
        "root": config["root"],
        "home": config["home"],
        "config": _config_snapshot(config),
        "page_count": len(pages),
        "pages": pages,
    }
    path = root / WIKI_MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def wiki_context_summary(root: Path, decision_ids: set[str] | None = None, limit: int = 8) -> dict[str, Any] | None:
    config = load_wiki_config(root)
    if config is None:
        return None
    comparison = compare_wiki(root)
    manifest = load_wiki_manifest(root)
    pages = list((manifest or {}).get("pages", []))
    decision_ids = decision_ids or set()
    selected: list[dict[str, Any]] = []

    for page in pages:
        if page.get("path") == config["home"]:
            selected.append(page)
    for page in pages:
        if page in selected:
            continue
        if set(page.get("related_decisions", [])) & decision_ids:
            selected.append(page)
        if len(selected) >= limit:
            break
    if len(selected) < min(limit, 4):
        for page in pages:
            if page not in selected and page.get("type") in {"index", "overview", "hub"}:
                selected.append(page)
            if len(selected) >= limit:
                break

    return {
        "status": comparison["status"],
        "root": config["root"],
        "home": config["home"],
        "page_count": len(pages),
        "manifest": WIKI_MANIFEST,
        "added_count": len(comparison["added"]),
        "changed_count": len(comparison["changed"]),
        "removed_count": len(comparison["removed"]),
        "config_changed": bool(comparison.get("config_changed")),
        "pages": selected[:limit],
    }
