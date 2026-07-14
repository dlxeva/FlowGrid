# FlowGrid Future Direction

> This document captures product-level insights from real-project usage and
> external research. Items here are NOT committed roadmap — they are validated
> directions waiting for the right timing and design maturity.

---

## Product Positioning Evolution

FlowGrid's positioning has been clarified through three converging insights:

| Insight | Source | Framing |
|---|---|---|
| Context Compiler | AI思考白板 A/B validation | FLG compresses project judgment chains into high-signal context for any model |
| Direction Engineering | AI思考白板 concept work | FLG organizes uncertainty into reviewable, actionable direction before execution |
| Cognitive Router | 认知四象限 discussion (2026-07-15) | FLG manages cognitive boundaries, routing each type of unknown to its proper handling protocol |

These are three angles of the same product identity:

> **FlowGrid is a cognitive state management and collaboration routing layer for
> non-coding knowledge workers working with AI agents.**

The decision log is the backbone. The broader system manages the full cognitive
lifecycle: judgment traces → assumptions → unknowns → decisions → evidence →
revisions.

---

## Direction 1: From Decision Log to Cognitive Account (发现 34)

### Problem

FLG currently records "what was decided and why." But the full judgment lifecycle
also includes:

- **Signals** (judgment traces): what the user reacted to, rejected, revised —
  the source of implicit-to-explicit migration (Q3→Q1)
- **Assumptions**: what the decision currently depends on (Q2)
- **Unknowns**: what is not yet resolved, including unknown-unknowns (Q4)
- **Evidence**: what validates the decision

Most of these have homes in FLG already (RATIONALE_TRAIL, Open Questions,
Unconfirmed, evidence_index), but they are scattered and not linked to individual
decision entries.

### Proposed Expansion

Extend the decision record to carry full cognitive context:

```yaml
decision:
  choice: "use two-layer status model"
  signals:               # judgment traces → Q3→Q1 source
    - "user repeatedly objected to AI silently rewriting formal state"
    - "handoff contained unconfirmed info treated as fact"
  rejected:              # negative path (high information density)
    - "write all state directly to main ledger"
    - "rely on git history alone"
  assumptions:           # current dependencies (Q2)
    - "user will process pending patches regularly"
    - "pending will not accumulate indefinitely"
  unknowns:              # unresolved questions (Q2/Q4)
    - "will non-technical users understand pending status?"
    - "will review cost rise over long-term use?"
  evidence:
    - "handoff validation passed"
    - "24 tests passing"
  confidence: medium
```

### Differentiation from Anthropic

Anthropic's Thariq Shihipar published "Finding Your Unknowns" (2026-07):
single-session blindspot discovery via blindspot pass, multi-prototype
elicitation, structured interviews.

FlowGrid's direction is "Managing Your Unknowns": cross-session cognitive
boundary maintenance via state, logs, hooks, and verification.

> Thariq teaches how to find unknowns. FlowGrid ensures teams and agents never
> lose them again.

### Status

`observed → product direction`. Needs: field-compatibility design with current
DECISIONS.md template, decision on manual vs auto-population. Target: v0.4.

---

## Direction 2: Quadrant Tags and Protocol Routing (发现 35)

### Problem

"Managing Your Unknowns" requires knowing which cognitive quadrant a task or
judgment is in, because each quadrant needs a fundamentally different agent
behavior:

| Quadrant | What it means | Agent role | Protocol | Wrong handling |
|---|---|---|---|---|
| Q1: known knowns | Explicit ability | Executor | Execute | AI re-explains, slows down |
| Q2: known unknowns | Identified gaps | Researcher | Research | AI fakes certainty, gives conclusion |
| Q3: unknown knowns | Implicit expertise | Elicitor | Elicit | AI asks user to explain from scratch |
| Q4: unknown unknowns | Blind spots | Challenger | Audit | AI does shallow reflection, declares done |

### Proposed Extensions

1. **Quadrant tags**: add `--quadrant Q1|Q2|Q3|Q4` to `flg capture`. Each
   candidate judgment carries its cognitive state. Context Pack can group by
   quadrant.

2. **Protocol routing**: system identifies quadrant, selects protocol. "What's
   next?" is no longer free-form AI improvisation — it routes to Research,
   Elicit, or Audit based on the cognitive state.

3. **Migration records**: track how a judgment moves between quadrants (e.g.
   Q3→Q1 implicit-to-explicit, Q4→Q2 blind-spot-named-to-known-unknown). This
   is the real judgment chain — not just the final decision.

