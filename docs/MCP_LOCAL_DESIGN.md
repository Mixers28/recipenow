# Local MCP Design – Files as Memory

Version: 0.1  
Owner: You  

---

## 0. Purpose

This document explains how this project uses **plain files + Git** as a structured memory system, similar in spirit to **Model Context Protocol (MCP)**.

Goals:

- Give AI coding agents a persistent, version-controlled memory.
- Keep the memory fully local, inspectable, and editor-friendly.
- Make it easy to plug this into any project without extra services.

No external DB, no server required. Everything lives in this repo.

---

## 1. Memory Layers

We treat the `/docs` folder as a set of memory layers:

- **Long-Term Memory (LTM)**
  - `PROJECT_CONTEXT.md`
  - High-level design, tech stack, constraints, big decisions.

- **Working Memory (WM)**
  - `NOW.md`
  - Current focus, active branch, immediate tasks and deliverables.

- **Session Memory (SM)**
  - `SESSION_NOTES.md`
  - Append-only log of what happened in each session.

- **Index / Meta Memory (IM)** (optional / future)
  - Could include a JSON index or embeddings cache if you extend this kit.

Each layer has a clear job and a small number of files.

---

## 2. Summary Blocks

Some docs include a **Summary Block** at the top, between:

```markdown
<!-- SUMMARY_START -->
...summary content...
<!-- SUMMARY_END -->
Purpose
Give humans and agents a fast, compressed view of the file.

Avoid re-reading huge docs on every request.

Keep token usage predictable.

Rules
The Summary Block is owned by the local code agent.

It should be kept to ~3–8 bullets.

Humans can edit it in emergencies, but the normal flow is:

Agent reads full doc.

Agent rewrites summary in its own words.

Rest of the doc remains as-is.

At minimum, this kit expects Summary Blocks in:

PROJECT_CONTEXT.md

NOW.md

You can add more if needed.

3. Session Events (Start / End)
This system defines two key events:

3.1 Start Session – “Context Hydration”
Triggered via the VS Code task:

Start Session (Agent) → scripts/session-helper.ps1 -Mode Start -OpenDocs

Flow:

Script prints a SESSION START prompt.

You paste that prompt into your local code agent (e.g. VS Code Code Agent).

The agent:

Reads docs/PROJECT_CONTEXT.md

Reads docs/NOW.md

Reads docs/SESSION_NOTES.md (recent entries)

Summarises the current context in 3–6 bullets.

The agent then waits for your instructions.

This is similar to an MCP client calling out to a “memory” tool to hydrate context before work.

3.2 End Session – “Memory Writeback + Checkpoint”
Triggered via the VS Code task:

End Session (Agent + Commit) → scripts/session-helper.ps1 -Mode End

Flow:

Script prints a SESSION END prompt.

You briefly describe what you did this session (2–5 bullets).

You paste the prompt + your notes into the code agent.

The agent:

Appends a new entry to docs/SESSION_NOTES.md.

Updates docs/NOW.md to reflect the new “current focus”.

Optionally refreshes Summary Blocks in PROJECT_CONTEXT.md and NOW.md.

When you’re happy with the changes, you return to the terminal and press Enter.

scripts/commit-session.ps1:

Stages docs + other changes.

Commits with a timestamped message.

Pushes the current branch.

This is functionally similar to an MCP server updating external state and then persisting a checkpoint.

4. Agent Roles
Local Code Agent (e.g. VS Code Code Agent)
Can read and write files in this repo.

Responsible for:

Maintaining Summary Blocks.

Keeping NOW.md honest.

Appending consistent entries to SESSION_NOTES.md.

External Assistant (e.g. ChatGPT / Nova)
Cannot access files directly.

Works on pasted snippets or uploaded files.

Can:

Propose updates to docs.

Help design architecture / refactors.

Suggest how to compress or reorganise memory.

Human applies changes locally and uses the normal start/end flow.

5. Scalability & Extensions
This kit is intentionally minimal, but you can extend it:

Per-branch session notes

SESSION_NOTES_main.md, SESSION_NOTES_feature-x.md, etc.

Context index

A small context_index.json listing files, tags, and summaries.

Embeddings

A script that generates embeddings for key docs and stores them in a local file or DB.

A simple CLI that lets you search context by meaning.

Try to keep the core rules:

Human-readable first.

Git-versioned.

Editor-native.

Easy for agents to follow.

6. Design Philosophy
This kit is intentionally:

Dumb on purpose – no hidden state, no background daemon.

Explicit – every start/end session is a conscious act.

Portable – you can drop /docs + /scripts + /.vscode into almost any repo.

It doesn’t replace “real” MCP server implementations; it complements them by giving you a lightweight, transparent memory layer you fully control.