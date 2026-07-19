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
`.gitignore` blocks these paths. FlowGrid projects initialized elsewhere do
not currently receive a generated `.gitignore`; add equivalent rules before
committing project files.
