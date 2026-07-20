"""Small cross-process safeguards for multi-file FlowGrid operations."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path


def atomic_write_text(path: Path, content: str) -> None:
    """Replace one UTF-8 text file without leaving a partial write behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


@contextmanager
def project_operation_lock(root: Path, timeout_seconds: float = 5.0):
    """Serialize review and merge writes across local agent processes."""
    lock_dir = root / ".flg" / ".operation.lock"
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            lock_dir.mkdir(parents=False)
            (lock_dir / "owner").write_text(
                f"pid={os.getpid()}\nstarted_at={time.time()}\n", encoding="utf-8"
            )
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "Another FlowGrid review or merge is already writing this project. Retry after it finishes."
                )
            time.sleep(0.05)
    try:
        yield
    finally:
        shutil.rmtree(lock_dir, ignore_errors=True)


def serialized_project_operation(func):
    """Decorate a CLI command that mutates one project's formal state."""
    @wraps(func)
    def wrapped(*args, **kwargs):
        root = Path.cwd()
        # Let the command itself report a normal "not a FLG project" error.
        if not (root / ".flg").is_dir():
            return func(*args, **kwargs)
        with project_operation_lock(root):
            return func(*args, **kwargs)
    return wrapped
