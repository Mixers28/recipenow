# Project Context - Long-Term Memory (LTM)

> High-level design, tech decisions, constraints for this project.
> This is the source of truth for agents and humans.

<!-- SUMMARY_START -->
**Summary (auto-maintained by Agent):**
- This repo defines a persistent agent workflow that merges local Markdown memory with a Codex handoff extension.
- Agents use explicit handoff selection in VS Code, backed by durable memory files and session rituals.
- Stable VS Code APIs only, Windows support required, and no external services.
<!-- SUMMARY_END -->

---

## 1. Project Overview

- Name: persistent-agent-workflow (working title)
- Owner: TBD (template maintainer)
- Purpose: Provide a local, VS Code-first workflow for persistent agent handoffs and shared memory.
- Primary Stack: Markdown docs, VS Code extension, helper scripts (PowerShell + bash), Git.
- Target Platforms: VS Code stable on Windows, macOS, and Linux.

---

## 2. Core Design Pillars

- Keep memory transparent and versioned in Markdown.
- Make handoffs explicit with a UI for selecting the active agent.
- Keep the workflow local and editor-native.
- Stay stable-API only and Windows-friendly.

---

## 3. Technical Decisions & Constraints

- Languages: TypeScript (extension), Markdown (docs), PowerShell/bash (scripts).
- VS Code: stable APIs only, no proposed API usage.
- Storage: Git history plus explicit memory files in `docs/`.
- Networking: no external services required.
- Cross-platform: scripts and path handling must support Windows.

---

## 4. Architecture Snapshot

- Memory files:
  - LTM: `docs/PROJECT_CONTEXT.md`
  - WM: `docs/NOW.md`
  - SM: `docs/SESSION_NOTES.md`
- Session protocol: `docs/AGENT_SESSION_PROTOCOL.md`
- Extension UI:
  - Status bar active agent selector
  - Handoff view (tree)
  - Command palette handoff commands
- Test harness: `extensions/codex/scripts/verify-command-wiring.js`

---

## 5. Links & Related Docs

- Design doc: `docs/PERSISTENT_AGENT_WORKFLOW.md`
- Protocol: `docs/AGENT_SESSION_PROTOCOL.md`
- Repo map: `docs/Repo_Structure.md`

---

## 6. Change Log (High-Level Decisions)

Use this section for big decisions only:
- YYYY-MM-DD - Adopted a persistent agent workflow that merges local memory docs with the Codex handoff extension.
