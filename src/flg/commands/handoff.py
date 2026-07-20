"""flg handoff command - Generate agent handoff summary."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown

from ..core.files import is_flg_project, read_file_safe
from ..core.patches import list_patches
from ..core.state import load_state
from .capture import _read_frontmatter

console = Console()


def _confirmed_decision_ids(root: Path) -> set[str]:
    """Return formal decision IDs from review evidence, not prose markers.

    DECISIONS.md remains human-editable and its headings do not carry an
    "accepted" token. The evidence index is the review record that tells a
    fresh host which entries reached confirmed project state.
    """
    index_path = root / ".flg" / "context" / "evidence_index.json"
    if not index_path.exists():
        return set()
    try:
        items = json.loads(index_path.read_text(encoding="utf-8")).get("items", {})
    except (OSError, json.JSONDecodeError, AttributeError):
        return set()
    return {
        decision_id
        for decision_id, item in items.items()
        if isinstance(item, dict) and item.get("status") == "confirmed"
    }


def parse_patch_for_handoff(content: str) -> dict:
    """Parse patch content for handoff summary."""
    info = {
        "patch_id": "",
        "source_command": "unknown",
        "risk_level": "unknown",
        "generated_at": "unknown",
        "status": "unknown",
        "decisions": [],
        "risks": [],
        "questions": [],
        "next_actions": [],
    }
    
    current_section = None
    current_decision = None
    
    for line in content.split("\n"):
        if line.startswith("patch_id:"):
            info["patch_id"] = line.split(":", 1)[1].strip()
        elif line.startswith("source_command:"):
            info["source_command"] = line.split(":", 1)[1].strip()
        elif line.startswith("risk_level:"):
            info["risk_level"] = line.split(":", 1)[1].strip()
        elif line.startswith("generated_at:"):
            info["generated_at"] = line.split(":", 1)[1].strip()
        elif line.startswith("status:") and not current_section:
            info["status"] = line.split(":", 1)[1].strip()

        # Detect section headers
        if line.startswith("## "):
            current_section = line[3:].strip()
            continue
        
        # Parse candidate decisions
        if current_section and "Candidate Decision" in current_section:
            if line.startswith("candidate_id:"):
                if current_decision:
                    current_decision["candidate_id"] = line.split(":", 1)[1].strip()
            elif line.startswith("status:"):
                if current_decision:
                    current_decision["status"] = line.split(":", 1)[1].strip()
            elif line.startswith("confidence:"):
                if current_decision:
                    current_decision["confidence"] = line.split(":", 1)[1].strip()
            elif line.startswith("decision_type:"):
                if current_decision:
                    current_decision["type"] = line.split(":", 1)[1].strip()
            elif line.startswith("why_this_is_a_decision:"):
                if current_decision:
                    current_decision["why"] = line.split(":", 1)[1].strip()
            elif line.startswith("source_excerpt:"):
                if current_decision:
                    current_decision["excerpt"] = line.split(":", 1)[1].strip().lstrip(">").strip()
            elif line.startswith("source_actor:"):
                if current_decision:
                    current_decision["source_actor"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("suggested_action:"):
                if current_decision:
                    current_decision["action"] = line.split(":", 1)[1].strip()
            # New bold-label fields from Phase 1 closeout output
            elif line.startswith("**What was decided:**"):
                if current_decision:
                    val = line.split(":", 1)[1].strip().lstrip("*").strip()
                    current_decision["what_decided"] = val
            elif line.startswith("**Why:**"):
                if current_decision:
                    val = line.split(":", 1)[1].strip().lstrip("*").strip()
                    current_decision["why"] = val
            elif line.startswith("**Alternatives mentioned:**"):
                if current_decision:
                    val = line.split(":", 1)[1].strip().lstrip("*").strip()
                    current_decision["alternatives"] = val
            elif line.startswith("**Rejected because:**"):
                if current_decision:
                    val = line.split(":", 1)[1].strip().lstrip("*").strip()
                    current_decision["rejected"] = val
            elif line.startswith("**Could reverse if:**"):
                if current_decision:
                    val = line.split(":", 1)[1].strip().lstrip("*").strip()
                    current_decision["reversal"] = val
            elif line.startswith("### Candidate Decision"):
                # New decision
                title = line.split(":", 1)[1].strip() if ":" in line else line
                current_decision = {
                    "title": title,
                    "candidate_id": "",
                    "status": "pending_review",
                    "confidence": "unknown",
                    "type": "unknown",
                    "what_decided": "",
                    "why": "",
                    "alternatives": "",
                    "rejected": "",
                    "reversal": "",
                    "excerpt": "",
                    "source_actor": "unknown",
                    "action": "needs_review",
                }
                info["decisions"].append(current_decision)
        
        # Parse risks
        elif current_section and "Risks" in current_section:
            if line.startswith("- ") and line != "- (none identified)":
                info["risks"].append(line[2:])
        
        # Parse open questions
        elif current_section and "Open Questions" in current_section:
            if line.startswith("- ") and line != "- (none identified)":
                info["questions"].append(line[2:])
        
        elif current_section and "Suggested Next Actions" in current_section:
            if line.startswith("- ") and line != "- (none identified)":
                info["next_actions"].append(line[2:])
    
    # Historical patches may predate candidate IDs. Derive a stable fallback
    # from their ordered position so reviews remain idempotent after upgrade.
    for index, decision in enumerate(info["decisions"], start=1):
        if not decision.get("candidate_id"):
            decision["candidate_id"] = f"{info['patch_id'] or 'unknown'}-c-{index:03d}"
    return info


def generate_handoff_summary(root: Path, format: str = "markdown") -> str:
    """Generate agent handoff summary."""
    # Load state
    state = load_state(root)
    if not state:
        return "Error: No FLG project found."
    
    project_name = state.get("project_name", "Unknown")
    current_stage = state.get("current_stage", "Unknown")
    created_at = state.get("created_at", "Unknown")
    
    # Read core files
    snapshot_content = read_file_safe(root / "SNAPSHOT.md") or ""
    framing_content = read_file_safe(root / "FRAMING.md") or ""
    decisions_content = read_file_safe(root / "DECISIONS.md") or ""
    progress_content = read_file_safe(root / "PROGRESS.md") or ""
    anchors_content = read_file_safe(root / "ANCHORS.md") or ""
    
    # NEW: Detect FRAMING.md field completeness for smarter handoff
    framing_fields_status = _detect_framing_completeness(framing_content)
    framing_is_complete = (
        framing_fields_status["filled_count"] == framing_fields_status["total_count"]
        and framing_fields_status["total_count"] > 0
    )
    
    # Read pending patches
    patches_dir = root / ".flg" / "patches"
    pending_patches = []
    all_decisions = []
    all_risks = []
    all_questions = []
    all_next_actions = []
    
    if patches_dir.exists():
        # Patch files remain on disk after rejection or supersession for audit.
        # Only pending patches belong in the next agent's active work state.
        pending_patch_metadata = [
            patch
            for patch in list_patches(root)
            if patch.get("status") == "pending_review"
        ]
        for patch in pending_patch_metadata:
            patch_file = patches_dir / patch["filename"]
            content = read_file_safe(patch_file)
            if content:
                patch_info = parse_patch_for_handoff(content)
                pending_patches.append({
                    "filename": patch_file.name,
                    "source_command": patch_info["source_command"],
                    "risk_level": patch_info["risk_level"],
                    "generated_at": patch_info["generated_at"],
                    "decisions": patch_info["decisions"],
                    "risks": patch_info["risks"],
                    "questions": patch_info["questions"],
                    "next_actions": patch_info["next_actions"],
                })
                all_decisions.extend(patch_info["decisions"])
                all_risks.extend(patch_info["risks"])
                all_questions.extend(patch_info["questions"])
                all_next_actions.extend(patch_info["next_actions"])

    # Real-time captures do not create a patch. They are still active project
    # state: a new agent must see inferred judgments before deciding whether to
    # promote, reject, or gather more evidence for them.
    captures_dir = root / ".flg" / "captures"
    if captures_dir.exists():
        for capture_file in sorted(captures_dir.glob("cap-*.md"), reverse=True):
            capture = _read_frontmatter(capture_file)
            if not capture or capture.get("status") != "pending_review":
                continue
            all_decisions.append(
                {
                    "title": capture.get("claim", capture_file.stem),
                    "status": "pending_review",
                    "confidence": capture.get("confidence", "unknown"),
                    "type": capture.get("type", "judgment"),
                    "what_decided": capture.get("claim", ""),
                    "why": capture.get("rationale", ""),
                    "alternatives": "; ".join(capture.get("alternatives", [])),
                    "rejected": "",
                    "reversal": capture.get("risks", ""),
                    "excerpt": capture.get("raw_evidence", ""),
                    "action": "needs_review",
                    "source": f"capture {capture.get('id', capture_file.stem)}",
                }
            )
            question = capture.get("question")
            if question and question != "(not specified)":
                all_questions.append(question)
    
    # SNAPSHOT.md is the project-level current truth. Surface its active goal,
    # priority, risks, and boundaries before falling back to generic CLI advice.
    current_goal = " ".join(_extract_markdown_section_lines(snapshot_content, "Current Core Goal")) or "(not defined)"
    current_priority = " ".join(
        _extract_markdown_section_lines(snapshot_content, "Next Highest Priority Action")
    )
    snapshot_risks = _extract_markdown_section_lines(snapshot_content, "Current Risks")
    snapshot_boundaries = _extract_markdown_section_lines(snapshot_content, "Do Not Misread")
    
    # NEW: If SNAPSHOT only has the default init template goal
    # (e.g. "Define project scope and goals for X"), fall back to FRAMING.md Goals.
    _DEFAULT_GOAL_HINT = "Define project scope and goals for"
    _DEFAULT_PRIORITY = "Run 'flg frame' to define project goals and boundaries"
    if current_goal == "(not defined)" or current_goal.startswith(_DEFAULT_GOAL_HINT):
        framing_goal = _extract_framing_goal(framing_content)
        if framing_goal != "(not defined)":
            current_goal = framing_goal
            # The init template's default next action is only meaningful before
            # framing exists. Do not let it override a completed FRAMING.md.
            if current_priority == _DEFAULT_PRIORITY:
                current_priority = ""

    # A pending closeout may carry the first meaningful project action before
    # framing is filled. Do not let the init template hide that action merely
    # because closeout no longer mutates SNAPSHOT.md before review.
    if current_priority == _DEFAULT_PRIORITY and all_next_actions:
        current_priority = ""
    
    # NEW: Pull Open Questions from FRAMING.md (in addition to patches)
    framing_questions = _extract_framing_questions(framing_content)
    if framing_questions:
        seen = set(q.lower().strip() for q in all_questions)
        for q in framing_questions:
            if q.lower().strip() not in seen:
                all_questions.append(q)
                seen.add(q.lower().strip())
    
    # Extract confirmed facts from core files. Formal decisions are selected
    # through review evidence, never by a title that happens to contain a
    # status word.
    confirmed_facts = []
    confirmed_decision_ids = _confirmed_decision_ids(root)
    
    # From SNAPSHOT
    in_confirmed = False
    for line in snapshot_content.split("\n"):
        if "Confirmed" in line and "##" in line:
            in_confirmed = True
            continue
        if in_confirmed:
            if line.startswith("## "):
                break
            if line.startswith("- ") and line != "- (none yet)":
                confirmed_facts.append(line[2:])
    
    # From DECISIONS
    for line in decisions_content.split("\n"):
        match = re.match(r"^##\s+(D-\d+)\b", line)
        if match and match.group(1) in confirmed_decision_ids:
            confirmed_facts.append(line.strip())
    
    recent_updated = created_at
    tracked_paths = [
        root / "PROJECT.md",
        root / "FRAMING.md",
        root / "SNAPSHOT.md",
        root / "DECISIONS.md",
        root / "PROGRESS.md",
    ]
    existing_times = [path.stat().st_mtime for path in tracked_paths if path.exists()]
    if existing_times:
        recent_updated = datetime.fromtimestamp(max(existing_times)).isoformat(timespec="seconds")

    # Build summary
    summary = f"""# FLG Handoff Summary

