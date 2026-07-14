"""flg closeout command - Generate closeout patch from transcript."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..core.files import is_flg_project, read_file_safe
from ..core.patches import create_patch, generate_patch_id
from ..core.state import add_pending_patch, load_state
from ..templates import CLOSEOUT_PATCH_MD, DECISION_PROMPT_TEMPLATE, CLOSEOUT_LLM_PROMPT_TEMPLATE, get_iso_now
from ..llm_client import call_llm, parse_llm_response, get_llm_config, is_llm_available, VALID_PROVIDERS

console = Console()

STRUCTURED_LEDGER_FILENAMES = {
    "project.md",
    "framing.md",
    "decisions.md",
    "snapshot.md",
    "progress.md",
    "readme.md",
    "goal_evolution.md",
    "constraints.md",
    "anchors.md",
    "项目进展.md",
    "项目快照.md",
    "决策日志.md",
}

# Decision keywords - must be explicit confirmation or trade-off
DECISION_KEYWORDS = {
    # Explicit confirmation
    "confirmation": [
        "定了", "确认", "就按这个", "采用", "就这个", "拍板",
        "decided", "confirmed", "approved", "finalized",
        # Common spoken-English commitment phrases
        "we'll go with", "let's go with", "going with",
        "let's do", "we're doing", "settled on", "locked in",
        "that's the plan", "that's final",
    ],
    # Explicit trade-off — strong exclusion/commitment actions only.
    # Weak signals like "优先" "边界" "选择" removed (发现 14: they fire on
    # work-plan priority lists, not real decisions).
    "tradeoff": [
        "不做", "放弃", "改成", "取代", "延后",
        "暂停", "进入下一阶段", "不是重点",
        "取舍",
        "不做.*选", "先做.*延后", "这个不是重点",
        # English: strong exclusion / sequencing verbs
        "not doing", "not going to", "we're dropping", "drop",
        "cut", "skip", "shelve", "park", "rule out", "ruled out",
        "descope", "defer", "push back", "put on hold",
        "instead of", "rather than", "trade-off", "choose a over b",
        "going with.*over", "a over b",
    ],
    # Project state change
    "state_change": [
        "目标变化", "边界变化", "版本范围", "试点对象",
        "下一步动作", "责任对象",
        "goal changed", "scope changed", "priority shifted",
        "pivoted", "changed direction", "new scope",
        "redefined the goal", "shifted focus",
    ],
    # Human confirmation signal
    "human_signal": [
        "用户确认", "用户拍板", "用户同意", "用户要求写入",
        "用户要求调整", "用户决定", "用户选择",
        "user confirmed", "user approved", "user decided",
        "stakeholder approved", "client signed off",
        "client confirmed", "client approved",
        "signed off", "gave the green light",
    ],
}

# Risk keywords - must be high impact. Use regex patterns for broader recall.
RISK_KEYWORDS = {
    # Impact on goals
    "goal_impact": [
        r"可能影响目标", r"可能导致失败", r"无法达成",
        r"might fail", r"could (miss|delay|jeopardize)", r"goal at risk",
        r"\brisk.*\b(cancel|fail|miss|delay)\b",
        r"\b(cancel|fail|miss|delay)\b.*\b(risk|might|could)\b",
    ],
    # Impact on delivery
    "delivery_impact": [
        r"可能影响交付", r"可能延期", r"质量风险",
        r"delivery risk", r"quality concern",
        r"(might|could) delay", r"delay.*\b(launch|timeline|delivery|deadline)\b",
        r"(might|could) cancel",
        r"(launch|timeline|delivery|deadline).*\b(risk|delay|slip|push)\b",
    ],
    # Impact on stakeholder expectations
    "stakeholder_impact": [
        r"客户可能不满意", r"评审风险", r"预期不一致",
        r"client concern", r"review risk", r"expectation gap",
        r"(might|could) affect.*\b(client|customer|stakeholder)\b",
        r"(client|customer|stakeholder).*(unhappy|concern|gap|risk)",
    ],
    # Impact on time/cost/scope
    "constraint_impact": [
        r"预算可能不够", r"时间可能不够", r"范围可能失控",
        r"budget risk", r"time risk", r"scope creep",
        r"budget.*(not|enough|exceed|over|insufficient)",
        r"(not|enough|exceed|over|insufficient).*budget",
        r"(might|could) exceed",
        r"not.*enough.*(budget|time|resource|money|fund)",
        r"不够.*?(预算|时间|资源|经费)",
    ],
    # Impact on data integrity
    "integrity_impact": [
        r"可能误写", r"可能污染", r"可能误导",
        r"data risk", r"integrity risk", r"misleading",
    ],
    # Positioning / clarity risks
    "clarity_impact": [
        r"(positioning|定位).*(not|isn't|unclear|不清楚|不明确|模糊)",
        r"(not|isn't|unclear|不清楚|不明确|模糊).*(positioning|定位|clear)",
        r"(might|could) affect.*\b(write|copy|content|messaging)\b",
    ],
}

# Open question keywords
OPEN_QUESTION_KEYWORDS = [
    "待确认", "未确认", "需要确认", "下一步", "后续", "TODO", "待办",
    "need to confirm", "pending", "open question", "to be determined",
]

GOAL_SHIFT_PATTERNS = [
    r"目标变化",
    r"目标改成",
    r"目标从.*变成",
    r"goal changed",
    r"goal is now",
    r"we are shifting to",
    r"priority shifted",
]

NEXT_ACTION_KEYWORDS = [
    r"\bnext step[s]?\b",
    r"\baction item[s]?\b",
    r"\bfollow up\b",
    r"\btodo\b",
    r"下一步",
    r"接下来",
    r"待办",
]

# Only match "to do" when followed by a concrete object, not "to do that/this/it"
# This is handled separately in extract_next_actions via exclusion.

ACTION_VERB_PATTERNS = [
    r"\bneed to (confirm|review|create|prepare|update|merge|fill|schedule|sync|draft|write|set up|send|build|fix|assign|ship|deploy)\b",
    r"\b(confirm|review|create|prepare|update|merge|fill in|schedule|sync|draft|write|set up|send|build|fix|assign|ship|deploy)\b",
    r"需要(确认|复核|创建|准备|更新|合并|补充|同步|起草|撰写|搭建|发送|构建|修复|分配|部署)",
    r"^(确认|复核|创建|准备|更新|合并|补充|同步|起草|撰写|搭建|发送|构建|修复|分配|部署)",  # bare CN verb at start
]

# Patterns that indicate broad goals/aspirations, NOT concrete next actions.
# These are excluded from next-actions even if they contain action verbs.
BROAD_GOAL_PATTERNS = [
    r"\b(we )?(want|need) to do (a|an|the)\b",       # "want to do a launch"
    r"\bto do (that|this|it|so|the same)\b",          # "need to do that"
    r"\b(generate|achieve|reach|get|increase|improve|grow|boost)\b.*\b(users|customers|revenue|growth|awareness|market share|engagement|traffic|conversion|leads)\b",  # outcome goals
    r"(提升|达到|实现|增长|获取).*?(用户|客户|收入|增长|知名度|曝光|转化|线索)",  # CN outcome goals
    r"\bgoal is\b.*\b\d+",                            # "goal is 1000 users"
    r"\bshould (we|I) (focus|define|think|consider|explore)\b",  # "should we focus on" — discussion, not action
]

# Rationale keywords - thinking process markers
RATIONALE_KEYWORDS = [
    r"我在想",
    r"纠结",
    r"犹豫",
    r"一方面.*另一方面",
    r"on one hand",
    r"on the other hand",
    r"I'm torn between",
    r"一方面",
    r"换个角度",
    r"回过头想",
]

LESSONS_LEARNED_KEYWORDS = [
    # 结果验证信号
    r"验证了", r"证明了", r"结果是", r"回头看", r"事后看",
    r"turns out", r"in hindsight", r"proved right", r"proved wrong",
    # 经验总结信号
    r"学到", r"教训", r"下次", r"以后", r"经验",
    r"lesson", r"next time", r"learned",
]


# Risk/problem language — sentences describing risks/problems are NOT next actions
RISK_SENTENCE_PATTERNS = [
    r"\b(might|could|may)\b.*\b(affect|impact|delay|cancel|fail|miss|exceed|slip)\b",
    r"\bisn't (clear|certain|confirmed|ready)\b",
    r"\b(not|isn't) (clear|certain|confirmed|ready|enough)\b",
    r"\brisk\b",
    r"\b(problem|issue|concern|blocker|threat)\b",
    r"(风险|问题|隐患|可能影响|不够明确|不清楚)",
]


def strip_inline_code(text: str) -> str:
    """Remove inline code spans and fenced code blocks from text.

    发现 24: code backticks cause keyword false-positives. A sentence like
    "读编译器源码确认：`inferDuration`" hits the "确认" confirmation
    keyword because the code span is not stripped before matching.

    This replaces inline `code` with a placeholder and removes fenced
    ```blocks``` entirely, so keyword matching only sees natural-language
    text. The original text is still used for context-window reasoning
    extraction (where seeing the code is fine).
    """
    # Remove fenced code blocks (```...```)
    text = re.sub(r"```[\s\S]*?```", " ", text)
    # Replace inline code (`...`) with a space — keep word boundaries clean
    text = re.sub(r"`[^`]+`", " ", text)
    return text


def iter_segments(content: str) -> list[str]:
    """Split transcript into sentence-like segments while keeping questions."""
    segments = []
    for match in re.findall(r"[^.!?。！？\n]+[.!?。！？]?", content):
        segment = match.strip()
        if segment:
            segments.append(segment)
    return segments


def match_pattern(segment: str, patterns: list[str]) -> str | None:
    """Return the first regex pattern that matches the segment."""
    for pattern in patterns:
        if re.search(pattern, segment, re.IGNORECASE):
            return pattern
    return None


def _get_context_window(full_text: str, target_sentence: str, window: int = 5) -> str:
    """Return a window of ±N sentences around a target sentence in the full text.

    Falls back to the target sentence alone if segmentation doesn't recover it.
    """
    all_segments = iter_segments(full_text)
    try:
        idx = all_segments.index(target_sentence)
    except ValueError:
        return target_sentence

    start = max(0, idx - window)
    end = min(len(all_segments), idx + window + 1)
    return " ".join(all_segments[start:end])


def extract_decisions(content: str) -> list[dict]:
    """Extract candidate decisions with strict criteria and enriched context."""
    decisions = []

    # Strip code spans from the entire content BEFORE segmentation (发现 24).
    # This prevents backtick-internal punctuation (e.g. the period in
    # `decided-to-skip-auth.md`) from splitting sentences mid-code, and
    # prevents backtick-internal keywords from triggering false matches.
    clean_content = strip_inline_code(content)

    for sentence in iter_segments(clean_content):
        if not sentence or len(sentence) < 10:
            continue

        # match_text equals sentence here since clean_content already stripped code.
        # (Kept as a variable for readability and future hooks.)
        match_text = sentence

        # Guard: skip sentences that describe risks (e.g. "KOLs we confirmed might cancel").
        # These contain confirmation words but the sentence is about a risk, not a decision.
        if match_pattern(match_text, RISK_SENTENCE_PATTERNS):
            continue

        # Check for explicit confirmation
        keyword = match_pattern(match_text, DECISION_KEYWORDS["confirmation"])
        if keyword:
            ctx = _get_context_window(clean_content, sentence)
            context_info = extract_decision_context(ctx)
            decisions.append({
                "content": sentence,
                "type": "explicit_confirmation",
                "confidence": "high",
                "keyword": keyword,
                "reasoning": "; ".join(context_info["reasoning"]),
                "rejected_alternatives": "; ".join(context_info["rejected_alternatives"]),
                "reversal_conditions": "; ".join(context_info["reversal_conditions"]),
            })
            continue

        # Check for trade-off
        keyword = match_pattern(match_text, DECISION_KEYWORDS["tradeoff"])
        if keyword:
            ctx = _get_context_window(clean_content, sentence)
            context_info = extract_decision_context(ctx)
            decisions.append({
                "content": sentence,
                "type": "tradeoff",
                "confidence": "high",
                "keyword": keyword,
                "reasoning": "; ".join(context_info["reasoning"]),
                "rejected_alternatives": "; ".join(context_info["rejected_alternatives"]),
                "reversal_conditions": "; ".join(context_info["reversal_conditions"]),
            })
            continue

        # Check for state change
        keyword = match_pattern(match_text, DECISION_KEYWORDS["state_change"])
        if keyword:
            ctx = _get_context_window(clean_content, sentence)
            context_info = extract_decision_context(ctx)
            decisions.append({
                "content": sentence,
                "type": "state_change",
                "confidence": "medium",
                "keyword": keyword,
                "reasoning": "; ".join(context_info["reasoning"]),
                "rejected_alternatives": "; ".join(context_info["rejected_alternatives"]),
                "reversal_conditions": "; ".join(context_info["reversal_conditions"]),
            })
            continue

        # Check for human signal
        keyword = match_pattern(match_text, DECISION_KEYWORDS["human_signal"])
        if keyword:
            ctx = _get_context_window(clean_content, sentence)
            context_info = extract_decision_context(ctx)
            decisions.append({
                "content": sentence,
                "type": "human_signal",
                "confidence": "high",
                "keyword": keyword,
                "reasoning": "; ".join(context_info["reasoning"]),
                "rejected_alternatives": "; ".join(context_info["rejected_alternatives"]),
                "reversal_conditions": "; ".join(context_info["reversal_conditions"]),
            })

    # Deduplicate
    seen = set()
    unique_decisions = []
    for d in decisions:
        if d["content"] not in seen:
            seen.add(d["content"])
            unique_decisions.append(d)

    return unique_decisions


def extract_risks(content: str) -> list[dict]:
    """Extract risks with strict criteria - only high-impact risks."""
    risks = []
    
    for sentence in iter_segments(content):
        if not sentence or len(sentence) < 10:
            continue
        
        # Check for goal impact
        keyword = match_pattern(sentence, RISK_KEYWORDS["goal_impact"])
        if keyword:
            risks.append({
                "content": sentence,
                "type": "goal_impact",
                "keyword": keyword,
            })
            continue
        
        # Check for delivery impact
        keyword = match_pattern(sentence, RISK_KEYWORDS["delivery_impact"])
        if keyword:
            risks.append({
                "content": sentence,
                "type": "delivery_impact",
                "keyword": keyword,
            })
            continue
        
        # Check for stakeholder impact
        keyword = match_pattern(sentence, RISK_KEYWORDS["stakeholder_impact"])
        if keyword:
            risks.append({
                "content": sentence,
                "type": "stakeholder_impact",
                "keyword": keyword,
            })
            continue
        
        # Check for constraint impact
        keyword = match_pattern(sentence, RISK_KEYWORDS["constraint_impact"])
        if keyword:
            risks.append({
                "content": sentence,
                "type": "constraint_impact",
                "keyword": keyword,
            })
            continue
        
        # Check for integrity impact
        keyword = match_pattern(sentence, RISK_KEYWORDS["integrity_impact"])
        if keyword:
            risks.append({
                "content": sentence,
                "type": "integrity_impact",
                "keyword": keyword,
            })
            continue
        
        # Check for clarity/positioning impact
        keyword = match_pattern(sentence, RISK_KEYWORDS.get("clarity_impact", []))
        if keyword:
            risks.append({
                "content": sentence,
                "type": "clarity_impact",
                "keyword": keyword,
            })
    
    # Deduplicate
    seen = set()
    unique_risks = []
    for r in risks:
        if r["content"] not in seen:
            seen.add(r["content"])
            unique_risks.append(r)
    
    return unique_risks


def extract_open_questions(content: str) -> list[str]:
    """Extract open questions."""
    questions = []
    
    for sentence in iter_segments(content):
        if not sentence or len(sentence) < 10:
            continue
        # Skip section headers
        stripped = sentence.strip().lstrip("#").strip().lower()
        if stripped in {"open questions", "questions", "questions to resolve", "unresolved questions"}:
            continue
        if sentence.strip().startswith("#") and len(stripped) < 30:
            continue
        if "?" in sentence or "？" in sentence:
            questions.append(sentence)
            continue
        keyword = match_pattern(sentence, OPEN_QUESTION_KEYWORDS)
        if keyword:
            questions.append(sentence)
    
    return list(set(questions))


def extract_next_actions(content: str) -> list[str]:
    """Extract concrete executable next actions only.

    Excludes:
    - Questions (belong in open_questions)
    - Section headers (e.g. "### Next Steps")
    - Broad goals / aspirations (e.g. "get 1000 users")
    - Vague references (e.g. "need to do that")
    - Discussion prompts (e.g. "should we focus on")
    """
    actions = []

    for sentence in iter_segments(content):
        if not sentence or len(sentence) < 10:
            continue
        normalized = sentence.strip().rstrip(".。")
        lower = normalized.lower()
        
        # 1. Skip bare headers and section titles
        stripped = normalized.lstrip("#").strip().lower()
        if stripped in {"next steps", "next step", "action items", "to do", "follow up"}:
            continue
        if normalized.startswith("#") and len(stripped) < 30:
            continue

        # 2. Skip questions — these belong in open_questions
        if "?" in sentence or "？" in sentence:
            continue

        # 3. Skip bare "user: yes" confirmations
        if lower.startswith("user: yes") or lower == "yes":
            continue

        # 4. Skip broad goals / aspirations
        if match_pattern(sentence, BROAD_GOAL_PATTERNS):
            continue

        # 4b. Skip risk/problem descriptions — they belong in Risks, not next actions
        if match_pattern(sentence, RISK_SENTENCE_PATTERNS):
            continue

        # 5. Positive match: either a keyword marker or an action verb
        marker = match_pattern(sentence, NEXT_ACTION_KEYWORDS)
        verb = match_pattern(sentence, ACTION_VERB_PATTERNS)
        if marker or verb:
            actions.append(normalized)

    unique_actions = []
    seen = set()
    for action in actions:
        if action not in seen:
            seen.add(action)
            unique_actions.append(action)
    return unique_actions


def extract_goal_shifts(content: str) -> list[str]:
    """Extract sentences that signal goal evolution."""
    shifts = []
    seen = set()
    for sentence in iter_segments(content):
        if not sentence or len(sentence) < 10:
            continue
        if match_pattern(sentence, GOAL_SHIFT_PATTERNS):
            if sentence not in seen:
                seen.add(sentence)
                shifts.append(sentence.strip())
    return shifts


def extract_related_docs_and_assets(content: str) -> tuple[list[str], list[str]]:
    """Extract file-like references from transcript text."""
    doc_matches = re.findall(r"\b[\w./-]+\.(?:md|docx|pdf|html|pptx|xlsx|csv)\b", content, re.IGNORECASE)
    asset_matches = re.findall(r"\b[\w./-]+\.(?:png|jpg|jpeg|gif|webp|mp4|mov|fig)\b", content, re.IGNORECASE)

    docs = list(dict.fromkeys(doc_matches))
    assets = list(dict.fromkeys(asset_matches))
    return docs, assets


def infer_decision_relations(decision: dict, next_actions: list[str], content: str) -> dict:
    """Infer lightweight decision relations for patch review."""
    related_docs, related_assets = extract_related_docs_and_assets(content)
    related_goals = []
    affected_actions = []
    supersedes = "(none detected)"

    for sentence in iter_segments(content):
        lower = sentence.lower()
        if "goal" in lower or "目标" in sentence:
            related_goals.append(sentence.strip())
        if any(token in lower for token in ["replace", "instead of", "supersede"]) or any(token in sentence for token in ["取代", "改成", "替代", "改为"]):
            supersedes = sentence.strip()

    decision_words = {word.lower() for word in re.findall(r"[A-Za-z]+", decision["content"])}
    for action in next_actions:
        action_words = {word.lower() for word in re.findall(r"[A-Za-z]+", action)}
        if decision_words & action_words:
            affected_actions.append(action)

    if not affected_actions:
        affected_actions = next_actions[:2]

    return {
        "related_goals": list(dict.fromkeys(related_goals[:2])) or ["(none detected)"],
        "related_docs": related_docs[:3] or ["(none detected)"],
        "related_assets": related_assets[:3] or ["(none detected)"],
        "affected_actions": affected_actions[:3] or ["(none detected)"],
        "supersedes": supersedes,
    }


def extract_rationale_excerpts(content: str) -> list[str]:
    """Extract thinking-process excerpts from conversation.

    Captures moments of deliberation, hesitation, inspiration shifts,
    and perspective changes — the "推导过程" behind decisions.
    """
    excerpts = []
    seen = set()
    for sentence in iter_segments(content):
        if not sentence or len(sentence) < 10:
            continue
        keyword = match_pattern(sentence, RATIONALE_KEYWORDS)
        if keyword and sentence not in seen:
            seen.add(sentence)
            excerpts.append(sentence.strip())
    return excerpts


def extract_lessons_learned_signals(content: str) -> list[str]:
    """Extract lessons-learned signal sentences from conversation.

    Captures moments where someone reflects on outcomes, validates past
    judgments, or articulates reusable experience.
    """
    excerpts = []
    seen = set()
    for sentence in iter_segments(content):
        if not sentence or len(sentence) < 10:
            continue
        keyword = match_pattern(sentence, LESSONS_LEARNED_KEYWORDS)
        if keyword and sentence not in seen:
            seen.add(sentence)
            excerpts.append(sentence.strip())
    return excerpts


# Reasoning patterns - why a decision was made
REASONING_PATTERNS = [
    r"因为",
    r"依据",
    r"考虑到",
    r"基于",
    r"原因是",
    r"这样.*因为",
    r"since\b",
    r"because\b",
    r"the reason is\b",
    r"given that\b",
    r"考虑到",
    r"基于.*考虑",
    r"出于.*原因",
    # English spoken reasoning
    r"so that\b",
    r"that's why\b",
    r"the thinking was\b",
    r"the idea is\b",
    r"this way\b",
    r"makes sense because\b",
    r"it comes down to\b",
]

# Rejection patterns - what alternatives were rejected
REJECTION_PATTERNS = [
    r"不做.*选",
    r"放弃.*(?:选|改为|改成)",
    r"不选",
    r"排除",
    r"不考虑",
    r"不采用",
    r"否定",
    r"排除了",
    r"放弃",
    r"instead of\b",
    r"rather than\b",
    r"not choosing\b",
    r"ruled out\b",
    # English spoken rejection
    r"we (dropped|cut|skipped|shelved|nixed|abandoned)\b",
    r"we're (dropping|cutting|skipping|shelving)\b",
    r"decided against\b",
    r"didn't go with\b",
    r"passed on\b",
]

# Reversal patterns - conditions under which to reverse
REVERSAL_PATTERNS = [
    r"如果.*(?:回退|逆转|撤销|推翻)",
    r"万一.*(?:回退|改回|变回)",
    r"除非.*(?:否则|不然)",
    r"如果.*(?:失败|不行|出问题)",
    r"if.*then.*(?:revert|rollback|reverse)",
    r"unless\b",
    r"if.*(?:doesn't work|fails|goes wrong)",
    r"回退到",
    r"退回.*方案",
    # English spoken reversal
    r"if that doesn't work",
    r"we can always (go back|revert|switch back)",
    r"fall back to\b",
    r"worst case\b",
    r"plan b\b",
]


def extract_decision_context(context_text: str) -> dict:
    """Extract reasoning, rejected alternatives, and reversal conditions from context.

    Args:
        context_text: The decision sentence and surrounding context (±5 sentences).

    Returns:
        dict with keys: reasoning, rejected_alternatives, reversal_conditions
    """
    reasoning = []
    rejected = []
    reversal = []

    for sentence in iter_segments(context_text):
        if not sentence or len(sentence) < 5:
            continue

        for pattern in REASONING_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                reasoning.append(sentence.strip())
                break

        for pattern in REJECTION_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                rejected.append(sentence.strip())
                break

        for pattern in REVERSAL_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                reversal.append(sentence.strip())
                break

    return {
        "reasoning": list(dict.fromkeys(reasoning)),
        "rejected_alternatives": list(dict.fromkeys(rejected)),
        "reversal_conditions": list(dict.fromkeys(reversal)),
    }


def generate_decision_title(content: str) -> str:
    """Generate a short title for a decision."""
    # Take first 50 chars
    if len(content) <= 50:
        return content
    return content[:47] + "..."


def why_this_is_a_decision(decision: dict) -> str:
    """Explain why this is a decision."""
    if decision["type"] == "explicit_confirmation":
        return f"Explicit confirmation detected: '{decision['keyword']}'"
    elif decision["type"] == "tradeoff":
        return f"Explicit trade-off detected: '{decision['keyword']}'"
    elif decision["type"] == "state_change":
        return f"Project state change detected: '{decision['keyword']}'"
    elif decision["type"] == "human_signal":
        return f"Human confirmation signal detected: '{decision['keyword']}'"
    return "Decision keyword detected"


# Placeholder markers used to detect empty/shell decision fields.
# A candidate decision whose reasoning + alternatives + reversal all come back
# as these placeholders is a "shell" — it matched a keyword but carries no
# real decision context, so downstream review should not silently accept it.
_SHELL_PLACEHOLDERS = (
    "(not detected in context)",
    "(not detected by llm)",
    "(not provided by ai)",
    "(none detected)",
)


def is_shell_decision(reasoning: str, rejected: str, reversal: str) -> bool:
    """Return True when reasoning + alternatives + reversal are all empty/placeholder.

    These "shell" decisions matched a trigger keyword but carry no real context
    (no why, no alternatives, no reversal conditions). They are the most common
    source of noise when closeout misfires on work-plans or priority lists.
    They stay in the patch (the match may be real), but get flagged low_confidence
    so review does not silently write them into DECISIONS.md.
    """
    fields = (reasoning or "", rejected or "", reversal or "")
    normalized = tuple(f.strip().lower() for f in fields)
    # All three empty
    if all(not f for f in normalized):
        return True
    # All three are either empty or a known placeholder
    def _is_empty_or_placeholder(v: str) -> bool:
        if not v:
            return True
        return any(p in v for p in _SHELL_PLACEHOLDERS)
    return all(_is_empty_or_placeholder(f) for f in normalized)


def closeout_session(
    transcript: Path = typer.Option(..., "--transcript", "-t", help="Path to transcript markdown"),
    mode: str = typer.Option("concise", "--mode", "-m", help="Output mode: concise, full, or prompt"),
    prompt_only: bool = typer.Option(False, "--prompt", "-p", help="Generate LLM prompt for decision extraction (no API call)"),
    llm: Optional[str] = typer.Option(None, "--llm", "-l", help="LLM provider: openai, claude, custom, local, or 'hermes' to delegate to current AI session"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Force keyword-based extraction (skip LLM even if configured)"),
    llm_write: Optional[Path] = typer.Option(None, "--llm-write", help="Write a JSON decision file (from Hermes-assisted extraction) into a closeout patch"),
    force: bool = typer.Option(False, "--force", help="Allow closeout on structured ledger files (not recommended)"),
) -> None:
    """Generate closeout patch from session transcript.

    Decision extraction modes (in priority order):
      1. --prompt: generate a prompt file for external LLM use
      2. --llm-write <json>: finalize a Hermes-assisted extraction
      3. --llm <provider>: call LLM API (or delegate to current AI session if provider='hermes')
      4. --no-llm: force keyword-based extraction
      5. default: auto-detect — use LLM if API keys are configured, else keyword matching

    Hermes-assisted mode (--llm hermes):
      Saves the extraction prompt to .flg/sessions/ and asks the current AI
      to process it. The AI writes decisions as JSON, then you run:
        flg closeout --llm-write <result.json>
    """
    root = Path.cwd()

    # Validate --llm provider value
    if llm is not None and llm.lower() not in VALID_PROVIDERS and llm.lower() != "hermes":
        console.print(f"[red]Unknown provider: {llm}. Supported: hermes, {', '.join(sorted(VALID_PROVIDERS))}[/red]")
        raise typer.Exit(1)

    # ── --llm-write: finalize a Hermes-assisted extraction ──────────────
    if llm_write is not None:
        _finalize_llm_result(root, llm_write, transcript, force)
        return

    # Check if this is a FLG project
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    # Check transcript exists
    if not transcript.exists():
        console.print(f"[red]Transcript not found: {transcript}[/red]")
        raise typer.Exit(1)

    transcript_name = transcript.name.lower()
    if transcript_name in STRUCTURED_LEDGER_FILENAMES and not force:
        console.print("[red]Refusing to run closeout on a structured ledger file.[/red]")
        console.print(f"[yellow]File:[/yellow] {transcript.name}")
        console.print("[dim]Use raw session notes, meeting transcripts, or files under .flg/sessions/ instead.[/dim]")
        console.print("[dim]If you intentionally want to process this file anyway, rerun with --force.[/dim]")
        raise typer.Exit(1)

    # Load state
    state = load_state(root)
    project_name = state["project_name"] if state else "Unknown"

    # Read transcript
    content = read_file_safe(transcript)
    if not content:
        console.print("[red]Transcript is empty.[/red]")
        raise typer.Exit(1)

    # ── Resolve extraction mode ────────────────────────────────────────
    # Priority: --prompt > explicit --llm > --no-llm > auto-detect

    use_llm = False
    llm_provider: Optional[str] = None

    if prompt_only:
        # --prompt: generate prompt file only, no extraction
        _do_prompt_only(root, transcript, content)
        return

    if llm is not None:
        if llm.lower() == "hermes":
            # Hermes-assisted: save prompt, let current AI process it
            _delegate_to_hermes(root, transcript, content)
            return
        # Explicit --llm <provider>
        if not is_llm_available(llm.lower()):
            console.print(f"[yellow]No API key found for {llm}. Trying Hermes-assisted mode instead.[/yellow]")
            _delegate_to_hermes(root, transcript, content)
            return
        use_llm = True
        llm_provider = llm.lower()
    elif no_llm:
        # Explicit --no-llm
        use_llm = False
    elif is_llm_available():
        # Auto-detect: LLM configured → use it
        use_llm = True
        llm_provider = None  # let call_llm use default from config
        console.print("[dim]LLM config detected, using LLM for decision extraction. Use --no-llm to force keyword mode.[/dim]")
    else:
        # No LLM config → keyword extraction
        use_llm = False

    # ── LLM extraction path (v0.2.3) ───────────────────────────────────
    if use_llm:
        _do_llm_closeout(root, transcript, content, project_name, state, llm_provider)
        return

    # ── Keyword extraction path (existing behavior) ────────────────────
    _do_keyword_closeout(root, transcript, content, project_name, state, mode)


def _do_prompt_only(root: Path, transcript: Path, content: str) -> None:
    """Generate a prompt file for external LLM use."""
    prompt_content = DECISION_PROMPT_TEMPLATE.format(transcript=content)
    prompt_path = root / ".flg" / "patches" / f"decision-prompt-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt_content, encoding="utf-8")

    console.print()
    console.print("[bold green]✓ Decision extraction prompt generated[/bold green]")
    console.print()
    console.print(f"Transcript: {transcript}")
    console.print(f"Prompt: {prompt_path}")
    console.print()
    console.print("Next steps:")
    console.print("  1. Give this prompt to an LLM agent (Hermes, Claude, GPT, etc.)")
    console.print("  2. Agent fills in the 9-field decision template")
    console.print("  3. Save the agent's output as a .patch.md file in .flg/patches/")
    console.print("  4. Run: flg merge --patch <file>")


def _delegate_to_hermes(root: Path, transcript: Path, content: str) -> None:
    """Hermes-assisted extraction: save prompt for the current AI session to process.

    The current AI (Hermes/DeepSeek/etc.) reads the prompt file, extracts decisions
    as JSON, writes them to a .json file, and the user runs:
        flg closeout --llm-write <result.json>
    """
    sessions_dir = root / ".flg" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    prompt_content = CLOSEOUT_LLM_PROMPT_TEMPLATE.format(transcript=content)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    prompt_path = sessions_dir / f"llm-prompt-{ts}.md"
    prompt_path.write_text(prompt_content, encoding="utf-8")

    console.print()
    console.print("[bold blue]🤖 Hermes-assisted extraction mode[/bold blue]")
    console.print()
    console.print(f"Transcript: {transcript}")
    console.print(f"Prompt saved: {prompt_path}")
    console.print()
    console.print("[bold]交给当前AI处理:[/bold]")
    console.print(f"  你的AI已经可以读取这个文件。告诉它:")
    console.print(f"  [cyan]\"读取 {prompt_path}，按里面的JSON格式提取决策，结果写入 .flg/sessions/llm-result-{ts}.json\"[/cyan]")
    console.print()
    console.print("[bold]然后完成:[/bold]")
    console.print(f"  [cyan]flg closeout --llm-write .flg/sessions/llm-result-{ts}.json[/cyan]")


def _finalize_llm_result(root: Path, json_path: Path, transcript: Path, force: bool) -> None:
    """Write a JSON decision file (from AI extraction) into a closeout patch.

    The JSON file should be an array of objects with: what, type, confidence,
    why, rejected, reverse_condition. Or an object with a "decisions" key.
    """
    import json as _json

    if not json_path.exists():
        console.print(f"[red]JSON result file not found: {json_path}[/red]")
        raise typer.Exit(1)

    # Load state
    state = load_state(root)
    if state is None:
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)
    project_name = state["project_name"]

    # Read and parse JSON
    raw = json_path.read_text(encoding="utf-8")
    try:
        data = _json.loads(raw)
    except _json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1)

    if isinstance(data, dict) and "decisions" in data:
        decisions_raw = data["decisions"]
    elif isinstance(data, list):
        decisions_raw = data
    else:
        console.print("[red]JSON must be an array of decisions or object with 'decisions' key[/red]")
        raise typer.Exit(1)

    # Normalize to internal format
    llm_decisions = []
    for i, d in enumerate(decisions_raw):
        if not isinstance(d, dict):
            continue
        llm_decisions.append({
            "id": d.get("id", f"D-HERMES-{i+1:03d}"),
            "content": d.get("what", str(d)),
            "type": d.get("type", "llm_extracted"),
            "confidence": d.get("confidence", "medium"),
            "reasoning": d.get("why", ""),
            "rejected_alternatives": d.get("rejected", ""),
            "reversal_conditions": d.get("reverse_condition", ""),
        })

    if not llm_decisions:
        console.print("[yellow]No decisions found in JSON.[/yellow]")
        return

    # Build patch (reuse _do_llm_closeout's patch format)
    now = get_iso_now()
    patch_id = generate_patch_id("closeout-hermes")

    candidate_decisions = ""
    for i, d in enumerate(llm_decisions, 1):
        reasoning = d.get("reasoning", "")
        rejected = d.get("rejected_alternatives", "")
        reversal = d.get("reversal_conditions", "")
        title = generate_decision_title(d["content"])
        source_excerpt = d.get("content", "")[:120]

        # Quality gate (same as keyword / LLM paths): flag shell decisions.
        why_label = "Hermes AI extracted (v0.2.3)"
        confidence = d.get("confidence", "medium")
        suggested_action = "needs_review"
        if is_shell_decision(reasoning, rejected, reversal):
            confidence = "low"
            why_label = f"{why_label}; low_confidence_shell (no reasoning/alternatives/reversal detected)"
            suggested_action = "needs_review_blocked_accept_all"

        candidate_decisions += f"""### Candidate Decision {i}: {title}

