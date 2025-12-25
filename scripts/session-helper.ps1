param(
    [ValidateSet("Start", "End")]
    [string]$Mode = "Start",

    [ValidateSet("Architect", "Coder", "Reviewer", "QA")]
    [string]$AgentRole = "Coder",

    [switch]$OpenDocs
)

$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..")
$agentRoleSlug = $AgentRole.ToLowerInvariant()
$agentRoleFile = ".github/agents/$agentRoleSlug.agent.md"

Write-Host "Local MCP – $Mode Session" -ForegroundColor Cyan
Write-Host ""

# Show current Git branch
try {
    Push-Location $projectRoot
    $branch = git rev-parse --abbrev-ref HEAD 2>$null
    if ($branch) {
        Write-Host "Current Git branch: $branch" -ForegroundColor DarkCyan
        Write-Host ""
    }
} finally {
    Pop-Location
}

if ($Mode -eq "Start") {
    Write-Host "SESSION START" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Paste the block below into your local code agent (e.g. VS Code Code Agent)." -ForegroundColor Green
    Write-Host ""

@"
SESSION START – PROJECT CONTEXT

You are a local code assistant working on this project.

Before doing anything:

0. Assume the role described here:
   - $agentRoleFile

1. Read these files in this order:
   - docs/PROJECT_CONTEXT.md
   - docs/NOW.md
   - docs/SESSION_NOTES.md

2. Summarise the current context in 3–6 bullet points so we both know you understood it.

3. Then wait for my next instruction.
"@ | Write-Host

    if ($OpenDocs) {
        Write-Host ""
        if (Get-Command code -ErrorAction SilentlyContinue) {
            Write-Host "Opening docs in VS Code..." -ForegroundColor Green
            Push-Location $projectRoot
            code $agentRoleFile "docs/PROJECT_CONTEXT.md" "docs/NOW.md" "docs/SESSION_NOTES.md" "docs/AGENT_SESSION_PROTOCOL.md"
            Pop-Location
        } else {
            Write-Host "VS Code 'code' CLI not found; open docs manually." -ForegroundColor Yellow
        }
    }
}
elseif ($Mode -eq "End") {
    Write-Host "SESSION END" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1) Copy the block below into your local code agent." -ForegroundColor Green
    Write-Host "2) Let it update docs (SESSION_NOTES, NOW, summaries)." -ForegroundColor Green
    Write-Host "3) Come back here and press Enter to commit & push." -ForegroundColor Green
    Write-Host ""

@"
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
"@ | Write-Host

    Write-Host ""
    Read-Host "After the agent has updated the docs and you're happy with the changes, press Enter here to commit & push"

    $commitScript = Join-Path $scriptDir "commit-session.ps1"
    if (Test-Path $commitScript) {
        & $commitScript
    } else {
        Write-Host "commit-session.ps1 not found at $commitScript" -ForegroundColor Red
    }
}
