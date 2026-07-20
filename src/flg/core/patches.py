"""Patch generation for Framing Ledger."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from .files import read_file_safe


def generate_patch_id(prefix: str) -> str:
    """Generate a unique patch ID."""
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    random_suffix = hashlib.md5(str(now.timestamp()).encode()).hexdigest()[:6]
    return f"{prefix}-{timestamp}-{random_suffix}"


def create_patch(root: Path, patch_id: str, content: str) -> Path:
    """Create a patch file in .flg/patches/."""
    patches_dir = root / ".flg" / "patches"
    patches_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{patch_id}.patch.md"
    patch_path = patches_dir / filename
    patch_path.write_text(content, encoding="utf-8")
    return patch_path


def list_patches(root: Path) -> list[dict]:
    """List patch metadata using only the patch header lifecycle state."""
    patches_dir = root / ".flg" / "patches"
    if not patches_dir.exists():
        return []
    
    patches = []
    for f in sorted(patches_dir.glob("*.patch.md")):
        content = f.read_text(encoding="utf-8")
        # Extract basic info from patch
        patch_info = {
            "filename": f.name,
            "path": str(f),
            "size": f.stat().st_size,
        }
        # Header fields define patch lifecycle. Candidate decision blocks may
        # contain their own status lines and must not overwrite patch status.
        for line in content.split("\n"):
            if line.strip() == "---":
                break
            if line.startswith("patch_id:"):
                patch_info["patch_id"] = line.split(":", 1)[1].strip()
            elif line.startswith("status:"):
                patch_info["status"] = line.split(":", 1)[1].strip()
            elif line.startswith("risk_level:"):
                patch_info["risk_level"] = line.split(":", 1)[1].strip()
            elif line.startswith("source_command:"):
                patch_info["source_command"] = line.split(":", 1)[1].strip()
            elif line.startswith("generated_at:"):
                patch_info["generated_at"] = line.split(":", 1)[1].strip()
        
        patches.append(patch_info)
    
    return patches


def resolve_managed_patch(root: Path, reference: str) -> Optional[Path]:
    """Resolve a patch reference without permitting writes outside .flg/patches.

    Lifecycle and merge commands mutate their patch artifact. Accepting an
    arbitrary existing path here would allow an agent to overwrite unrelated
    project files, so every accepted path must resolve inside the managed patch
    directory and retain the expected extension and header.
    """
    patches_dir = (root / ".flg" / "patches").resolve()
    if not patches_dir.is_dir():
        return None

    supplied = Path(reference)
    candidates: list[Path] = []
    if supplied.is_absolute():
        candidates.append(supplied)
    else:
        candidates.extend((root / supplied, patches_dir / supplied, patches_dir / f"{reference}.patch.md"))

    for candidate in candidates:
        if not candidate.exists():
            continue
        resolved = candidate.resolve()
        if resolved.suffixes[-2:] != [".patch", ".md"]:
            continue
        try:
            resolved.relative_to(patches_dir)
        except ValueError:
            continue
        content = read_file_safe(resolved) or ""
        if "patch_id:" not in content or "status:" not in content:
            continue
        return resolved

    # A patch ID is resolved only by inspecting managed patch files.
    for candidate in patches_dir.glob("*.patch.md"):
        content = read_file_safe(candidate) or ""
        for line in content.splitlines():
            if line.startswith("patch_id:") and line.split(":", 1)[1].strip() == reference:
                return candidate.resolve()
    return None
