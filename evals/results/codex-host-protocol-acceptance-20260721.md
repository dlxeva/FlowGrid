# Codex Host Protocol Acceptance - 2026-07-21

## Scope

This acceptance run used a real FlowGrid project and the current Codex
conversation about the BIZ-to-FLG handoff. The host archived only the raw
conversation excerpt, then ran the ordinary background flow without asking the
user to invoke FlowGrid commands:

```text
session save -> closeout --no-llm -> review --report-only
-> review --autonomous -> merge --yes -> context -> doctor --strict
```

The source transcript included user questions and assistant explanations. It
did not include a user statement explicitly confirming the proposed BIZ
handoff policy.

## Result

`closeout` produced two candidate decisions:

1. A BIZ-to-FLG responsibility split stated by the assistant.
2. An unlabelled restatement of the proposed authorization rule.

`review --autonomous` rejected both as `unattributed`. It wrote no formal
decision. `merge --yes` completed routine progress maintenance and closed the
patch without changing `DECISIONS.md` or `SNAPSHOT.md`.

| Check | Result |
| --- | --- |
| Raw conversation archived under `.flg/sessions/` | Pass |
| Candidate extraction occurred without user CLI interaction | Pass |
| Assistant-authored candidate entered formal ledger | No |
| Unattributed candidate entered formal ledger | No |
| `DECISIONS.md` hash unchanged | Pass |
| `SNAPSHOT.md` hash unchanged | Pass |
| Closed patch remained pending | No |
| `flg doctor --strict` | Pass: 33 formal decisions, 33 indexed, no errors |
| Context Pack loaded raw transcript by default | No |

The generated Context Pack was 10,233 characters, approximately 2,558 tokens,
with zero pending patches and five rendered confirmed decisions.

## What This Validates

Codex can follow the FlowGrid host protocol in a natural project conversation:
it can preserve raw evidence, perform candidate extraction and routine cleanup
in the background, and keep assistant reasoning out of formal project truth.

## Limits

This is a host-operated protocol run, not proof of a native Codex event hook or
automatic transcript export. The transcript was deliberately archived by the
host agent. It also does not validate promotion of an explicitly user-authored
decision; that behavior is covered by deterministic review tests and needs a
separate natural-session acceptance sample.