## 1. Project State

- **Project:** {project_name}
- **Stage:** {current_stage}
- **Current Goal:** {current_goal}
- **Created:** {created_at}
- **Last Updated:** {recent_updated}
- **Generated:** {datetime.now().isoformat(timespec="seconds")}

---

## 2. Confirmed Facts

"""
    if confirmed_facts:
        for fact in confirmed_facts[:10]:
            summary += f"- {fact}\n"
    else:
        summary += "(no confirmed facts yet)\n"
    
    # --- Authoritative Anchors from ANCHORS.md ---
    anchor_entries = _parse_anchors(anchors_content)
    if anchor_entries:
        summary += "\n## Authoritative Anchors\n\n"
        summary += "> 冲突时以存在且 active 的锚点文件为准。缺失锚点不能作为当前权威来源。\n\n"
        for entry in anchor_entries:
            anchor_path = _resolve_anchor_path(root, entry["file"])
            exists = anchor_path.exists()
            summary += f"### {entry['topic']}\n\n"
            summary += f"- **File:** `{entry['file']}`\n"
            summary += f"- **Status:** {'active' if exists else 'missing'}\n"
            summary += f"- **Role:** {entry['role']}\n"
            summary += f"- **Authority:** {entry['authority']}\n"
            summary += f"- **Provenance:** {entry['provenance']}\n"
            summary += f"- **Lifecycle:** {entry['lifecycle']}\n"
            if entry['notes']:
                summary += f"- **Notes:** {entry['notes']}\n"
            if not exists:
                summary += "- **Warning:** This anchor path is missing. Do not use it as current authority; repair ANCHORS.md first.\n"
            summary += "\n"
    else:
        summary += "\n## Authoritative Anchors\n\n"
        summary += "(no anchors defined — edit ANCHORS.md to add)\n"
    
    # --- Decision Context from DECISIONS.md ---
    decision_context_items = _extract_decisions_context(decisions_content, confirmed_decision_ids)
    if decision_context_items:
        summary += "\n## Decision Context (from DECISIONS.md)\n\n"
        for item in decision_context_items[:5]:
            summary += f"### {item['title']}\n\n"
            if item['what_decided']:
                summary += f"- **What was decided:** {item['what_decided']}\n"
            if item['why']:
                summary += f"- **Why:** {item['why']}\n"
            if item['alternatives']:
                summary += f"- **Alternatives mentioned:** {item['alternatives']}\n"
            if item['rejected']:
                summary += f"- **Rejected because:** {item['rejected']}\n"
            if item['reversal']:
                summary += f"- **Could reverse if:** {item['reversal']}\n"
            summary += "\n"
    
    summary += """
