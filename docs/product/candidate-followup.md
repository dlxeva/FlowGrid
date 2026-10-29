# Candidate review and follow-up

Candidates can remain undecided for a good reason. Follow-up distinguishes
unreviewed captures, reviewed work awaiting evidence, reviews due after a declared
date or reference change, and explicit closures. Age never approves a judgment,
rejects it, or proves that nobody reviewed it.

`flg capture followups` displays actionable reviews. `--all` also includes waiting
and closed records; `--capture ID` expands one capture. Reads make no changes.
Status and recovery views summarize the queue without inserting every old claim
into current action. Handoff preserves a pointer for the next host.

The host reads the original claim, its attribution, prior review, relevant current
work and evidence before recording its review:

```bash
flg capture followups --capture CAPTURE_ID
flg capture followup-record CAPTURE_ID --input review.json --expected-sha256 CAPTURE_SHA
```

The JSON review uses `schema_version: 1`, `disposition`, `reason`, `reviewed_at`,
`waiting_for`, `review_trigger`, optional `review_after`, and `refs`.
Dispositions are `awaiting_evidence`, `needs_review`, `absorbed`, `expired`,
and `rejected`. A waiting record requires concrete missing evidence and a review
trigger. Absorbed, expired and rejected are distinct explicit dispositions, with
a reason and checked references. This command never writes a formal D entry or
changes the capture's original status or claim. Closure is never inferred from
age, text search failure, another pending record, or a read operation.

References contain `path`, `quote`, `sha256`, and `scope`. `scope: quote` binds
an exact unique quote and its UTF-8 hash; unrelated edits elsewhere in that file
do not reopen the review. `scope: file` binds the complete byte version. Both
retain project-relative locators and verify the declared quote. Version checks
detect changes, not their meaning; a host must inspect changes before deciding
whether the waiting condition was fulfilled. Free-text triggers are not executed
as semantic rules. Review dates request another look, not automatic closure.

Review history lives in the capture itself. The writer uses the existing project
lock, atomic replacement, and a compare-and-swap capture version. Exact retries
are idempotent; conflicting updates fail. Original fields and body remain.
Legacy `reviewed_at`, `review_disposition`, `waiting_for` and `review_trigger`
remain readable. Unversioned legacy references do not become retroactively
verified evidence. Automatic capture confirmation must not bypass an explicit
follow-up; approval remains on the existing authorized review path.

This is a host-operated workflow, with no background watcher or global hook.
An unchanged waiting item is available on demand without becoming a repeated
action alert. The first real-project validation preserves all nine original
pending statuses and formal files; detailed private evidence is not distributed.