status: pending_review
confidence: {confidence}
decision_type: {d.get('type', 'llm_extracted')}
why_this_is_a_decision: {why_label}
**What was decided:** {d['content']}
**Why:** {reasoning if reasoning else '(not provided by AI)'}
**Alternatives mentioned:** {rejected if rejected else '(not provided by AI)'}
**Rejected because:** {rejected if rejected else '(not provided by AI)'}
**Could reverse if:** {reversal if reversal else '(not provided by AI)'}
**Related goals:** (not analyzed)
**Related docs:** (not analyzed)
**Related assets:** (not analyzed)
**Affected actions:** (not analyzed)
**Supersedes:** (not analyzed)
source_excerpt: > {source_excerpt}
suggested_action: {suggested_action}

"""

    summary = (
        f"- Candidate decisions extracted by Hermes AI: {len(llm_decisions)}\n"
        f"- Source: {json_path}\n"
        f"- All decisions marked pending_review — human confirmation required"
    )

    patch_content = f"""# FLG Patch (Hermes AI Extracted — v0.2.3)

patch_id: {patch_id}
project: {project_name}
generated_at: {now}
source_command: flg closeout --llm-write
source_json: {str(json_path)}
risk_level: medium
status: pending_review
mode: llm-hermes

---

## 1. Session Summary