---

## 3. Pending Patches

"""
    if pending_patches:
        summary += f"**{len(pending_patches)} pending patch(es) found.**\n\n"
        for patch in pending_patches:
            summary += f"- `{patch['filename']}` | source: `{patch['source_command']}` | risk: `{patch['risk_level']}` | generated: `{patch['generated_at']}`\n"
    else:
        summary += "(no pending patches)\n"
    
    summary += """
---

## 4. Pending Candidate Decisions

"""
    if all_decisions:
        summary += f"**{len(all_decisions)} candidate decision(s) pending review.**\n\n"
        for i, d in enumerate(all_decisions[:5], 1):
            summary += f"### {i}. {d['title']}\n\n"
            summary += f"- **Status:** {d['status']}\n"
            summary += f"- **Confidence:** {d['confidence']}\n"
            if d.get("source"):
                summary += f"- **Source:** {d['source']}\n"
            if d['what_decided']:
                summary += f"- **What was decided:** {d['what_decided']}\n"
            if d['why']:
                summary += f"- **Why:** {d['why']}\n"
            elif d['type'] != "unknown":
                summary += f"- **Type:** {d['type']}\n"
            if d['alternatives']:
                summary += f"- **Alternatives mentioned:** {d['alternatives']}\n"
            if d['rejected']:
                summary += f"- **Rejected because:** {d['rejected']}\n"
            if d['reversal']:
                summary += f"- **Could reverse if:** {d['reversal']}\n"
            if d['excerpt']:
                summary += f"- **Source excerpt:** {d['excerpt']}\n"
            summary += "\n"
    else:
        summary += "(no candidate decisions)\n"
    
    summary += """
