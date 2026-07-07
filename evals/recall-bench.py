#!/usr/bin/env python3
"""FLG closeout recall benchmark — compares extraction output against golden decisions.

Usage:
    python3 recall-bench.py                          # keyword baseline
    python3 recall-bench.py --mode llm               # LLM extraction (needs API key)
    python3 recall-bench.py --mode hermes --json <f>  # hermes-assisted (needs result JSON)

Reports per-scenario and overall recall rate.
"""
import json, re, sys
from pathlib import Path
from typing import Optional

EVALS_DIR = Path(__file__).resolve().parent.parent / "evals" / "scenarios"
SCENARIOS = ["campaign-proposal", "client-solution-proposal", "operations-mechanism-design"]


def parse_golden(scenario_dir: Path) -> list[str]:
    """Extract decision statements from golden-decisions.md."""
    text = (scenario_dir / "golden-decisions.md").read_text()
    decisions = []
    for m in re.finditer(r"### Decision\n(.+?)(?=\n###|\Z)", text, re.DOTALL):
        decisions.append(m.group(1).strip())
    return decisions


def fuzzy_match(extracted: str, goldens: list[str]) -> bool:
    """Check if an extracted decision matches any golden decision (word overlap)."""
    ext_words = {w.lower() for w in re.findall(r"[A-Za-z]{3,}", extracted)}
    for g in goldens:
        g_words = {w.lower() for w in re.findall(r"[A-Za-z]{3,}", g)}
        overlap = ext_words & g_words
        min_len = min(len(ext_words), len(g_words))
        if min_len > 0 and len(overlap) >= min_len * 0.3:
            return True
    return False


def run_keyword_baseline() -> dict:
    """Run flg closeout --no-llm on each scenario and extract decisions."""
    import subprocess, tempfile

    results = {}
    for scenario in SCENARIOS:
        raw = EVALS_DIR / scenario / "raw-session.md"
        with tempfile.TemporaryDirectory() as tmp:
            # Init FLG project
            subprocess.run(
                ["/root/FlowGrid/.venv/bin/flg", "init", "bench"],
                cwd=tmp, capture_output=True,
            )
            # Run closeout
            r = subprocess.run(
                ["/root/FlowGrid/.venv/bin/flg", "closeout", "-t", str(raw), "--no-llm"],
                cwd=tmp, capture_output=True, text=True,
            )
            # Extract decisions from patches
            patches_dir = Path(tmp) / ".flg" / "patches"
            decisions = []
            for pf in patches_dir.glob("closeout-*.patch.md"):
                content = pf.read_text()
                for m in re.finditer(r"\*\*What was decided:\*\*\s*(.+?)(?=\n\*\*|\n\n|\Z)", content):
                    decisions.append(m.group(1).strip())
            results[scenario] = decisions
    return results


def report(scenario: str, extracted: list[str], goldens: list[str], verbose: bool = True):
    """Print recall report for one scenario."""
    matched = sum(1 for e in extracted if fuzzy_match(e, goldens))
    recall = matched / len(goldens) * 100 if goldens else 0
    if verbose:
        print(f"  {scenario}: {matched}/{len(goldens)} ({recall:.0f}%)")
        for i, e in enumerate(extracted):
            golden_match = any(fuzzy_match(e, [g]) for g in goldens)
            print(f"    {'✅' if golden_match else '❌'} {e[:80]}...")
    return matched, len(goldens)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["keyword", "llm", "hermes"], default="keyword")
    ap.add_argument("--json", type=Path, help="JSON result file (hermes mode)")
    args = ap.parse_args()

    if args.mode == "hermes":
        if not args.json or not args.json.exists():
            print("ERROR: --json <result.json> required for hermes mode", file=sys.stderr)
            sys.exit(1)
        data = json.loads(args.json.read_text())
        if isinstance(data, dict) and "decisions" in data:
            data = data["decisions"]
        extracted_map = {}
        for s in SCENARIOS:
            extracted_map[s] = [d.get("what", "") for d in data if isinstance(d, dict)]
    elif args.mode == "keyword":
        extracted_map = run_keyword_baseline()
    else:
        print("LLM mode requires API key. Use --mode hermes instead.", file=sys.stderr)
        sys.exit(1)

    total_golden = 0
    total_matched = 0
    for scenario in SCENARIOS:
        goldens = parse_golden(EVALS_DIR / scenario)
        extracted = extracted_map.get(scenario, [])
        m, g = report(scenario, extracted, goldens)
        total_matched += m
        total_golden += g

    print(f"\n  OVERALL: {total_matched}/{total_golden} ({total_matched/total_golden*100:.0f}%)")


if __name__ == "__main__":
    main()