{summary}

## 2. Candidate Decisions (Hermes AI Extracted)

{candidate_decisions}

## 3. Suggested Next Actions

(Hermes extraction mode — run 'flg closeout --no-llm' for keyword-based next-action analysis.)

## 4. Risks

(Hermes extraction mode — run 'flg closeout --no-llm' for keyword-based risk detection.)

## 5. Open Questions

(not analyzed in Hermes mode)

## 6. Goal Evolution Signals

(not analyzed in Hermes mode)

## 7. Evidence Excerpts

### Decisions

"""
    for d in llm_decisions:
        patch_content += f"> {d['content'][:200]}\n\n"

    patch_content += f"""
## 8. Needs Human Review

- [ ] Review ALL {len(llm_decisions)} AI-extracted candidate decisions
- [ ] Confirm each decision is real (AI may hallucinate or over-extract)
- [ ] Fill in missing fields where AI marked "not provided"
- [ ] Reject any false positives

---

*Generated by flg closeout --llm-write v0.2.3*
"""

    patch_path = create_patch(root, patch_id, patch_content)
    add_pending_patch(root, patch_id, str(patch_path), "medium", source_command="flg closeout --llm-write")

    console.print()
    console.print(f"[bold green]✓ Hermes AI extraction finalized[/bold green]")
    console.print()
    console.print(f"Source JSON: {json_path}")
    console.print(f"Patch: {patch_path}")
    console.print(f"Decisions written: {len(llm_decisions)}")
    console.print()
    console.print("Next steps:")
    console.print("  1. Review the patch — AI decisions need human confirmation")
    console.print("  2. Confirm or reject each candidate decision")
    console.print("  3. Run: flg merge --patch <file>")


def _do_llm_closeout(
    root: Path,
    transcript: Path,
    content: str,
    project_name: str,
    state: dict | None,
    llm_provider: Optional[str],
) -> None:
    """LLM-based closeout: call LLM API, parse JSON response, write structured patch.

    On failure, falls back to keyword extraction (not prompt mode — v0.2.3 behavior).
    """
    prompt_content = CLOSEOUT_LLM_PROMPT_TEMPLATE.format(transcript=content)

    console.print()
    console.print("[bold blue]Calling LLM for decision extraction...[/bold blue]")
    if llm_provider:
        console.print(f"[dim]Provider: {llm_provider}[/dim]")
    console.print()

    try:
        llm_response = call_llm(prompt_content, provider=llm_provider)
    except Exception as e:
        console.print(f"[red]LLM API call failed: {e}[/red]")
        console.print("[yellow]Falling back to keyword-based extraction...[/yellow]")
        _do_keyword_closeout(root, transcript, content, project_name, state, "concise")
        return

    # Parse LLM response (prefers JSON, falls back to markdown)
    llm_decisions = parse_llm_response(llm_response)

    if not llm_decisions:
        console.print("[yellow]LLM found no decisions in this conversation.[/yellow]")
        # Still generate a minimal patch (consistent behavior)
        now = get_iso_now()
        patch_id = generate_patch_id("closeout-llm")
        patch_content = f"""# FLG Patch (LLM — No Decisions Found)