---

## 5. Open Questions

"""
    if all_questions:
        for q in all_questions[:5]:
            summary += f"- {q}\n"
    else:
        summary += "(no open questions)\n"
    
    summary += """
---

## 6. Risks

"""
    if all_risks:
        for r in all_risks[:3]:
            summary += f"- {r}\n"
    else:
        summary += "(no risks identified)\n"
    
    summary += """
---

## 7. Current Priority and Boundaries

"""
    if current_priority:
        summary += f"- **Highest priority (SNAPSHOT.md):** {current_priority}\n"
    else:
        summary += "- **Highest priority (SNAPSHOT.md):** (not defined)\n"

    if snapshot_risks:
        summary += "- **Current risks (SNAPSHOT.md):**\n"
        for risk in snapshot_risks[:3]:
            summary += f"  - {risk}\n"
    else:
        summary += "- **Current risks (SNAPSHOT.md):** (none declared)\n"

    if snapshot_boundaries:
        summary += "- **Do not (SNAPSHOT.md):**\n"
        for boundary in snapshot_boundaries[:3]:
            summary += f"  - {boundary}\n"
    else:
        summary += "- **Do not (SNAPSHOT.md):** (no project-specific boundary declared)\n"

    summary += """
---

## 8. Suggested Next Actions

"""
    if current_priority:
        summary += f"1. {current_priority}\n"
        if all_decisions:
            summary += "2. Process pending candidate decisions only after the current priority is addressed\n"
    elif all_next_actions:
        for idx, action in enumerate(all_next_actions[:5], 1):
            summary += f"{idx}. {action}\n"
    elif current_stage == "initialized" and not framing_is_complete:
        summary += "1. Run `flg frame` to define project goals and boundaries\n"
        summary += "2. Review and fill in FRAMING.md\n"
    elif framing_is_complete and not all_decisions and not pending_patches:
        # NEW: FRAMING is done — push user to session work
        summary += "1. FRAMING.md is complete — proceed with project work\n"
        summary += "2. Run `flg closeout --transcript <file>` at end of session\n"
    elif all_decisions:
        summary += "1. Process pending candidate decisions in the host background flow\n"
        summary += "2. Keep only material ambiguities pending; shell candidates stay out of formal state\n"
        summary += "3. Merge routine updates or discard a shell-only patch in the background\n"
        summary += "4. Continue project work from the updated ledger\n"
    else:
        summary += "1. Continue project work\n"
        summary += "2. Run `flg closeout` at end of session\n"
    
    summary += """
