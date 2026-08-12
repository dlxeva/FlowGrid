# Decision Relations v0

## Goal

FlowGrid already preserves each formal decision, its rationale, rejected paths, and evidence provenance. Decision Relations v0 adds one missing layer: explicit links between formal judgments.

The formal ledger remains authoritative. Relations are parsed directly from `DECISIONS.md`; FLG does not introduce a graph database or a second source of truth.

## Supported relations

| Relation | Meaning |
|---|---|
| `supersedes` | The new decision replaces an earlier decision. |
| `supports` | The new decision reinforces an earlier decision. |
| `contradicts` | The new decision challenges or conflicts with an earlier decision. |
| `depends_on` | The new decision relies on an earlier decision remaining valid. |

Relations are directional. For example, `D-006 supersedes D-002` does not rewrite or delete `D-002`. The historical decision remains inspectable.

## Recording relations

`flg decision add` accepts comma-separated existing decision IDs:

```bash
flg decision add \
  --decision "Ship the manifest-first context mode" \
  --rationale "It preserves continuity under bounded context budgets" \
  --supersedes D-004 \
  --supports D-003 \
  --depends-on D-001,D-002
```

FLG rejects malformed IDs and targets that do not exist in the formal ledger.

The command writes a human-editable block:

```markdown
### Decision Relations
- **Supersedes:** D-004
- **Supports:** D-003
- **Contradicts:** none
- **Depends On:** D-001, D-002
```

Chinese ledgers use the equivalent labels:

```markdown
### 决策关系
- **替代决策:** D-004
- **支持决策:** D-003
- **冲突决策:** none
- **依赖决策:** D-001, D-002
```

## Querying relations

`flg trace D-006` shows both directions:

- outgoing edges declared by `D-006`;
- incoming edges from later decisions that reference `D-006`.

This keeps provenance episodes and decision relations in one inspection path.

## Integrity checks

`flg doctor` reports:

- relation targets missing from `DECISIONS.md`;
- self-referential edges.

`flg doctor --strict` exits with code 1 when either condition exists.

## Deliberate boundaries

Decision Relations v0 does not:

- infer relations with an LLM;
- use embedding similarity;
- automatically change a referenced decision's status;
- delete superseded decisions;
- require Neo4j, RDF, or another graph runtime.

This is a deterministic projection over the human-readable ledger. A richer graph export can be added later without changing the source-of-truth contract.
