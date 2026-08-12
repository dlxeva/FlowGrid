"""Resolve one safe, source-backed current action for continuation artifacts."""

from __future__ import annotations

import re
from typing import Any, Iterable


ACTION_HEADINGS = (
    "Next Highest Priority Action",
    "Next Highest Priority Actions",
    "Next Highest-Priority Actions",
    "Next Actions",
    "下一步最高优先级",
    "下一步行动",
    "下一步",
)

_TERMINAL_ACTION_HEADINGS = (
    "Completed Actions",
    "Completed",
    "Superseded Actions",
    "Stale Actions",
    "已完成行动",
    "已完成",
    "已替代行动",
    "过期行动",
)

_EMPTY_ACTIONS = {
    "",
    "none",
    "(none)",
    "(none identified)",
    "(none recorded)",
    "(not defined)",
    "无",
    "暂无",
    "未定义",
}

_REVIEW_PENDING_ACTIONS = {
    "review pending patches",
    "review pending patch",
    "审核待处理补丁",
    "审核待处理 patch",
}

_INITIAL_FRAMING_ACTIONS = {
    "run 'flg frame' to define project goals and boundaries",
    "run ‘flg frame’ to define project goals and boundaries",
}


def _section_with_heading(text: str, headings: Iterable[str]) -> tuple[str, str]:
    wanted = {heading.casefold() for heading in headings}
    lines = text.splitlines()
    start: int | None = None
    matched = ""
    level = 0
    for index, line in enumerate(lines):
        match = re.match(r"^(#{2,6})\s+(.+?)\s*$", line)
        if not match:
            continue
        heading = match.group(2).strip()
        if heading.casefold() in wanted:
            start = index + 1
            matched = heading
            level = len(match.group(1))
            break
    if start is None:
        return "", ""

    end = len(lines)
    for index in range(start, len(lines)):
        match = re.match(r"^(#{1,6})\s+", lines[index])
        if match and len(match.group(1)) <= level:
            end = index
            break
    return "\n".join(lines[start:end]).strip(), matched


def _clean_action_line(raw: str) -> str:
    line = raw.strip()
    if not line or line.startswith("<!--"):
        return ""
    line = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", line)
    line = re.sub(r"^\[[ xX]\]\s+", "", line)
    line = line.strip().strip("`").strip()
    if line.casefold() in _EMPTY_ACTIONS:
        return ""
    return line


def _first_action(section: str) -> str:
    for raw in section.splitlines():
        action = _clean_action_line(raw)
        if action:
            return action
    return ""


def _list_actions(section: str) -> list[str]:
    actions: list[str] = []
    for raw in section.splitlines():
        action = _clean_action_line(raw)
        if action and action not in actions:
            actions.append(action)
    return actions


def _action_key(action: str) -> str:
    value = re.sub(r"\s+", " ", action).strip().casefold()
    return value.rstrip(".。;；")


def _snapshot_updated_at(snapshot_content: str) -> str:
    patterns = (
        r"^\*\*Updated:\*\*\s*(.+?)\s*$",
        r"^\*Last Updated:\s*(.+?)\*\s*$",
        r"^Last Updated:\s*(.+?)\s*$",
        r"^最后更新[：:]\s*(.+?)\s*$",
    )
    for pattern in patterns:
        match = re.search(
            pattern,
            snapshot_content,
            re.MULTILINE | re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
    return "unknown"


def _state_actions(state: dict[str, Any]) -> list[str]:
    raw = state.get("next_actions") or []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    actions: list[str] = []
    for item in raw:
        action = _clean_action_line(str(item))
        if action and action not in actions:
            actions.append(action)
    return actions


def resolve_current_action(
    snapshot_content: str,
    state: dict[str, Any],
    *,
    pending_patches_count: int,
    framing_goal_defined: bool = False,
) -> dict[str, Any]:
    """Compile one safe current action from formal state.

    SNAPSHOT.md is the formal current-state authority. ``state.next_actions`` is
    a legacy fallback cache: it may corroborate the Snapshot, but it cannot
    override or independently become an autonomous instruction.
    """
    section, heading = _section_with_heading(snapshot_content, ACTION_HEADINGS)
    snapshot_action = _first_action(section)
    snapshot_updated_at = _snapshot_updated_at(snapshot_content)
    state_actions = _state_actions(state)

    terminal_actions: list[str] = []
    for terminal_heading in _TERMINAL_ACTION_HEADINGS:
        terminal_section, matched = _section_with_heading(
            snapshot_content,
            (terminal_heading,),
        )
        if matched:
            terminal_actions.extend(_list_actions(terminal_section))
    terminal_keys = {_action_key(action) for action in terminal_actions}

    result: dict[str, Any] = {
        "status": "not_defined",
        "action": None,
        "source": None,
        "source_updated_at": snapshot_updated_at,
        "reason": "No formal current action is defined in SNAPSHOT.md.",
        "ignored_fallback_count": 0,
        "state_candidate_count": len(state_actions),
    }

    if snapshot_action:
        action_key = _action_key(snapshot_action)
        source = f"SNAPSHOT.md#{heading.replace(' ', '-')}"
        different_state_actions = [
            action for action in state_actions if _action_key(action) != action_key
        ]
        result.update(
            {
                "source": source,
                "ignored_fallback_count": len(different_state_actions),
            }
        )

        if action_key in _REVIEW_PENDING_ACTIONS and pending_patches_count == 0:
            result.update(
                {
                    "status": "needs_reconciliation",
                    "reason": (
                        "SNAPSHOT.md asks to review pending patches, but "
                        "FlowGrid reports no pending patches. Do not continue "
                        "this action."
                    ),
                }
            )
            return result

        if action_key in _INITIAL_FRAMING_ACTIONS and framing_goal_defined:
            result.update(
                {
                    "status": "needs_reconciliation",
                    "reason": (
                        "SNAPSHOT.md still carries the initialization framing "
                        "action after FRAMING.md defines a real goal. Do not "
                        "continue the template action."
                    ),
                }
            )
            return result

        if action_key in terminal_keys:
            result.update(
                {
                    "status": "needs_reconciliation",
                    "reason": (
                        "The Snapshot lists the same action as completed, "
                        "superseded, or stale. Do not continue it."
                    ),
                }
            )
            return result

        result.update(
            {
                "status": "current",
                "action": snapshot_action,
                "reason": (
                    "Selected from formal SNAPSHOT.md current state. Different "
                    "state.next_actions entries were treated as superseded "
                    "fallbacks."
                    if different_state_actions
                    else "Selected from formal SNAPSHOT.md current state."
                ),
            }
        )
        return result

    if state_actions:
        result.update(
            {
                "status": "needs_reconciliation",
                "reason": (
                    "Only .flg/state.json next_actions are available. They are "
                    "a legacy cache, not sufficient authority for autonomous "
                    "continuation."
                ),
            }
        )
    return result