patch_id: {patch_id}
project: {project_name}
generated_at: {now}
source_command: flg closeout --llm
source_transcript: {str(transcript)}
risk_level: low
status: pending_review
mode: llm

---

## LLM Extraction Result

The LLM found no explicit decisions in this conversation.

---

## Needs Human Review

- [ ] Review the transcript to confirm no decisions were missed

---

*Generated by flg closeout --llm*
"""
        patch_path = create_patch(root, patch_id, patch_content)
        add_pending_patch(root, patch_id, str(patch_path), "low", source_command="flg closeout --llm")

        console.print()
        console.print(f"[bold green]✓ Patch generated (no decisions found)[/bold green]")
        console.print(f"Patch: {patch_path}")
        return

    # ── Build patch with LLM-extracted decisions in unified keyword format ──
    now = get_iso_now()
    patch_id = generate_patch_id("closeout-llm")
    llm_model = get_llm_config()["model"]

    # Build candidate decisions section — same format as keyword extraction
    candidate_decisions = ""
    for i, d in enumerate(llm_decisions, 1):
        reasoning = d.get("reasoning", "")
        rejected = d.get("rejected_alternatives", "")
        reversal = d.get("reversal_conditions", "")
        title = generate_decision_title(d["content"])
        source_excerpt = d.get("content", "")
        # Truncate for display
        if len(source_excerpt) > 120:
            source_excerpt = source_excerpt[:117] + "..."

        # Quality gate (same as keyword path): flag shell decisions so
        # review --accept-all won't silently write them into DECISIONS.md.
        why_label = "LLM extracted (v0.2.3)"
        confidence = d.get("confidence", "medium")
        suggested_action = "needs_review"
        if is_shell_decision(reasoning, rejected, reversal):
            confidence = "low"
            why_label = f"{why_label}; low_confidence_shell (no reasoning/alternatives/reversal detected)"
            suggested_action = "needs_review_blocked_accept_all"

        candidate_decisions += f"""### Candidate Decision {i}: {title}