4. **Hard triggers**: `flg closeout --cognitive-audit` forces four questions
   (what was confirmed / what known-unknowns remain / what implicit judgments
   surfaced / what blind spots were found). Empty scan blocks "complete" status.

### Status

`observed → product direction`. Quadrant routing (direction 2) needs semantic
classification capability — keyword matching won't work (validated by closeout
detection quality issues). Quadrant tags (direction 1) is the feasible first
step. Target: v0.4+.

---

## Direction 3: Trigger Standardization (发现 27/28)

### Problem

FLG has the tools (CONTRACT.md, capture, closeout, review) but lacks the trigger
mechanism. No system tells the agent "now is the moment to capture." Codex
wrote its own FLG skill to fill this gap — multiple hosts independently hit the
same wall.

### Proposed Solution

Define "what counts as a decision worth recording" as explicit rules:

**Record:** architecture choices, mechanism discoveries, rejected directions,
design constraints, inferred-but-unverified judgments.

**Do NOT record:** routine bug fixes, single-file edits, debug steps,
work-plan priority lists.

The standard skill (`skills/flowgrid-operator/SKILL.md`) now carries these rules
(v0.3.0+). The next step is making them enforceable rather than advisory.

### Status

`confirmed`. Standard skill shipped (PR #11). Enforcement mechanism (capture
profile auto-consumption or closeout hooks) is the open design question. Target:
v0.4.

---

## Direction 4: Context Pack Layering (发现 18/30)

### Problem

`flg context` currently dumps everything into one pack. Progressive disclosure
stays at the documentation level — there is no "give me layer 1, expand to
layer 2 if needed" mechanism.

### Proposed Solution

Align with AI思考白板's three-layer Prompt Package structure:

| Layer | AI思考白板 | FLG equivalent |
|---|---|---|
| Raw event timeline | Complete session records | Session transcripts + raw operations |
| Semantic event timeline | Compressed judgment chain | DECISIONS.md |
| Memory state timeline | Concept/methodology evolution | GOAL_EVOLUTION + state |

Context Pack should distinguish Raw Package (complete records) from Model
Package (compressed judgment chain), defaulting to Model Package.

### Status

`observed`. Current 3.5KB pack is sufficient for most scenarios. Layering
becomes necessary when "context pack information overload" is reported across
multiple projects. Target: v0.4+.

---

## Priority Summary

Revised 2026-07-15 based on epistemic state governance review (发现 37-41).
Core principle: **stop adding abstraction layers; prioritize entry reliability
and real-world closed-loop.**

### Immediate engineering (v0.4 core)

| Direction | Feasibility | Impact | Finding |
|---|---|---|---|
| **Index rebuild from ledger** (`flg doctor` / `flg reindex`) | Low complexity | **Critical** | 37 |
| **Entry reliability** (sessions empty in real projects) | Medium design | **Critical** | 38 |
| **Real-project evaluation** (long, dirty, contradictory histories) | Medium | High | 40 |

### Near-term (v0.4 if capacity allows)

| Direction | Feasibility | Impact | Finding |
|---|---|---|---|
| Frame inference (derive from SNAPSHOT, not blank template) | Medium | Medium | 39 |
| Context pack layering (Raw/Model/Memory) | Medium design | Medium | 18/30 |

### Deferred — do NOT add to v0.4 (发现 41 product discipline)

| Direction | Why deferred |
|---|---|
| Cognitive account (decision field expansion: signals/assumptions/unknowns) | Valid direction but adds complexity before entry reliability is solved |
| Quadrant tags (`capture --quadrant`) | Low complexity but premature before P0/P1 land |
| Quadrant protocol routing (Execute/Research/Elicit/Audit) | High complexity, needs semantic classification that keyword matching can't deliver |
| Migration records (quadrant transitions) | Depends on quadrant tags |
| Blindspot pass (Q4 discovery) | Wait until entry + index + eval are solid (P3) |

> The system is already increasingly rigorous internally. The real risk is
> that real user judgments may not be reliably entering the system. Next phase
> priority: **entry reliability and real-world closed-loop.**

---

## References

- `FLG_COGNITIVE_QUADRANTS_AND_UNKNOWN_MANAGEMENT.md` (Vault) — cognitive quadrants discussion
- `FLG_EPISTEMIC_STATE_GOVERNANCE_REVIEW.md` (Vault) — governance review with risk analysis
- ITERATION_LOG 发现 27/28/30/32/34-41 — related findings
- `docs/product/v0.3-plan.md` — current execution plan
- Anthropic "Finding Your Unknowns" (Thariq Shihipar, 2026-07) — external convergence
