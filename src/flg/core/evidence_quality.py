"""Evidence-basis checks for project framing quality."""

from __future__ import annotations

import re


_SECTION_RE = re.compile(
    r"^##\s+(?:Evidence\s+(?:Tier|Basis)|Evidence\s+Quality|证据等级|证据基础)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_VALUE_RE = re.compile(
    r"(?:overall\s+basis|evidence\s+(?:tier|basis)|总体证据|证据(?:等级|基础))\s*[:：]\s*(.+)",
    re.IGNORECASE,
)


def _section_content(content: str) -> str:
    match = _SECTION_RE.search(content)
    if not match:
        return ""
    remainder = content[match.end():]
    next_heading = re.search(r"^##\s+", remainder, re.MULTILINE)
    return remainder[: next_heading.start()] if next_heading else remainder


def assess_evidence_basis(content: str) -> dict[str, str | bool]:
    """Return a conservative evidence-basis assessment for FRAMING.md.

    The section is advisory so legacy projects remain compatible. Explicit
    low-confidence declarations produce a warning; missing declarations do too.
    """
    section = _section_content(content)
    if not section.strip():
        return {
            "level": "missing",
            "label": "not declared",
            "warning": True,
            "message": "Evidence basis is not declared; verify the framing before commitment.",
        }

    value_match = _VALUE_RE.search(section)
    value = (value_match.group(1) if value_match else section).strip().lower()

    # The generated template lists the allowed values as a placeholder.
    if value.strip("() ") in {
        "direct / verified / secondary / speculative",
        "direct/verified/secondary/speculative",
    }:
        return {
            "level": "missing",
            "label": "not declared",
            "warning": True,
            "message": "Evidence basis is not declared; verify the framing before commitment.",
        }

    if re.search(r"tier\s*3|三手|tertiary|speculative|unverified|未验证|推测|猜测", value):
        level = "speculative"
        message = "This framing relies on speculative or unverified evidence; validate before commitment."
    elif re.search(r"tier\s*2|二手|secondary|reported|转述", value):
        level = "secondary"
        message = "This framing relies on secondary evidence; recommend first-hand validation before commitment."
    elif re.search(r"tier\s*1|一手|direct|first[- ]hand|observed|user[- ]confirmed|client[- ]confirmed|直接|现场", value):
        level = "direct"
        message = "Evidence basis is direct or explicitly confirmed."
    elif re.search(r"verified|核验|已确认|已验证", value):
        level = "verified"
        message = "Evidence basis is explicitly verified."
    else:
        level = "unknown"
        message = "Evidence basis is unclear; verify the framing before commitment."

    return {
        "level": level,
        "label": level,
        "warning": level in {"missing", "secondary", "speculative", "unknown"},
        "message": message,
    }