status: pending_review
confidence: {confidence}
decision_type: {d.get('type', 'llm_extracted')}
why_this_is_a_decision: {why_label}
**What was decided:** {d['content']}
**Why:** {reasoning if reasoning else '(not detected by LLM)'}
**Alternatives mentioned:** {rejected if rejected else '(not detected by LLM)'}
**Rejected because:** {rejected if rejected else '(not detected by LLM)'}
**Could reverse if:** {reversal if reversal else '(not detected by LLM)'}
**Related goals:** (not analyzed — LLM extraction only)
**Related docs:** (not analyzed — LLM extraction only)
**Related assets:** (not analyzed — LLM extraction only)
**Affected actions:** (not analyzed — LLM extraction only)
**Supersedes:** (not analyzed — LLM extraction only)
source_excerpt: > {source_excerpt}
suggested_action: {suggested_action}

"""

    summary = (
        f"- Candidate decisions extracted by LLM ({llm_model}): {len(llm_decisions)}\n"
        f"- Source: {transcript}\n"
        f"- All decisions marked pending_review — human confirmation required"
    )

    patch_content = f"""# FLG Patch (LLM Extracted — v0.2.3)

patch_id: {patch_id}
project: {project_name}
generated_at: {now}
source_command: flg closeout --llm
source_transcript: {str(transcript)}
risk_level: medium
status: pending_review
mode: llm
llm_model: {llm_model}

