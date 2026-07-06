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
from ..templates import CLOSEOUT_PATCH_MD, DECISION_PROMPT_TEMPLATE, get_iso_now
from ..llm_client import call_llm, parse_llm_response, get_llm_config

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
    ],
    # Explicit trade-off
    "tradeoff": [
        "不做", "放弃", "改成", "取代", "优先", "延后",
        "先做", "后做", "暂停", "进入下一阶段", "不是重点",
        "放弃", "选择", "取舍", "边界",
        "不做.*选", "先做.*延后", "这个不是重点",
        "not doing", "deprioritize", "trade-off", "choose A over B",
    ],
    # Project state change
    "state_change": [
        "目标变化", "边界变化", "版本范围", "试点对象",
        "下一步动作", "责任对象",
        "goal changed", "scope changed", "priority shifted",
    ],
    # Human confirmation signal
    "human_signal": [
        "用户确认", "用户拍板", "用户同意", "用户要求写入",
        "用户要求调整", "用户决定", "用户选择",
        "user confirmed", "user approved", "user decided",
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

    for sentence in iter_segments(content):
        if not sentence or len(sentence) < 10:
            continue

        # Guard: skip sentences that describe risks (e.g. "KOLs we confirmed might cancel").
        # These contain confirmation words but the sentence is about a risk, not a decision.
        if match_pattern(sentence, RISK_SENTENCE_PATTERNS):
            continue

        # Check for explicit confirmation
        keyword = match_pattern(sentence, DECISION_KEYWORDS["confirmation"])
        if keyword:
            ctx = _get_context_window(content, sentence)
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
        keyword = match_pattern(sentence, DECISION_KEYWORDS["tradeoff"])
        if keyword:
            ctx = _get_context_window(content, sentence)
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
        keyword = match_pattern(sentence, DECISION_KEYWORDS["state_change"])
        if keyword:
            ctx = _get_context_window(content, sentence)
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
        keyword = match_pattern(sentence, DECISION_KEYWORDS["human_signal"])
        if keyword:
            ctx = _get_context_window(content, sentence)
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
    r"不做.*",
    r"放弃.*",
    r"instead of\b",
    r"rather than\b",
    r"not choosing\b",
    r"ruled out\b",
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


def closeout_session(
    transcript: Path = typer.Option(..., "--transcript", "-t", help="Path to transcript markdown"),
    mode: str = typer.Option("concise", "--mode", "-m", help="Output mode: concise, full, or prompt"),
    prompt_only: bool = typer.Option(False, "--prompt", "-p", help="Generate LLM prompt for decision extraction (no keyword matching)"),
    llm: bool = typer.Option(False, "--llm", "-l", help="Call LLM API directly for decision extraction (requires API key)"),
    provider: Optional[str] = typer.Option(None, "--provider", help="LLM provider override (openai, anthropic, custom)"),
    force: bool = typer.Option(False, "--force", help="Allow closeout on structured ledger files (not recommended)"),
) -> None:
    """Generate closeout patch from session transcript.

    Modes:
      - concise: keyword-based extraction, capped results (default)
      - full: keyword-based extraction, all results
      - prompt: generate LLM prompt for 9-field decision extraction (--prompt flag)
      - llm: call LLM API directly for 9-field extraction (--llm flag)
    """
    root = Path.cwd()
    
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

    # Prompt mode: generate LLM prompt instead of keyword extraction
    if prompt_only:
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
        return

    # LLM mode: call LLM API directly for decision extraction
    if llm:
        prompt_content = DECISION_PROMPT_TEMPLATE.format(transcript=content)
        
        console.print()
        console.print("[bold blue]Calling LLM for decision extraction...[/bold blue]")
        console.print()
        
        try:
            llm_response = call_llm(prompt_content, provider=provider)
        except Exception as e:
            console.print(f"[red]LLM extraction failed: {e}[/red]")
            console.print("[yellow]Falling back to prompt mode...[/yellow]")
            # Fall back to prompt mode
            prompt_path = root / ".flg" / "patches" / f"decision-prompt-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_path.write_text(prompt_content, encoding="utf-8")
            console.print(f"Prompt saved to: {prompt_path}")
            raise typer.Exit(1)
        
        # Parse LLM response
        llm_decisions = parse_llm_response(llm_response)
        
        if not llm_decisions:
            console.print("[yellow]LLM found no decisions in this conversation.[/yellow]")
            console.print("[dim]If you believe there are decisions, try: flg closeout --transcript <file> --prompt[/dim]")
            return
        
        # Create patch with LLM extracted decisions
        patch_id = generate_patch_id("closeout-llm")
        now = get_iso_now()
        
        patch_content = f"""# FLG Patch (LLM Extracted)

patch_id: {patch_id}
project: {project_name}
generated_at: {now}
source_command: flg closeout --llm
source_transcript: {str(transcript)}
risk_level: medium
status: pending_review
mode: llm

---

## LLM Extraction Result

The following decisions were extracted by LLM ({get_llm_config()['model']}).

{llm_response}

---

## Needs Human Review

- [ ] Review extracted decisions
- [ ] Confirm each decision matches the 9-field template
- [ ] Merge confirmed decisions to DECISIONS.md

---

*Generated by flg closeout --llm*
"""
        
        patch_path = create_patch(root, patch_id, patch_content)
        add_pending_patch(root, patch_id, str(patch_path), "medium", source_command="flg closeout --llm")
        
        console.print()
        console.print(f"[bold green]✓ LLM extraction complete[/bold green]")
        console.print()
        console.print(f"Transcript: {transcript}")
        console.print(f"Patch: {patch_path}")
        console.print(f"Decisions found: {len(llm_decisions)}")
        console.print()
        console.print("Next steps:")
        console.print("  1. Review the patch file")
        console.print("  2. Confirm or reject extracted decisions")
        console.print("  3. Run: flg merge --patch <file>")
        return

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
    date = datetime.now().strftime("%Y-%m-%d")
    
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
            candidate_decisions += f"""
### Candidate Decision {i}: {title}

status: pending_review
confidence: {d['confidence']}
decision_type: {d['type']}
why_this_is_a_decision: {why_this_is_a_decision(d)}
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
suggested_action: needs_review

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

    # Build rationale excerpts section (low-risk, thinking process)
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
