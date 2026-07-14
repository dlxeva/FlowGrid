"""Project language helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from .state import load_state

Language = Literal["en", "zh"]
SUPPORTED_LANGUAGES = ("en", "zh")
DEFAULT_LANGUAGE: Language = "zh"


def normalize_language(value: str | None) -> Language:
    normalized = (value or DEFAULT_LANGUAGE).strip().lower()
    if normalized in {"en", "english", "en-us", "en-gb"}:
        return "en"
    if normalized in {"zh", "zh-cn", "chinese", "中文"}:
        return "zh"
    raise ValueError(f"Unsupported language: {value}. Choose en or zh.")


def project_language(root: Path) -> Language:
    state = load_state(root)
    if not state:
        return DEFAULT_LANGUAGE
    try:
        return normalize_language(str(state.get("language", DEFAULT_LANGUAGE)))
    except ValueError:
        return DEFAULT_LANGUAGE


_LEDGER_LINE_TRANSLATIONS = {
    "### 决策时间": "### Decision Date",
    "### 所属阶段": "### Project Stage",
    "### 决策背景": "### Decision Background",
    "### 核心问题": "### Core Question",
    "### 备选方案": "### Alternatives",
    "### 最终决策": "### Final Decision",
    "### 决策理由": "### Decision Rationale",
    "### 放弃理由": "### Rejected Alternatives",
    "### 风险判断": "### Risk Assessment",
    "### 后续验证": "### Follow-up Validation",
    "### 复盘入口": "### Reversal Conditions",
    "执行": "Execution",
    "立项": "Initiation",
    "项目推进中的关键判断": "Key judgment in the current project",
    "待结合项目上下文补充": "To be completed from project context",
    "未记录备选方案": "No alternatives recorded",
    "由 `flg decision add` 直接写入决策日志。": "Written directly by flg decision add.",
    "由 `flg capture review` 从候选判断中确认写入。": "Confirmed from a candidate judgment by flg capture review.",
    "选择了当前方案，放弃其他备选方案。": "The selected path was chosen over the alternatives.",
    "通过后续执行结果和项目反馈验证。": "Validate through execution results and project feedback.",
    "如果关键前提变化或出现新的替代方案，需要重新评估。": "Reconsider if a key premise changes or a new alternative appears.",
    "用户明确指令：直接写入决策日志（`flg decision add`）。": "User explicitly requested this decision be recorded.",
    "用户判断": "user judgment",
    "*决策 | Source: 用户明确指令*": "*decision | Source: user explicit instruction*",
}


def localize_ledger_entry(content: str, language: Language) -> str:
    if language != "en":
        return content
    return "\n".join(_LEDGER_LINE_TRANSLATIONS.get(line, line) for line in content.split("\n"))