---

## 1. Session Summary

{summary}

## 2. Candidate Decisions (LLM Extracted)

{candidate_decisions}

## 3. Suggested Next Actions

(LLM extraction mode does not analyze next actions. Run 'flg closeout --no-llm' for keyword-based extraction with next-action analysis.)

## 4. Risks

(LLM extraction mode does not analyze risks. Run 'flg closeout --no-llm' for keyword-based risk detection.)

## 5. Open Questions

(LLM extraction mode does not analyze questions.)

## 6. Goal Evolution Signals

(not analyzed in LLM mode)

## 7. Evidence Excerpts

### Decisions

"""
    for d in llm_decisions:
        patch_content += f"> {d['content'][:200]}\n\n"

    patch_content += f"""
## 8. Needs Human Review

- [ ] Review ALL {len(llm_decisions)} LLM-extracted candidate decisions
- [ ] Confirm each decision is a real decision (LLM may hallucinate or over-extract)
- [ ] Fill in reasoning, alternatives, and reversal conditions where LLM marked "not detected"
- [ ] Reject any false positives
- [ ] Consider running 'flg closeout --no-llm' for complementary keyword-based extraction

---

*Generated by flg closeout --llm v0.2.3*
"""

    patch_path = create_patch(root, patch_id, patch_content)
    add_pending_patch(root, patch_id, str(patch_path), "medium", source_command="flg closeout --llm")

    # Refresh snapshot with LLM decisions
    llm_decisions_for_snapshot = [
        {"content": d["content"][:100]} for d in llm_decisions
    ]
    _refresh_snapshot(root, llm_decisions_for_snapshot, [], [], state)

    console.print()
    console.print(f"[bold green]✓ LLM extraction complete (v0.2.3)[/bold green]")
    console.print()
    console.print(f"Transcript: {transcript}")
    console.print(f"LLM: {llm_model}")
    console.print(f"Patch: {patch_path}")
    console.print(f"Decisions found: {len(llm_decisions)}")
    console.print()
    console.print("Next steps:")
    console.print("  1. Review the patch — LLM decisions need human confirmation")
    console.print("  2. Confirm or reject each candidate decision")
    console.print("  3. Run: flg merge --patch <file>")


def _do_keyword_closeout(
    root: Path,
    transcript: Path,
    content: str,
    project_name: str,
    state: dict | None,
    mode: str,
) -> None:
    """Keyword-based closeout: the original extraction pipeline."""
    # Extract content
    decisions = extract_decisions(content)
    risks = extract_risks(content)
    open_questions = extract_open_questions(content)
    next_actions = extract_next_actions(content)
    rationale_excerpts = extract_rationale_excerpts(content)
    lessons_learned_signals = extract_lessons_learned_signals(content)
    goal_shifts = extract_goal_shifts(content)

    # Apply limits for concise mode
    if mode == "concise":
        decisions = decisions[:5]
        risks = risks[:3]
        open_questions = open_questions[:5]
        next_actions = next_actions[:5]
        rationale_excerpts = rationale_excerpts[:5]
        lessons_learned_signals = lessons_learned_signals[:5]
        goal_shifts = goal_shifts[:3]

    # Build sections
    now = get_iso_now()

    # Summary
    summary_lines = [
        f"- Candidate decisions pending review: {len(decisions)}",
        f"- Risks requiring attention: {len(risks)}",
        f"- Open questions captured: {len(open_questions)}",
        f"- Suggested next actions captured: {len(next_actions)}",
    ]
    if decisions:
        summary_lines.append(f"- Highest-confidence decision signal: {generate_decision_title(decisions[0]['content'])}")
    summary = "\n".join(summary_lines[:5])

    # Build candidate decisions section
    candidate_decisions = ""
    if decisions:
        for i, d in enumerate(decisions, 1):
            title = generate_decision_title(d["content"])
            reasoning = d.get("reasoning", "")
            rejected = d.get("rejected_alternatives", "")
            reversal = d.get("reversal_conditions", "")
            relations = infer_decision_relations(d, next_actions, content)
            related_goals = "; ".join(relations["related_goals"])
            related_docs = "; ".join(relations["related_docs"])
            related_assets = "; ".join(relations["related_assets"])
            affected_actions = "; ".join(relations["affected_actions"])

            # Quality gate: flag shell decisions (no reasoning/alternatives/reversal).
            # These stay in the patch but get low_confidence so review won't
            # silently accept them into DECISIONS.md via --accept-all.
            why_label = why_this_is_a_decision(d)
            confidence = d["confidence"]
            suggested_action = "needs_review"
            if is_shell_decision(reasoning, rejected, reversal):
                confidence = "low"
                why_label = f"{why_label}; low_confidence_shell (no reasoning/alternatives/reversal detected)"
                suggested_action = "needs_review_blocked_accept_all"

            candidate_decisions += f"""
