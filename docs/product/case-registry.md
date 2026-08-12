# FlowGrid Case Registry

FlowGrid already has real-project and repeated dogfood evidence. The missing
piece was not another anecdote; it was a durable way to distinguish what each
case proves from what it does not prove.

The machine-readable source is [`evals/case-registry.json`](../../evals/case-registry.json).
Every entry must include:

- a stable case ID and evidence kind;
- the number and redacted identity of projects involved;
- a repository-local source and optional locator;
- objective or operational metrics;
- one bounded supported claim;
- one explicit limitation.

## Evidence kinds

- `real_project_controlled_eval`: sealed comparison using state from a real
  project. It can support continuation claims, not adoption claims.
- `customer_field_use`: work performed against a real customer situation. It
  can expose workflow defects without proving customer outcomes.
- `cross_project_dogfood`: the same failure pattern observed in multiple
  owner-operated projects.
- `host_acceptance`: a concrete host workflow with recorded pass/fail checks.
- `project_orchestration_dogfood`: use of FlowGrid inside a live project master.

`external_adoption` is intentionally absent until an independent user operates
the product with evidence of onboarding, continued use, or outcome value.

## Evaluation rule

Do not turn one reviewer score into a product fact. Prefer, in order:

1. hard boundary failures and deterministic pass/fail checks;
2. input size, latency, correction count, command burden, and completion state;
3. blinded pairwise semantic review with disagreement preserved;
4. qualitative interpretation, labelled as interpretation.

The registry test verifies required fields, unique IDs, positive case counts,
known evidence kinds, and repository-local source existence.
