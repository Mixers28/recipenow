# Agent Session Protocol

Version: 1.0  
Owner: You

## Purpose
Define how a human and a local code agent coordinate using this repo's memory files so every session starts with shared context and ends with consistent writeback.

## Memory Files
- Long-term memory (LTM): `docs/PROJECT_CONTEXT.md`
- Working memory (WM): `docs/NOW.md`
- Session memory (SM): `docs/SESSION_NOTES.md`
- Design notes: `docs/MCP_LOCAL_DESIGN.md`

## Canonical Artifact
- `docs/SPEC.md` is the source of truth for implementation.
- Architect creates/updates it; everyone else must follow it.

## Handoff Loop
Architect -> Coder -> Reviewer <-> Coder (until pass) -> QA -> Polish

## Hard Anti-Drift Rules
Every handoff prompt must include:
- Invariants (non-negotiables)
- `docs/SPEC.md` (full or excerpt)
- Only relevant code snippets/diff

Reviewer rule:
- Reviewer must not redesign; only evaluate against `docs/SPEC.md`, best practices, and current docs (Context7).

## Start Session (Context Hydration)
Preferred: VS Code task `Start Session (Agent - Coder)` (or pick another role; see `.vscode/tasks.json`).

CLI equivalent:
```bash
handoffkit session start --agent-role Coder --open-docs
```

Agent instructions:
1. Read (in order): `docs/PROJECT_CONTEXT.md`, `docs/NOW.md`, `docs/SESSION_NOTES.md` (recent).
2. Summarize context in 3-6 bullets.
3. Wait for the next instruction.

## End Session (Writeback + Checkpoint)
Preferred: VS Code task `End Session (Agent + Commit)` (see `.vscode/tasks.json`).

CLI equivalent:
```bash
handoffkit session end --commit
```

Human steps:
1. Paste the printed `SESSION END` block into the agent.
2. Add 2-5 bullets describing what happened this session (what you changed, why).
3. Let the agent update the memory files in the workspace.
4. Return to the terminal and press Enter to let `handoffkit` commit and push.

Writeback expectations:
- `docs/PROJECT_CONTEXT.md`: update only when higher-level decisions/constraints changed; refresh summary blocks if present.
- `docs/NOW.md`: update immediate next steps and current focus; refresh summary blocks if present.
- `docs/SESSION_NOTES.md`: append a new dated entry (do not overwrite previous entries).