### Candidate Decision {i}: {title}

status: pending_review
confidence: {confidence}
decision_type: {d['type']}
why_this_is_a_decision: {why_label}
**What was decided:** {d['content']}
**Why:** {reasoning if reasoning else '(not detected in context)'}
**Alternatives mentioned:** {rejected if rejected else '(not detected in context)'}
**Rejected because:** {rejected if rejected else '(not detected in context)'}
**Could reverse if:** {reversal if reversal else '(not detected in context)'}
**Related goals:** {related_goals}
**Related docs:** {related_docs}
**Related assets:** {related_assets}
**Affected actions:** {affected_actions}
**Supersedes:** {relations['supersedes']}
source_excerpt: > {d['content']}
suggested_action: {suggested_action}

"""
    else:
        candidate_decisions = "(no candidate decisions extracted)\n"

    # Build next actions section
    next_actions_text = ""
    if next_actions:
        for action in next_actions:
            next_actions_text += f"- {action}\n"
    else:
        next_actions_text = "(none identified)\n"

    # Build risks section
    risks_text = ""
    if risks:
        for r in risks:
            risks_text += f"- {r['content']} (type: {r['type']})\n"
    else:
        risks_text = "(none identified)\n"

    # Build open questions section
    questions_text = ""
    if open_questions:
        for q in open_questions:
            questions_text += f"- {q}\n"
    else:
        questions_text = "(none identified)\n"

    goal_shifts_text = ""
    if goal_shifts:
        for shift in goal_shifts:
            goal_shifts_text += f"- {shift}\n"
    else:
        goal_shifts_text = "(none identified)\n"

    # Build evidence section
    evidence = ""
    if decisions:
        evidence += "### Decisions\n\n"
        for d in decisions:
            evidence += f"> {d['content']}\n\n"
    if risks:
        evidence += "### Risks\n\n"
        for r in risks:
            evidence += f"> {r['content']}\n\n"
    if not evidence:
        evidence = "(no evidence extracted)\n"

    # Build rationale excerpts section
    rationale_text = ""
    if rationale_excerpts:
        for excerpt in rationale_excerpts:
            rationale_text += f"> {excerpt}\n\n"
    else:
        rationale_text = "(none identified)\n"

    # Build lessons learned signals section
    lessons_text = ""
    if lessons_learned_signals:
        lessons_text = "检测到经验回收信号，请人工填写 LESSONS_LEARNED.md\n\n"
        for signal in lessons_learned_signals:
            lessons_text += f"> {signal}\n\n"
    else:
        lessons_text = "(none identified)\n"

    # Create patch
    patch_id = generate_patch_id("closeout")

    patch_content = f"""# FLG Patch

