"""File operations for Framing Ledger."""

import hashlib
import os
from pathlib import Path
from typing import Optional


def is_flg_project(path: Path) -> bool:
    """Check if the given path is a FLG project."""
    return (
        (path / ".flg").is_dir()
        and (path / ".flg" / "state.json").exists()
        and (path / ".flg" / "CONTRACT.md").exists()
    )


def get_project_root() -> Path:
    """Get the current directory as project root."""
    return Path.cwd()


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    if not filepath.exists():
        return ""
    content = filepath.read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]


def safe_write(filepath: Path, content: str, force: bool = False) -> bool:
    """Write content to file. Returns True if written, False if skipped."""
    if filepath.exists() and not force:
        return False
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    return True


def ensure_dir(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def list_project_files(root: Path) -> list[dict]:
    """List all markdown and json files in the project."""
    files = []
    for ext in ["*.md", "*.json"]:
        for f in root.rglob(ext):
            # Skip .flg internal files
            if ".flg" in f.parts:
                continue
            rel = f.relative_to(root)
            files.append({
                "path": str(rel),
                "hash": compute_file_hash(f),
                "size": f.stat().st_size,
            })
    return files


def read_file_safe(filepath: Path) -> Optional[str]:
    """Read file content, return None if not exists."""
    if not filepath.exists():
        return None
    return filepath.read_text(encoding="utf-8")
