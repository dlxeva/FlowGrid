# Source continuity validation

Date: 2026-10-29. Scope: explicit processing declarations and continuation
navigation in the filesystem CLI. Package version remains v0.3.0.

## Executable coverage

`tests/test_source_receipts.py` verifies source-to-work-to-judgment references,
immutable claims, exact and transport retries, source/target/D drift, partial
coverage, invalid completion claims, and explicit current replacements. Reads
preserve formal files and do not create state. Pending output is bounded;
details expand by receipt ID.

Eight synthetic cases cover two parameter/date changes, two rejection/reopen
events, two discussions, and two completed/accepted-work events. They verify
storage and review boundaries using host-supplied interpretations, without
evaluating automatic semantic extraction. Original labels and statements remain
in the reviewed spans; formal D status stays unchanged.

A separate Python process recovers the persisted notice through the public CLI.
Resume, Manifest, Work, Handoff and exported handoff preserve its pointer.
Insufficient budgets fail when required current work would otherwise be lost.

Inventory tests check bounded discovery, stable groups, configured roots, role
hints, raw-response metadata, exclusions and unsafe paths. Candidate I/O tests
cover exclusive creation, ancestry replacement, competing processes, partial
writes and resource release. Local verification passed 507 tests with two
Windows-only skips. Commit `4cb24b9` passed native Windows Python 3.12 and Linux
Python 3.10/3.11/3.12 in [run 40772529638](https://github.com/dlxeva/FlowGrid/actions/runs/40772529638).
This includes the native file-signature and directory-sharing correction after
the first Windows run failed. Simulated API tests alone were not accepted as
Windows verification.

## Independent review

Independent review reproduced issues and drove regressions for stale receipts
without a retirement path, reordered or transport-variant references reviving
rejected actions, self-certifying targets, raw JSON review claims, parent-path
redirection, narrowed replacements hiding unreviewed content, and a small budget
retaining notices while dropping current work.

The implementation normalizes semantic identity, preserves original claims and
acknowledgment history, requires a current replacement covering prior references
and reviewed ranges, checks reviewable sources and independent target evidence,
and pins candidate ancestry. POSIX can detect an observed moved directory inode
but cannot prevent another local process from moving an opened inode. No stronger
cross-file transaction claim is made.

## Private read-only portability

Evidence alias: `private-dogfood@2026-10-29#source-portability`.
The portable reader and an existing private adapter identified the same linked
judgments as requiring revalidation. Old actions were suppressed. Frozen source
fixtures retained their versions and remained discoverable. Protected source,
ledger, control and processing-file fingerprints matched before and after.
Private records, transcripts, identities, business quantities, paths and source
fingerprints stay outside this repository.

This is compatibility evidence. The earlier source-routing A/B lacked historical
T/D snapshots, and shared-input answers still omitted details. That limitation
remains open. No universal benefit, strict blind result, or completed longitudinal
effectiveness is claimed.

## Prospective current-state continuation

Evidence alias: `private-dogfood@2026-10-29#prospective-continuation`.
Before execution, one actual current project cut, input fingerprints, two views
and a review contract were frozen. Two fresh no-history agents inherited the
same model and reasoning settings and answered eight identical continuation
questions. Both views contained the same current work and expanded judgments;
the second additionally contained the portable source-review notice. The common
input cap was 20,000 characters and each answer was capped at 220 characters.

An independent text-only reviewer reported no hard errors or action-changing
omissions in either set of eight answers. The additional-notice answer explicitly
identified pending source review and kept it separate from formal approval.
The baseline also identified judgment conditions requiring review. This is a
bounded navigation observation, not an overall win or evidence of superior
reasoning. No answers were regenerated after grading.

Limits: one project cut rather than eight independent events; same-family
models; no strict blind evaluation; no longitudinal outcome. A source note was
date-labeled on the following local day relative to the UTC snapshot date; its
actual historical insertion time is not independently established. The snapshot
preserves captured contents, not a reconstructed historical T/D state. Detailed
inputs, answers and review evidence remain private.

## Reproduce

```bash
python -m pytest -q
python scripts/check_current_state.py
python scripts/smoke_test.py
```

Committed CI supplies Linux/Python and native Windows results. Synthetic tests,
fresh-process recovery and private read-only comparison support publication of
this bounded mechanism; broader effectiveness and future source-provider work
remain separate validation items.
