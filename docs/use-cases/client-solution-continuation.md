# Client Solution Continuation

This is a synthetic example. It shows the kind of long-running, judgment-heavy
work FlowGrid is designed to support without exposing a real client or project.

## Situation

An independent solution owner is preparing an operations-improvement proposal
for Client A. After two working sessions, a new client meeting changes the
project:

- the original problem diagnosis was based on secondary information;
- a proposed automation path is technically possible, but not the immediate
  bottleneck;
- the next deliverable must become a discovery plan, not a full implementation
  proposal.

Without durable project state, a new agent sees an old deck outline and may
continue refining the wrong proposal.

## What FlowGrid keeps separate

| Project signal | FLG state | Why |
|---|---|---|
| The owner wants to explore automation | `assumption` / `pending_review` | It is an intention, not client approval. |
| The meeting disproves the original bottleneck | reviewed evidence | Future work must not rely on the old diagnosis. |
| Reframe the next deliverable as discovery | `confirmed` decision | It changes the project's active direction. |
| The original implementation-first outline | `superseded` direction | Keep the rationale so it is not silently revived. |

## Continuation Result

The next agent starts with a bounded Context Pack instead of the full chat
history. It can see:

```text
Current objective: validate the real workflow before proposing implementation.

Confirmed direction: prepare a discovery plan, not an implementation-first deck.

Do not revive: the original automation-first proposal; it relied on an
unverified bottleneck assumption.

Pending: client confirmation of access to first-party workflow samples.

Next action: draft the discovery plan and list the evidence needed to reopen
the implementation proposal.
```

The value is not that FlowGrid decides for the owner. It preserves the reason
the project changed, the boundary of the new direction, and what must be true
before the old direction can return.

## Run the Included Demo

For a small CLI walkthrough, use the synthetic proposal project:

```bash
cd examples/demo-proposal-project
flg init "Client A solution proposal" --type proposal --client "Client A"
flg frame
flg closeout --transcript demo_transcript.md
```

The host-integrated path is recommended for real work. Install the
`flowgrid-operator` skill with `flg onboard`, then continue in your usual AI
host using natural language.