---

## 9. Do Not Misread

"""
    # Add warnings
    if all_decisions:
        summary += "- Pending candidate decisions are NOT confirmed facts\n"
        summary += "- The host should process them in the background; keep only material ambiguities pending\n"
    if all_risks:
        summary += "- Risks identified are from keyword matching, may need verification\n"
    
    summary += """
---

*This summary is generated for agent handoff. Read both formal ledger and pending patches to understand full project state.*
"""
    
    return summary


# ---------------------------------------------------------------------------
# FRAMING.md smart helpers (Goal 3 v0.1.7 handoff enhancement)
# These let handoff reflect FRAMING.md state instead of pretending it's empty.
# ---------------------------------------------------------------------------

# Mirror of frame.py REQUIRED_FIELDS, kept here to avoid circular import.
# Accept H2 or H3 for Explicit Requirements / Real Needs Hypothesis (见 frame.py 注释).
_FRAMING_REQUIRED_PATTERNS = [
    ("Problem Statement", r"##\s+Problem\s+Statement"),
    ("Explicit Requirements", r"#{2,3}\s+Explicit\s+Requirements"),
    ("Real Needs Hypothesis", r"#{2,3}\s+Real\s+Needs\s+Hypothesis"),
    ("Goals", r"##\s+Goals"),
    ("Non-Goals", r"##\s+Non-Goals"),
    ("User Objects", r"##\s+User\s+Objects"),
    ("Review Objects", r"##\s+Review\s+Objects"),
    ("Success Criteria", r"##\s+Success\s+Criteria"),
    ("Constraints", r"##\s+Constraints"),
    ("Open Questions", r"##\s+Open\s+Questions"),
]

_PLACEHOLDER_PATTERNS = [
    "(to be defined)",
    "(to be filled)",
    "(to be confirmed)",
    "(to be identified)",
    "(none yet)",
    "(to be hypothesized)",
]


def _detect_framing_completeness(framing_content: str) -> dict:
    """Return field-by-field fill status for FRAMING.md."""
    import re
    filled = []
    missing = []
    for field_name, pattern in _FRAMING_REQUIRED_PATTERNS:
        match = re.search(pattern, framing_content, re.IGNORECASE)
        is_filled = False
        if match:
            start = match.end()
            next_heading = re.search(r"^##\s+", framing_content[start:], re.MULTILINE)
            field_text = framing_content[start:start + next_heading.start()] if next_heading else framing_content[start:]
            stripped = field_text.strip()
            if stripped:
                is_filled = not any(p in stripped for p in _PLACEHOLDER_PATTERNS)
        if is_filled:
            filled.append(field_name)
        else:
            missing.append(field_name)
    return {
        "filled": filled,
        "missing": missing,
        "filled_count": len(filled),
        "total_count": len(_FRAMING_REQUIRED_PATTERNS),
    }


def _extract_framing_goal(framing_content: str) -> str:
    """Pull a one-line Current Goal summary from FRAMING.md's Goals section.

    Strategy:
    1. Skip bold labels (e.g. **Top 3 Goals:**) — these are sub-headers.
    2. Skip headings/placeholders/blank lines.
    3. Prefer the first bullet point; fall back to the first non-empty line.
    Returns "(not defined)" if no usable content is found.
    """
    import re
    match = re.search(r"##\s+Goals", framing_content, re.IGNORECASE)
    if not match:
        return "(not defined)"
    start = match.end()
    next_heading = re.search(r"^##\s+", framing_content[start:], re.MULTILINE)
    body = framing_content[start:start + next_heading.start()] if next_heading else framing_content[start:]
    first_bullet = None
    for raw in body.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            break
        if any(p in line for p in _PLACEHOLDER_PATTERNS):
            continue
        # Skip bold sub-headers like "**Top 3 Goals:**"
        if line.startswith("**") and line.endswith("**"):
            continue
        if line.startswith("- "):
            bullet = line[2:].strip()
            if bullet:
                if first_bullet is None:
                    first_bullet = bullet
                # keep scanning in case later bullet is shorter/summarized
        elif first_bullet is None:
            # Non-bullet line; only use it as fallback
            return line
    return first_bullet or "(not defined)"


def _extract_framing_questions(framing_content: str) -> list:
    """Pull Open Questions list from FRAMING.md (in addition to patch-sourced questions)."""
    import re
    match = re.search(r"##\s+Open\s+Questions", framing_content, re.IGNORECASE)
    if not match:
        return []
    start = match.end()
    next_heading = re.search(r"^##\s+", framing_content[start:], re.MULTILINE)
    body = framing_content[start:start + next_heading.start()] if next_heading else framing_content[start:]
    questions = []
    for raw in body.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            break
        if line.startswith("- "):
            q = line[2:].strip()
            if q and not any(p in q for p in _PLACEHOLDER_PATTERNS):
                questions.append(q)
    return questions


def _extract_markdown_section_lines(content: str, heading: str) -> list[str]:
    """Return meaningful lines from a level-two Markdown section.

    SNAPSHOT.md is intentionally human-editable, so this accepts bullets or
    plain prose and strips only structural/template noise.
    """
    import re

    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", content, re.MULTILINE)
    if not match:
        return []
    following = content[match.end():]
    next_heading = re.search(r"^##\s+", following, re.MULTILINE)
    body = following[:next_heading.start()] if next_heading else following

    ignored = {"(none identified)", "(none yet)", "(not defined)", "(to be filled)"}
    lines = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line == "---" or line.startswith("*Last Updated:"):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        if line.lower() in ignored:
            continue
        lines.append(line)
    return lines


def _extract_decisions_context(decisions_content: str, confirmed_ids: set[str] | None = None) -> list:
    """Extract confirmed decision context from DECISIONS.md.

    Returns a list of dicts with keys: title, what_decided, why, alternatives, rejected, reversal.
    Each DECISIONS.md entry is expected to have headings like:
        ## D-001 | Title
        ### 最终决策
        ### 决策理由
        ### 备选方案
        ### 放弃理由
        ### 复盘入口
    """
    import re
    items = []
    # Split by ## D- headings
    blocks = re.split(r"(?=^## D-)", decisions_content, flags=re.MULTILINE)
    for block in blocks:
        title_match = re.match(r"^## (D-\d+\s*\|.*)", block, re.MULTILINE)
        if not title_match:
            continue
        title = title_match.group(1).strip()
        decision_id = title.split("|", 1)[0].strip()
        # New ledgers use review evidence. Keep the legacy text-marker fallback
        # only when no evidence index exists.
        if confirmed_ids is not None:
            if decision_id not in confirmed_ids:
                continue
        elif "accepted" not in block.lower() and "confirmed" not in block.lower():
            continue

        def _extract_subsection(heading: str) -> str:
            pattern = rf"###\s+{re.escape(heading)}\s*\n([\s\S]*?)(?=\n###\s|\n##\s|\Z)"
            m = re.search(pattern, block)
            if m:
                text = m.group(1).strip()
                # Strip placeholder patterns
                if text and not any(p in text for p in _PLACEHOLDER_PATTERNS):
                    return text
            return ""

        item = {
            "title": title,
            "what_decided": _extract_subsection("最终决策"),
            "why": _extract_subsection("决策理由"),
            "alternatives": _extract_subsection("备选方案"),
            "rejected": _extract_subsection("放弃理由"),
            "reversal": _extract_subsection("复盘入口"),
        }
        # Only include if at least one field has content
        if any(item[k] for k in ("what_decided", "why", "alternatives", "rejected", "reversal")):
            items.append(item)
    return items


def handoff_command(
    format: str = typer.Option("markdown", "--format", "-f", help="Output format (markdown)"),
) -> None:
    """Generate agent handoff summary."""
    root = Path.cwd()
    
    # Check if this is a FLG project
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)
    
    # Generate summary
    summary = generate_handoff_summary(root, format)
    
    # Output
    if format == "markdown":
        console.print(Markdown(summary))
    else:
        console.print(summary)


def _parse_anchors(anchors_content: str) -> list:
    """Parse ANCHORS.md content into structured anchor entries.

    Returns a list of dicts with keys: topic, file, role, authority, provenance, lifecycle, notes.
    """
    import re
    entries = []

    # Split by ### headings (each anchor entry)
    blocks = re.split(r"(?=^### )", anchors_content, flags=re.MULTILINE)
    for block in blocks:
        # Match ### [Topic Name]
        topic_match = re.match(r"^### (.+)", block, re.MULTILINE)
        if not topic_match:
            continue
        topic = topic_match.group(1).strip()
        # Skip the template placeholder
        if topic.startswith("[") and topic.endswith("]"):
            continue

        def _extract_field(field_name: str) -> str:
            pattern = rf"\*\*{re.escape(field_name)}:\*\*\s*(.+)"
            m = re.search(pattern, block)
            if m:
                val = m.group(1).strip().strip("`")
                # Strip placeholder parentheses
                if val.startswith("(") and val.endswith(")"):
                    return ""
                return val
            return ""

        entry = {
            "topic": topic,
            "file": _extract_field("File"),
            "role": _extract_field("Role"),
            "authority": _extract_field("Authority"),
            "provenance": _extract_field("Provenance"),
            "lifecycle": _extract_field("Lifecycle"),
            "notes": _extract_field("Notes"),
        }
        # Only include entries that have at least a file path
        if entry["file"]:
            entries.append(entry)

    return entries


def _resolve_anchor_path(root: Path, anchor_file: str) -> Path:
    """Resolve relative anchors against the ledger root for health checks."""
    path = Path(anchor_file).expanduser()
    return path if path.is_absolute() else root / path
