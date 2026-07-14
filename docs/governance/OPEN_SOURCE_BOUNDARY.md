# FlowGrid Open-Source Boundary

## Core Principle

> FlowGrid's protocol and trusted local core stay open. Real human-AI
> collaboration learning assets, user data, and advanced product capabilities
> stay private.

---

## Public Core

The public repository permanently includes:

- **Local-first project ledger** — PROJECT.md, FRAMING.md, DECISIONS.md,
  SNAPSHOT.md, PROGRESS.md, and supporting files
- **Judgment status model** — confirmed, pending_review, assumption, rejected,
  superseded, needs_recheck
- **Context Pack protocol** — bounded agent startup context generation
- **Capture / Review / Merge pipeline** — the core closeout → review → merge loop
- **Evidence capability** — source tracing for reviewed decisions
- **Patch lifecycle** — supersede, discard, status-based filtering
- **Basic Agent Skill** — `skills/flowgrid-operator/SKILL.md`
- **Basic CLI** — all commands in `src/flg/`
- **Data import/export** — `flg import`, `flg export-handoff`
- **Synthetic tests and basic eval** — `tests/`, `evals/`
- **Onboarding** — `flg onboard` command and demo

The public version must remain independently installable and usable without
any private repository.

---

## Private Learning Assets

The following content is NOT published in the public repository by default:

- **Real project data** — actual conversation logs, session transcripts,
  decision logs from real engagements
- **User judgment language data** — real captures, judgment profiles,
  trigger-word corpora from real usage
- **Complete false-positive / false-negative records** — detailed error
  analysis tied to real sessions
- **Full adversarial eval sets** — high-difficulty test scenarios used for
  internal quality benchmarking
- **Advanced cognitive audit rules** — blindspot detection logic reserved
  for commercial versions
- **Industry templates** — sector-specific framing and constraint templates
- **Commercial implementation** — hosted/team features, pricing, market analysis
- **Unredacted human evaluation results**

Private assets are maintained in a separate location (`flowgrid-lab-export/`
or a private repository) and are NOT a runtime dependency of the public version.

---

## Boundary Enforcement

### .gitignore

The public `.gitignore` blocks accidental commits of:

- `.flg/sessions/`, `.flg/captures/`, `.flg/memory/`, `.flg/context/`,
  `.flg/exports/` — runtime project state
- `dogfood/private/`, `evals/private/`, `research/private/`, `private/` —
  designated private research zones
- `*_profile.local.yaml`, `*.private.yaml`, `*.private.json` — user-specific
  configuration
- `.env`, `*.pem`, `*.key`, `credentials.json`, `secrets.*` — credentials

### Contribution Rule

External contributions must use synthetic data only. See `CONTRIBUTING.md`.

### Trademark

The FlowGrid name and official branding are not automatically licensed with
the MIT code. See `TRADEMARK.md`.
