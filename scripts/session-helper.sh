#!/usr/bin/env bash
set -euo pipefail

mode="start"
agent_role="Coder"
open_docs="false"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/session-helper.sh --mode start|end [--agent-role Architect|Coder|Reviewer|QA] [--open-docs]

Examples:
  ./scripts/session-helper.sh --mode start --agent-role Coder --open-docs
  ./scripts/session-helper.sh --mode end
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      mode="${2:-}"; shift 2 ;;
    --agent-role)
      agent_role="${2:-}"; shift 2 ;;
    --open-docs)
      open_docs="true"; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage; exit 2 ;;
  esac
done

case "$mode" in
  start|end) ;;
  *)
    echo "Invalid --mode: $mode" >&2
    usage
    exit 2
    ;;
esac

case "$agent_role" in
  Architect|Coder|Reviewer|QA) ;;
  *)
    echo "Invalid --agent-role: $agent_role" >&2
    usage
    exit 2
    ;;
esac

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/.." && pwd)"
agent_role_slug="$(printf '%s' "$agent_role" | tr '[:upper:]' '[:lower:]')"
agent_role_file=".github/agents/${agent_role_slug}.agent.md"

echo "Local MCP – ${mode^} Session"
echo

if command -v git >/dev/null 2>&1; then
  if branch="$(git -C "$project_root" rev-parse --abbrev-ref HEAD 2>/dev/null)"; then
    if [[ -n "$branch" ]]; then
      echo "Current Git branch: $branch"
      echo
    fi
  fi
fi

if [[ "$mode" == "start" ]]; then
  echo "SESSION START"
  echo
  echo "Paste the block below into your local code agent (e.g. VS Code Code Agent)."
  echo
  cat <<EOF
SESSION START – PROJECT CONTEXT

You are a local code assistant working on this project.

Before doing anything:

0. Assume the role described here:
   - $agent_role_file

1. Read these files in this order:
   - docs/PROJECT_CONTEXT.md
   - docs/NOW.md
   - docs/SESSION_NOTES.md

2. Summarise the current context in 3–6 bullet points so we both know you understood it.

3. Then wait for my next instruction.
EOF

  if [[ "$open_docs" == "true" ]]; then
    echo
    if command -v code >/dev/null 2>&1; then
      echo "Opening docs in VS Code..."
      (
        cd "$project_root"
        code "$agent_role_file" "docs/PROJECT_CONTEXT.md" "docs/NOW.md" "docs/SESSION_NOTES.md" "docs/AGENT_SESSION_PROTOCOL.md"
      )
    else
      echo "VS Code 'code' CLI not found; open docs manually."
    fi
  fi
  exit 0
fi

echo "SESSION END"
echo
echo "1) Copy the block below into your local code agent."
echo "2) Let it update docs (SESSION_NOTES, NOW, summaries)."
echo "3) Come back here and press Enter to commit & push."
echo

cat <<'EOF'
SESSION END – PROJECT CONTEXT

You are a local code assistant working on this project.

1. Read these again to refresh context:
   - docs/PROJECT_CONTEXT.md
   - docs/NOW.md
   - docs/SESSION_NOTES.md

2. Based on what we did this session (my notes below) and the current repo state,
   UPDATE THESE FILES DIRECTLY in the workspace:

   - docs/PROJECT_CONTEXT.md
     *Only if any high-level design / tech decisions changed.*
     *If it has a SUMMARY block between SUMMARY_START and SUMMARY_END, update that summary.*

   - docs/NOW.md
     Update to reflect the next immediate focus / short-term tasks.
     Also refresh its SUMMARY block if present.

   - docs/SESSION_NOTES.md
     Append a new dated session entry (do not overwrite previous ones)
     with:
       - Participants
       - Branch name
       - Summary of work
       - Files touched
       - Decisions made

3. When you are done updating the files, reply with:
   - 3–6 bullet points summarising the session
   - A list of the files you modified

Here is my brief description of what we did this session:
[WRITE 2–5 BULLET POINTS HERE BEFORE SENDING TO THE AGENT]
EOF

echo
read -r -p "After the agent has updated the docs and you're happy with the changes, press Enter here to commit & push" _

commit_script="$script_dir/commit-session.sh"
if [[ -f "$commit_script" ]]; then
  "$commit_script"
else
  echo "commit-session.sh not found at $commit_script" >&2
  exit 1
fi
