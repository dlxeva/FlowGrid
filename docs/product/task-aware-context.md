# Task-aware context (experimental, explicit query)

Use `flg context --mode resume --query "brand narrative and user agency"` when
the current task needs older project judgments. The host derives a short intent
from the user's request; the user does not maintain tags or ranking fields.
Without `--query`, existing context behavior is preserved. Manifest and Work
remain unchanged; combining them with a query explicitly fails in this slice.

## Selection and authority

The query selects from the existing formal decision ledger using explicit
decision IDs and deterministic English-word/Chinese-bigram matches. Up to three
matching valid judgments are combined with recent valid judgments in the
existing five-decision allocation. The navigation explains matches and links to
`flg evidence`. No embedding provider, remote model, background hook, additional
ledger or schema migration is introduced.

Non-current matches appear separately as reference-only history. Relevance does
not restore superseded decisions, approve candidates or authenticate evidence.
Declared status is retained. A lexical match is a retrieval aid, not a semantic
claim; the host must inspect the original source and existing evidence health.
No-match queries retain the recent-decision fallback and disclose the limitation.

When query terms overlap recorded reversal conditions, the pack asks for source
review. It does not claim that a condition is fulfilled. Existing source-review
receipts linked to selected judgments are expanded by ID; drift and pending
review continue to follow the existing source workflow. No receipt, candidate,
decision or current action is changed by reading.

## Budget and compatibility

The existing Current Action and constraint-source precedence retain their
authority. Query mode includes all parsed items from the selected Snapshot
constraint/non-goal sections, or the full noise-filtered CONSTRAINTS fallback;
it does not stop after the default view's six-item/seven-hundred-character caps.
This does not resolve contradictory or undeclared rules across project files.
A query pack that cannot fit the current work and review navigation raises an explicit
budget error; an old derived output is not overwritten on that failure. Increase
the budget or narrow the task. Evidence lookup can expand individual judgments.
The command writes its usual derived context output only, or an explicitly
chosen `--output` path. Raw sessions are not loaded automatically.
The selected ledger version is checked again before the builder returns. This
detects intervening changes; it is not a multi-file transaction or a guarantee
that project files cannot change after the view was generated.

This is a lexical recall slice. It may miss paraphrases, mixed-language synonyms,
implicit relationships and unrecorded conditions. Matching a word in a reversal
condition can be incidental. The host must verify current applicability; no
automatic reversal, decay, deletion or learning of ranking weights is provided.

## Evaluation scope

Synthetic availability checks compare the same-budget raw ledger, default
Resume and query Resume. They test whether a declared relevant judgment is
available and whether non-current history stays separate. Raw history can retain
all evidence in short examples, so this does not claim query Resume always wins.
These checks do not measure human decision quality, saved explanation time or
longitudinal benefit. A separately scoped real task must establish those outcomes.