patch_id: {patch_id}
project: {project_name}
generated_at: {now}
source_command: flg closeout
source_transcript: {str(transcript)}
risk_level: medium
status: pending_review
mode: {mode}

---

## 1. Session Summary

{summary}

## 2. Candidate Decisions

{candidate_decisions}

## 3. Suggested Next Actions

{next_actions_text}

## 4. Risks

{risks_text}

## 5. Open Questions

{questions_text}

    ## 6. Goal Evolution Signals

    {goal_shifts_text}

    ## 7. Evidence Excerpts

    {evidence}

    ## 8. Rationale Excerpts (thinking process)

    {rationale_text}

    ## 9. Lessons Learned Trigger

    {lessons_text}

    ## 10. Needs Human Review

    - [ ] Review candidate decisions
    - [ ] Review goal evolution signals
    - [ ] Review suggested next actions
    - [ ] Confirm or reject each decision
- [ ] Evaluate risks
- [ ] Address open questions
- [ ] Fill in LESSONS_LEARNED.md if signals detected

---

*Generated by flg closeout*
"""

    patch_path = create_patch(root, patch_id, patch_content)

    # Update state
    add_pending_patch(root, patch_id, str(patch_path), "medium", source_command="flg closeout")

    # Display results
    console.print()
    console.print(f"[bold green]✓ Closeout patch generated[/bold green]")
    console.print()
    console.print(f"Transcript: {transcript}")
    console.print(f"Patch: {patch_path}")
    console.print(f"Mode: {mode}")
    console.print()
    console.print(f"Extracted items:")
    console.print(f"  - Decisions: {len(decisions)}")
    console.print(f"  - Risks: {len(risks)}")
    console.print(f"  - Open Questions: {len(open_questions)}")
    console.print(f"  - Next Actions: {len(next_actions)}")
    console.print(f"  - Rationale Excerpts: {len(rationale_excerpts)}")
    console.print()

    # Refresh SNAPSHOT.md for Agent Startup Context Protocol
    _refresh_snapshot(root, decisions, risks, next_actions, state)

    console.print("Next steps:")
    console.print("  1. Review the patch file")
    console.print("  2. Confirm or reject candidate decisions")
    console.print("  3. Update project files as needed")
    console.print("  4. Mark patch as reviewed in state")

    # Capture pipeline awareness: check for pending captures
    captures_dir = root / ".flg" / "captures"
    if captures_dir.exists():
        import yaml as _yaml
        pending = 0
        for cf in captures_dir.glob("cap-*.md"):
            try:
                raw = cf.read_text(encoding="utf-8")
                m = re.match(r"^---\s*\n(.*?)\n---", raw, re.DOTALL)
                if m:
                    meta = _yaml.safe_load(m.group(1))
                    if isinstance(meta, dict) and meta.get("status") == "pending_review":
                        pending += 1
            except Exception:
                pass
        if pending:
            console.print()
            console.print(f"[yellow]⚠ {pending} pending capture(s) await review.[/yellow]")
            console.print("[dim]Run 'flg capture review' to confirm or reject them.[/dim]")


def _refresh_snapshot(
    root: Path,
    decisions: list[dict],
    risks: list[dict],
    next_actions: list[str],
    state: dict | None,
) -> None:
    """Refresh SNAPSHOT.md — a ~2KB file that gives an agent current project state.

    Part of the Agent Startup Context Protocol: SNAPSHOT.md is the first of
    three sources every agent must read on entry.
    """
    from ..templates import SNAPSHOT_MD

    now = get_iso_now()
    current_stage = state.get("current_stage", "unknown") if state else "unknown"

    # Current goal: try FRAMING.md first, fall back to state
    current_goal = _read_framing_goal(root)

    # Judgments from latest decisions
    if decisions:
        judgment_lines = [f"- {d['content'][:100]}" for d in decisions[:3]]
        judgments = "\n".join(judgment_lines)
    else:
        judgments = "- (no recent decisions)"

    # Confirmed vs unconfirmed
    confirmed = "- (review pending patches)"
    unconfirmed = f"- {len(decisions)} candidate decisions pending review"

    # Risks
    if risks:
        risk_lines = [f"- {r['content'][:120]}" for r in risks[:3]]
        risks_text = "\n".join(risk_lines)
    else:
        risks_text = "- (none identified)"

    # Next action
    next_action = next_actions[0] if next_actions else "Review pending patches"

    content = SNAPSHOT_MD.format(
        updated_at=now,
        current_stage=current_stage,
        current_goal=current_goal,
        judgments=judgments,
        confirmed=confirmed,
        unconfirmed=unconfirmed,
        risks=risks_text,
        next_action=next_action,
    )
    snapshot_path = root / "SNAPSHOT.md"
    snapshot_path.write_text(content, encoding="utf-8")


def _read_framing_goal(root: Path) -> str:
    """Extract the current goal from FRAMING.md Goals section."""
    framing_path = root / "FRAMING.md"
    if not framing_path.exists():
        return "(FRAMING.md not found)"
    content = framing_path.read_text(encoding="utf-8")
    # Look for ## Goals section
    goal_match = re.search(r"## Goals?\n\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if goal_match:
        goal_text = goal_match.group(1).strip()
        # Take first 3 non-empty lines
        lines = [l.strip("- ") for l in goal_text.split("\n") if l.strip() and not l.strip().startswith("<!--")]
        return "; ".join(lines[:3])[:200] or "(goals section empty)"
    return "(no goals defined)"
