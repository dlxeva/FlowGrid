"""Patch generation for Framing Ledger."""

import hashlib
from datetime import datetime
from pathlib import Path


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
    """List all pending patches."""
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
        # Try to extract patch_id and status
        for line in content.split("\n"):
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
