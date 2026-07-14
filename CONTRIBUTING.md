# Contributing to FlowGrid

## Quick Rules

1. **Use synthetic data only.** Do not include real project materials, real
   conversation logs, real client names, or real decision content in
   contributions. All test fixtures and examples must use fictional data.

2. **Tests must pass.** Run `pytest -q` before submitting. New features must
   include tests.

3. **Submitted code is licensed under the repository's MIT license.** By
   contributing, you agree your contributions are licensed under the same terms.

4. **Large architectural changes should start with an issue.** Open an issue
   describing the problem and proposed approach before writing significant
   code. This avoids wasted effort on directions that may not align.

## What belongs in the public repository

- CLI source code (`src/flg/`)
- Tests with synthetic fixtures (`tests/`)
- Protocol and product design docs (`docs/`)
- Synthetic eval scenarios (`evals/`)
- The standard Agent Skill (`skills/flowgrid-operator/`)

## What does NOT belong

- Real project data (any kind)
- Real user judgment profiles or trigger-word corpora
- Detailed commercial strategy or pricing
- Credentials or API keys

If you're unsure whether something is appropriate for a public contribution,
open an issue and ask first.

## Development setup

```bash
pip install -e .
pytest -q
```

## Running the smoke test

```bash
python scripts/smoke_test.py
```
