# BIZ Meeting Handoff

BIZ analyzes meetings. FlowGrid governs project-state changes. A BIZ handoff
keeps those responsibilities separate: BIZ supplies role-aware evidence, and
FlowGrid decides whether a judgment may enter the durable ledger.

## Contract

`flg capture import-biz --input handoff.json` accepts this JSON shape:

```json
{
  "schema_version": "1.0",
  "source": {
    "ref": "06-retro/2026-07-21-meeting.md"
  },
  "judgments": [
    {
      "claim": "Use the revised proposal structure.",
      "rationale": "The project owner explicitly requested it.",
      "status": "Confirmed",
      "source_anchor": "Meeting 1, project owner, 24:10",
      "actor": {
        "role": "project_owner",
        "role_basis": "explicit_source_metadata"
      },
      "alternatives": ["Keep the current structure"],
      "risks": "Client needs still require validation."
    }
  ]
}
```

Required per judgment: `claim`, `rationale`, and `source_anchor`.

## Promotion Rule

A BIZ item is imported as `confirmed` only when all conditions hold:

1. BIZ marks the item `Confirmed`.
2. `actor.role` is `project_owner`, `authorized_client`, or
   `authorized_representative`.
3. `actor.role_basis` is exactly `explicit_source_metadata`.

Every other item remains an inferred, pending capture. This includes a
plausible meeting conclusion with an anonymous speaker, a role inferred from
conversation content, and a normal participant proposal.

The command never infers authority from speaker number, tone, subject matter,
or a BIZ narrative. `flg capture review --auto-confirm` can then process only
the explicitly authorized captures; all others remain available for natural
language follow-up or later review.

## Source Ownership

The handoff preserves the original meeting reference, evidence anchor, BIZ
status, role, and role basis in the capture front matter. BIZ owns transcript
interpretation and participant mapping. FlowGrid owns candidate status,
promotion, ledger inheritance, and audit.
