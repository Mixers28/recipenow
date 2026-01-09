RecipeNow/
  apps/
    web/                 # Next.js UI
    api/                 # FastAPI app
    worker/              # OCR/parse jobs
  packages/
    schema/              # Pydantic/JSON schema + TS types
    ocr/                 # OCR adapters + preprocess
    parser/              # structuring + provenance writer
    matcher/             # pantry matching logic
  infra/
    docker-compose.yml
    migrations/
  docs/
    SPEC.md
    PROJECT_CONTEXT.md
    NOW.md
    SESSION_NOTES.md
    AGENT_SESSION_PROTOCOL.md
    MCP_LOCAL_DESIGN.md
    PERSISTENT_AGENT_WORKFLOW.md
    UI_NOTES.md
    IMPLEMENTATION_PLAN.md
