# Host-Like Continuation Safety Acceptance - 2026-07-20

## Scope

This is a local reference-host acceptance replay against a disposable copy of
an existing, non-code content project. It validates FlowGrid's background
closeout/review/merge boundary using a real labelled raw session. It is not an
external-host, design-partner, retention, or usability validation.

## Procedure

1. Copy an existing FlowGrid project to a temporary directory; leave the source
   project untouched.
2. Record SHA-256 hashes for `DECISIONS.md` and `SNAPSHOT.md`.
3. Run `closeout --no-llm --mode concise` on a real raw session containing both
   `User:` and `Assistant:` turns.
4. Run `review --report-only`, then `review --autonomous`, then `merge --yes`.
5. Recheck formal-file hashes, patch lifecycle, and the generated Context Pack.

## Observed Input

The keyword extractor produced one candidate from an `Assistant:` proposal.
The candidate was not a user/client commitment and did not contain enough
reasoning for autonomous adoption.

## Results

- `review --report-only` surfaced the candidate without writing ledger state.
- `review --autonomous` skipped the candidate; no decision was accepted.
- `merge --yes` appended routine progress and closed the patch.
- `DECISIONS.md` SHA-256 was unchanged before and after the flow.
- `SNAPSHOT.md` SHA-256 was unchanged before and after the flow.
- `flg status` reported no pending patch after merge.
- The generated Context Pack reported zero pending patches and did not contain
  the assistant proposal.

## Interpretation

The reference-host loop now preserves the intended safety boundary for this
real-session case: an agent proposal can remain auditable as a candidate but
cannot become formal project truth through background processing.

This does **not** prove that a real external host automatically supplies clean,
speaker-labelled transcripts, nor that an external user experiences zero CLI
burden. Those remain the next acceptance criteria.
