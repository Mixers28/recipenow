# persistent-agent-workflow

A local, VS Code-first workflow that combines durable Markdown memory with a
Codex handoff extension so humans and agents share context and can route work to
the right agent.

## What this repo provides
- Long-term memory: `docs/PROJECT_CONTEXT.md`
- Working memory: `docs/NOW.md`
- Session log: `docs/SESSION_NOTES.md`
- Agent protocol: `docs/AGENT_SESSION_PROTOCOL.md`
- Design notes: `docs/PERSISTENT_AGENT_WORKFLOW.md`
- Codex handoff extension: `extensions/codex`

## Getting started
### 1) Clone
```bash
git clone https://github.com/YOUR_USERNAME/persistent-agent-workflow
cd persistent-agent-workflow
```

### 2) Fill in your project details
- Edit `docs/PROJECT_CONTEXT.md` and `docs/NOW.md`.
- Let your agent maintain the summary blocks.

### 3) Start a session
In VS Code: `Tasks: Run Task` -> `Start Session (Agent - Coder)` (or pick another role)

Or run directly:
```bash
# macOS/Linux
bash ./scripts/session-helper.sh --mode start --agent-role Coder --open-docs
```
```powershell
# Windows
pwsh ./scripts/session-helper.ps1 -Mode Start -AgentRole Coder -OpenDocs
```

### 4) Use the Codex handoff extension (optional)
- Build the extension from `extensions/codex`.
- Use the status bar to select the active agent, then run `Codex: Hand off task`.

### 5) End a session (writeback + commit/push)
In VS Code: `Tasks: Run Task` -> `End Session (Agent + Commit)`

Or run directly:
```bash
# macOS/Linux
bash ./scripts/session-helper.sh --mode end
```
```powershell
# Windows
pwsh ./scripts/session-helper.ps1 -Mode End
```

## Tooling
- VS Code tasks: `.vscode/tasks.json`
- Scripts:
  - `scripts/session-helper.sh` / `scripts/session-helper.ps1` (prints prompts, optionally opens docs)
  - `scripts/commit-session.sh` / `scripts/commit-session.ps1` (commit + push current branch)
- Extension:
  - `extensions/codex` (Codex handoff UI and chat participants)

## License
MIT

Notes:
- This repo merges the original memory kit with a Codex handoff extension.
- MCP terminology is deprecated; see `docs/PERSISTENT_AGENT_WORKFLOW.md`.
