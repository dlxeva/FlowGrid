"""Bounded, read-only source discovery; never establishes authorship or truth.

Paths and inferred meeting IDs are project-relative POSIX strings; explicit
meeting IDs are opaque labels. Filename roles are hints only. A meeting groups
related artifacts, not independent
corroboration. JSON/XML are metadata_only and raw responses are not reviewable.
Invalid configuration raises ValueError before discovery. Missing, excluded,
unsafe or unreadable files are omitted; exceeding a budget raises ValueError
instead of returning a misleading partial inventory. No contents are returned.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


MAX_ROOTS = 64
MAX_ENTRIES = 20_000
MAX_FILES = 4_096
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
ROLES = frozenset({"transcript", "manual_notes", "smart_summary", "raw_response"})
_EXTENSIONS = frozenset({".md", ".txt", ".json", ".xml"})
_EXCLUDED = frozenset({
    "people", "audit", "audits", "cache", "caches", "__pycache__",
    "tmp", "temp", "temporary", "build", "dist", "target", "out",
    "node_modules", "vendor", "venv", "env", "coverage", "htmlcov",
    "人物", "审计", "缓存", "临时",
})
_DEFAULT_ROOTS = (
    {"path": ".flg/sessions", "max_depth": 0},
    {"path": "docs/meetings", "max_depth": 0},
    {"path": "sources/meetings", "max_depth": 3},
)
_ROLE_HINTS = (
    ("raw_response", r"raw[ _-]*response|原始响应|原始回复|模型回复|模型响应"),
    ("smart_summary", r"smart[ _-]*summary|ai[ _-]*summary|智能纪要|智能总结|智能摘要|妙记|自动纪要"),
    ("transcript", r"transcript|transcription|逐字稿|转写|转录"),
    ("manual_notes", r"manual[ _-]*notes|meeting[ _-]*notes|notes|minutes|手写|手工|人工纪要|会议纪要|笔记"),
)


@dataclass(frozen=True)
class _SourceRoot:
    path: PurePosixPath
    max_depth: int
    role: str | None
    meeting_id: str | None


def _control(value: str) -> bool:
    return any(unicodedata.category(char).startswith("C") for char in value)


def _relative(value: Any) -> PurePosixPath:
    """Validate both Windows and POSIX spellings on either platform."""
    if not isinstance(value, (str, Path)):
        raise ValueError("Source path must be a project-relative path.")
    text = str(value).replace("\\", "/")
    parts = text.split("/")
    if not text or _control(text) or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("Source path must be nonempty and cannot contain traversal.")
    for part in parts:
        if (any(char in part for char in ':*?"<>|') or part.endswith((" ", "."))
                or re.fullmatch(r"(?:con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", part, re.I)):
            raise ValueError("Source path is not a portable regular-file path.")
    return PurePosixPath(text)


def _excluded(path: PurePosixPath) -> bool:
    for index, part in enumerate(path.parts):
        name = part.casefold()
        if index == 0 and name == ".flg":
            continue
        if (name.startswith((".", "~", "#")) or name.endswith(("~", ".tmp", ".temp", ".bak", ".swp"))
                or name in _EXCLUDED
                or re.search(r"(?:^|[._-])(?:tmp|temp|temporary)(?:[._-]|$)", name)):
            return True
    return False


def _roots(config: dict | None) -> list[_SourceRoot]:
    if config is None:
        declarations = list(_DEFAULT_ROOTS)
    else:
        if (not isinstance(config, dict) or type(config.get("version")) is not int
                or config["version"] != 1 or set(config) - {"version", "roots"}
                or not isinstance(config.get("roots"), list)):
            raise ValueError("Expected source config version 1 with a roots list.")
        declarations = config["roots"]
    if len(declarations) > MAX_ROOTS:
        raise ValueError("Source root budget exceeded.")
    roots: list[_SourceRoot] = []
    for item in declarations:
        if not isinstance(item, dict) or set(item) - {"path", "max_depth", "role", "meeting_id"}:
            raise ValueError("Invalid source root declaration.")
        path = _relative(item.get("path"))
        if _excluded(path) or path == PurePosixPath(".flg"):
            raise ValueError("Excluded directories cannot be source roots.")
        depth = item.get("max_depth")
        if type(depth) is not int or not 0 <= depth <= 4:
            raise ValueError("Source max_depth must be an integer between 0 and 4.")
        role = item.get("role")
        if role is not None and (not isinstance(role, str) or role not in ROLES):
            raise ValueError("Unknown source role.")
        meeting = item.get("meeting_id")
        if meeting is not None and (not isinstance(meeting, str) or not meeting.strip() or _control(meeting)):
            raise ValueError("meeting_id must be a nonempty string without controls.")
        candidate = _SourceRoot(path, depth, role, meeting)
        for other in roots:
            # Case-insensitive comparison prevents Windows-only collisions.
            left, right = path.as_posix().casefold(), other.path.as_posix().casefold()
            if left == right:
                if candidate != other:
                    raise ValueError("Conflicting duplicate source roots.")
            else:
                parent, child = sorted((other, candidate), key=lambda entry: len(entry.path.parts))
                parent_parts = tuple(p.casefold() for p in parent.path.parts)
                child_parts = tuple(p.casefold() for p in child.path.parts)
                intersects = (child_parts[:len(parent_parts)] == parent_parts
                              and len(child_parts) - len(parent_parts) <= parent.max_depth)
                if intersects and (candidate.role, candidate.meeting_id) != (other.role, other.meeting_id):
                    raise ValueError("Conflicting overlapping source roots.")
        if candidate not in roots:
            roots.append(candidate)
    return sorted(roots, key=lambda entry: entry.path.as_posix())


def _project(root: Path) -> Path:
    root = Path(root).absolute()
    for component in (root, *root.parents):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Project root cannot contain a symlink or reparse point.")
    return root.resolve()


def _safe_stat(root: Path, relative: PurePosixPath) -> os.stat_result | None:
    current = root
    try:
        for index, part in enumerate(relative.parts):
            current = current / part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                return None  # Also exclude Windows junctions/reparse points.
            if index < len(relative.parts) - 1 and not stat.S_ISDIR(info.st_mode):
                return None
        return info
    except OSError:
        return None


def _open_directory(root: Path, parts: tuple[str, ...]) -> int:
    """Pin directory ancestry without following links (POSIX only)."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(root, flags)
    try:
        for part in parts:
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _signature(info: os.stat_result) -> tuple:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _digest(root: Path, relative: PurePosixPath) -> tuple[str, int] | None:
    before = _safe_stat(root, relative)
    if before is None or not stat.S_ISREG(before.st_mode):
        return None
    if before.st_size > MAX_FILE_BYTES:
        raise ValueError("Source file byte budget exceeded.")
    fd = None
    directory_fd = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        if os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW"):
            # Pin each directory on POSIX, including while opening the leaf.
            directory_fd = _open_directory(root, relative.parts[:-1])
            fd = os.open(relative.name, flags, dir_fd=directory_fd)
        else:
            fd = os.open(root.joinpath(*relative.parts), flags)
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            return None
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(fd, min(65536, MAX_FILE_BYTES + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise ValueError("Source file byte budget exceeded.")
            digest.update(chunk)
        after = _safe_stat(root, relative)
        final = os.fstat(fd)
        if after is None or _signature(before) != _signature(final) or _signature(final) != _signature(after):
            return None
        return digest.hexdigest(), size
    except OSError:
        return None
    finally:
        if fd is not None:
            os.close(fd)
        if directory_fd is not None:
            os.close(directory_fd)


def _matches(relative: PurePosixPath, roots: list[_SourceRoot]) -> list[_SourceRoot]:
    matches = []
    for source in roots:
        try:
            child = relative.relative_to(source.path)
        except ValueError:
            continue
        if 1 <= len(child.parts) <= source.max_depth + 1:
            matches.append(source)
    return matches


def _metadata(relative: PurePosixPath, matches: list[_SourceRoot], sha256: str) -> dict:
    source = matches[0]
    if relative.suffix.casefold() in {".json", ".xml"}:
        role, role_basis = "metadata_only", "extension"
    elif source.role is not None:
        role, role_basis = source.role, "config"
    else:
        role, role_basis = "manual_notes", "fallback_inference"
        for inferred_role, pattern in _ROLE_HINTS:
            if re.search(pattern, relative.stem, re.I):
                role, role_basis = inferred_role, "filename_inference"
                break
    meeting_id = source.meeting_id if source.meeting_id is not None else relative.parent.as_posix()
    return {
        "sha256": sha256,
        "role": role,
        "review_eligible": role in {"transcript", "manual_notes", "smart_summary"},
        "meeting_id": meeting_id,
        "role_basis": role_basis,
        "group_basis": "config" if source.meeting_id is not None else "folder",
        "source_roots": sorted(source.path.as_posix() for source in matches),
    }


def describe(root: Path, path: str | Path, config: dict | None = None) -> dict | None:
    """Hash exactly one relative, in-scope regular file, without scanning siblings.

    Invalid configuration raises ValueError. An invalid/excluded/out-of-scope
    target returns None. role_basis describes inference, never authorship.
    """
    roots = _roots(config)
    project = _project(root)
    try:
        relative = _relative(path)
    except ValueError:
        return None
    if _excluded(relative) or relative.suffix.casefold() not in _EXTENSIONS:
        return None
    matches = _matches(relative, roots)
    if not matches:
        return None
    result = _digest(project, relative)
    return _metadata(relative, matches, result[0]) if result is not None else None


def inventory(root: Path, config: dict | None = None) -> dict:
    """Discover declared source trees only; depth zero means direct files.

    Identical declarations coalesce. Overlapping declarations may share files
    only with identical role/meeting settings. Custom roots replace defaults.
    Budgets are fixed module constants; configuration cannot widen them.
    """
    roots = _roots(config)
    project = _project(root)
    candidates: set[PurePosixPath] = set()
    visited: set[PurePosixPath] = set()
    entries = 0

    def walk(directory: PurePosixPath, remaining: int) -> None:
        nonlocal entries
        info = _safe_stat(project, directory)
        if info is None or not stat.S_ISDIR(info.st_mode):
            return
        directory_fd = None
        try:
            if os.open in os.supports_dir_fd and os.scandir in os.supports_fd and hasattr(os, "O_NOFOLLOW"):
                directory_fd = _open_directory(project, directory.parts)
                target = directory_fd
            else:
                target = project.joinpath(*directory.parts)
            with os.scandir(target) as scan:
                children = []
                for entry in scan:
                    entries += 1
                    if entries > MAX_ENTRIES:
                        raise ValueError("Source entry budget exceeded.")
                    children.append(entry.name)
        except OSError:
            return
        finally:
            if directory_fd is not None:
                os.close(directory_fd)
        for name in sorted(children):
            child = directory / name
            try:
                _relative(child.as_posix())
            except ValueError:
                continue
            if _excluded(child):
                continue
            info = _safe_stat(project, child)
            if info is None:
                continue
            if stat.S_ISDIR(info.st_mode) and remaining:
                walk(child, remaining - 1)
            elif stat.S_ISREG(info.st_mode) and child.suffix.casefold() in _EXTENSIONS:
                candidates.add(child)
                if len(candidates) > MAX_FILES:
                    raise ValueError("Source file count budget exceeded.")

    for source in roots:
        # Distinct overlapping roots still need their own depth limits.
        if source.path not in visited:
            walk(source.path, source.max_depth)
            visited.add(source.path)
    files: dict[str, dict] = {}
    meetings: dict[str, dict] = {}
    total_bytes = 0
    for relative in sorted(candidates, key=lambda path: path.as_posix()):
        info = _safe_stat(project, relative)
        if info is not None and total_bytes + info.st_size > MAX_TOTAL_BYTES:
            raise ValueError("Source total byte budget exceeded.")
        result = _digest(project, relative)
        if result is None:
            continue
        sha256, size = result
        total_bytes += size
        if total_bytes > MAX_TOTAL_BYTES:
            raise ValueError("Source total byte budget exceeded.")
        metadata = _metadata(relative, _matches(relative, roots), sha256)
        path = relative.as_posix()
        files[path] = metadata
        meeting = meetings.setdefault(metadata["meeting_id"], {"paths": [], "review_paths": []})
        meeting["paths"].append(path)
        if metadata["review_eligible"]:
            meeting["review_paths"].append(path)
    return {"version": 1, "files": files, "meetings": dict(sorted(meetings.items()))}


__all__ = ["inventory", "describe"]
