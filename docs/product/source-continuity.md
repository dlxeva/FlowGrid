# Source review and processing continuity

An AI host can preserve the exact passage it reviewed, link it to existing work
and judgments, and recover that processing in a fresh session. FlowGrid checks
byte versions and explicit declarations. The host interprets the material and
checks who has authority to decide.

## Discover sources

`flg source inventory` reads `.flg/sessions` and `docs/meetings` directly, and
up to three subdirectories under `sources/meetings`. Roles distinguish
transcripts, manual notes, generated summaries, and raw responses. Filename
inference does not establish authorship. JSON/XML remain metadata. Artifacts
grouped into one meeting do not count as independent corroboration.

`flg source inventory --config source-roots.json` can replace roots for that
query, using `{"version":1,"roots":[{"path":"research/interviews","max_depth":2}]}`.
Discovery is bounded by depth, entries, and byte limits; generated, temporary,
people, and audit directories are excluded. No Wiki is required.

## Declare the actual review

The host prepares a JSON record with these fields:

| Field | Meaning |
| --- | --- |
| `id`, `verified_at`, `status`, `remaining` | Processing identity, review time, stage, unfinished work |
| `source.path`, `source.sha256`, `source.quote` | Exact project-relative UTF-8 source, complete byte hash, actual quote |
| `source.derived_from` (optional) | One-hop originals with path, SHA-256, and `extracted_from`, `transcribed_from`, or `summarized_from` relation |
| `targets` | Existing work references with path, complete SHA-256, and inspectable text anchor |
| `continuity.schema_version` | `1` |
| `continuity.coverage`, `continuity.spans` | `excerpt` or `full`; 1-based inclusive line ranges, exact quotes, attribution boundaries |
| `continuity.judgments` | Existing D IDs, original block hash, old-condition quote, new impact, reason, span index, next-action candidate |
| `continuity.no_judgment_reason` | Required when no judgment is affected |

Dispositions are `retain`, `supplement`, `implementation_changed`,
`replacement_candidate`, and `unresolved`. None approves a formal decision.
The D block hash includes its heading through the next D heading, trimmed.
Complete executable synthetic examples are in `tests/test_source_receipts.py`.

```bash
flg source prepare --input review.json --output candidate.json
flg source pending
flg source record --input candidate.json --expected-sha256 absent
```

Prepare fills omitted span quotes from the already-declared source version;
it rejects a wrong supplied quote and never overwrites a candidate. It does
not infer decisions, attribution, or fresh hashes. For an existing receipt
file, use `state_sha256` from `source pending` instead of `absent`.

Registration uses the existing project operation lock, a version check, and
atomic replacement of `.flg/processing-receipts.json`. It preserves old records
and writes no formal decisions or work documents. Missing historic fingerprints
remain unknown. Excerpts stay partial; full coverage requires every source line
and valid target evidence. Pending judgment changes cannot be absorbed.
Processing scope does not prove comprehension, transcription completeness,
authority, or business acceptance. Project adapters retain any additional
people or approval gates they require.

## Resume, expand, and retry

```bash
flg source pending --judgment D-001
flg source show RECEIPT_ID
flg source trace sources/meetings/pilot/transcript.md
flg source trace work.md --receipt RECEIPT_ID
flg context --mode resume
flg context --mode manifest
flg context --mode work
```

Pending returns at most 12 summaries by default; show expands one receipt.
Exact reverse filtering precedes the display cap. Trace checks body and original
versions independently; filenames do not imply a relationship. All context modes
reserve a compact review notice and leave raw text out of startup context.
Insufficient budgets fail explicitly rather than silently dropping required work.

Source, target, or D drift requires review and hides obsolete candidate actions.
This first implementation binds entire target files, so unrelated edits within
the same target file also request review. Formal decision status is unchanged.
An exact retry recognizes a historical successful commit before checking current
validity. A new transport ID for the same review does not duplicate processing;
a changed payload under the same ID is refused. Atomic-write failure retains
the prior receipt file for retry.

If a fresh review replaces a stale processing receipt, register the new review,
then run `flg source resolve OLD_ID --replacement NEW_ID --reason "Revalidated"
--expected-sha256 HASH`. The replacement must be current and cover the same
source, previous work references, judgment IDs, and original references. The
replacement preserves full coverage or every prior partial line range. The
resolution retains prior acknowledgments. The old
receipt remains inspectable; later drift is tracked through the replacement.
It does not replace a formal decision.

```bash
flg source pending --reminders
flg source acknowledge RECEIPT_ID --outcome shown --reason "Actually displayed" --expected-sha256 HASH
flg source acknowledge RECEIPT_ID --outcome completed --reason "Review completed" --expected-sha256 HASH
```

Acknowledgments bind the receipt version in the same processing file. `shown`
suppresses another reminder; `completed` and `rejected` close its suggestion.
Drift remains visible after closure while old actions stay suppressed. Ordinary
reads never pretend a display occurred. No watcher or automatic host hook runs.

## Validation scope

Portable regressions use synthetic evidence and cover conflicts, scope,
attribution boundaries, no promotion, closure, drift, retries, reverse lookup,
and a fresh Python process. Private project replays remain local.
An earlier eight-event real-source exercise exposed a discovery gap and detail
omissions, but lacked historical T/D snapshots for a complete adaptation A/B.
No universal continuation or reasoning benefit is claimed from those results.

The provider-neutral knowledge-source RFC remains future adapter work. This
filesystem processing interface does not implement those providers or a Wiki.
