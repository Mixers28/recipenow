# Agent Session Protocol

Version: 1.1
Owner: You

## Purpose
Define how a human and a local code agent coordinate using this repo's memory
files so every session starts with shared context and ends with consistent
writeback. The Codex handoff extension is used for explicit agent selection.

## Memory Files
- Long-term memory (LTM): `docs/PROJECT_CONTEXT.md`
- Working memory (WM): `docs/NOW.md`
- Session memory (SM): `docs/SESSION_NOTES.md`
- Design notes: `docs/PERSISTENT_AGENT_WORKFLOW.md`

## Start Session (Context Hydration)
Preferred: VS Code task `Start Session (Agent - Coder)` (or pick another role; see `.vscode/tasks.json`).

CLI equivalent:
```bash
# macOS/Linux
bash ./scripts/session-helper.sh --mode start --agent-role Coder --open-docs
```
```powershell
# Windows
pwsh ./scripts/session-helper.ps1 -Mode Start -AgentRole Coder -OpenDocs
```

Agent instructions:
1. Read (in order): `docs/PROJECT_CONTEXT.md`, `docs/NOW.md`, `docs/SESSION_NOTES.md` (recent).
2. Summarize context in 3-6 bullets.
3. If using the extension, select the active agent in the status bar.
4. Wait for the next instruction.

## End Session (Writeback + Checkpoint)
Preferred: VS Code task `End Session (Agent + Commit)` (see `.vscode/tasks.json`).

CLI equivalent:
```bash
# macOS/Linux
bash ./scripts/session-helper.sh --mode end
```
```powershell
# Windows
pwsh ./scripts/session-helper.ps1 -Mode End
```

Human steps:
1. Paste the printed `SESSION END` block into the agent.
2. Add 2-5 bullets describing what happened this session (what you changed, why).
3. Let the agent update the memory files in the workspace.
4. Return to the terminal and press Enter to run `scripts/commit-session.sh` / `scripts/commit-session.ps1`.

Writeback expectations:
- `docs/PROJECT_CONTEXT.md`: update only when higher-level decisions/constraints changed; refresh summary blocks if present.
- `docs/NOW.md`: update immediate next steps and current focus; refresh summary blocks if present.
- `docs/SESSION_NOTES.md`: append a new dated entry (do not overwrite previous entries).
