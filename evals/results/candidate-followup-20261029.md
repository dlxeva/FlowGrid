# Candidate follow-up validation

Date: 2026-10-29. Candidate implementation; no version tag or Release.

Synthetic tests cover legacy review/closed states, explicit waiting and closure
reasons, quote/file references, due dates, changed candidate basis, invalid YAML,
path boundaries, CAS, exact retries, same-file history, failed writes, read-only
collection, and no formal promotion. CLI tests exercise recording, on-demand
expansion, guarded automatic confirmation, context modes, handoff and a separate
process reading persisted review state. Ordinary waiting does not become an age
failure. Closure never changes original capture status or claim.

Private evidence alias: `private-dogfood@2026-10-29#candidate-followup-nine`.
The real nine-candidate isolated replay starts with five reviewed evidence waits
and four unreviewed entries. Explicit review records produce seven evidence waits
and two requests to reconcile newer evidence. All nine original pending statuses
and claims are retained; formal decisions, work ledger and control files are
protected. Existing confirmed and historical closed candidates stay outside the
new review queue. Legacy closure reasons remain unspecified where unknown.

Local full-suite verification passed 575 tests, with two Windows-only skips.
Native Windows verification and external publication are separate gates; no
cross-platform result is inferred from these local tests. Private input details,
names, original records and local paths are not included in this repository.

Independent synthetic reproduction found and drove fixes for legacy evidence
waits bypassing automatic-confirmation guards, status filtering after a display
cap, list output re-exposing drifted claims, and reference validation failures
not suppressing claims. All four original reproducers passed after correction;
the independent targeted run passed 101 tests.

The reviewed metadata was subsequently applied to the same nine private captures.
Exactly nine files gained follow-up metadata; all pre-existing fields and bodies
were preserved. The complete capture inventory remained nine pending, seven
confirmed and thirteen historically closed. The project-local recovery entry
now reports seven waits and two review requests, with no errors. Protected formal
and work/control files retained their fingerprints. Project adapter regressions
passed 422 tests and 390 subtests. This opt-in read-only recovery reader does not
replace the private project's customized base runtime.

The reader detects byte/quote changes and declared review dates. It does not
understand a free-text trigger, determine source authority, decide that a wait was
satisfied, or infer business approval. The nine-item exercise supports the review
mechanism and state preservation, not a general improvement in project outcomes
or retrospective completeness.
