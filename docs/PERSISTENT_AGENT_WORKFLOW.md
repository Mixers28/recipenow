# Persistent Agent Workflow Design

This document is the source of truth for the persistent agent workflow.

Version: 1.0
Owner: You

## Purpose
This repo combines a local memory kit with a Codex VS Code extension to enable a
persistent agent workflow. The goal is a predictable handoff loop where humans
and agents share the same context, select the right agent for the task, and
write back durable memory in Markdown.

## Core Ideas
- Keep memory in plain Markdown tracked by Git.
- Use a VS Code extension for fast, explicit agent selection and handoff.
- Keep everything local, stable-API only, and Windows-friendly.

## System Components
### Memory Files
- Long-term memory (LTM): `docs/PROJECT_CONTEXT.md`
- Working memory (WM): `docs/NOW.md`
- Session memory (SM): `docs/SESSION_NOTES.md`

### Session Protocol
- Start session: read LTM -> WM -> recent SM, then summarize context.
- End session: append session notes and update LTM/WM summaries.

### Codex Extension
- Status bar shows the active agent and lets you change it.
- Handoff view lists agents for quick selection.
- Commands for direct handoff and for selecting the active agent.
- Chat participants for Architect, Coder, Reviewer, and QA.

## Primary Workflows
1) Select active agent in the status bar or handoff view.
2) Use `Codex: Hand off task` or click a handoff target to open chat.
3) Provide instructions to the agent, using selection or file context when helpful.
4) At session end, write back to memory docs and commit if needed.

## Constraints
- VS Code stable APIs only (no proposed APIs).
- Windows support is required (path handling, scripts, and tasks).
- No external services or network dependencies.

## Testing
- Command wiring check (`extensions/codex/scripts/verify-command-wiring.js`).
- Manual smoke tests in VS Code for handoff and status bar selection.
