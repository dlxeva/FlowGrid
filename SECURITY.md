# Security Policy

## Reporting a Vulnerability

Do NOT file public issues for security vulnerabilities.

Report security issues privately. If you have access to a private reporting
channel (GitHub Security Advisories, direct contact), use that.

## What NOT to put in public issues

- Project ledgers (`DECISIONS.md`, `SNAPSHOT.md`, `PROGRESS.md`, etc.) from
  real projects
- Conversation logs or session transcripts
- Client names, project names, or business materials
- API keys, tokens, passwords, or any credentials

## `.flg/` directory sensitivity

The `.flg/` directory in a FlowGrid project may contain sensitive project
state, including:

- `.flg/sessions/` — raw conversation transcripts
- `.flg/captures/` — real-time judgment captures
- `.flg/state.json` — project metadata
- `.flg/context/` — generated context packs

Never commit `.flg/` contents to a public repository. This repository's
`.gitignore` blocks these paths. `flg init` also creates or extends the target
project's `.gitignore` with `.flg/` and common local credential rules. Verify
the result before committing an existing project with unusual ignore rules.

## Remote LLM extraction

`flg closeout` does not automatically send transcripts to a configured remote
LLM provider. A host must pass both `--llm <provider>` and
`--allow-remote-llm` for that command. Review the provider's terms before
using it with confidential project material.
