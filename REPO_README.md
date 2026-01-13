# RecipeNow

RecipeNow is a self-hosted, privacy-first recipe pipeline that turns uploaded
recipe media (photos, screenshots, PDFs) into verified, provenance-backed
recipes. Every extracted field is traceable to source pixels, and the split-view
review UI makes correction and verification fast.

## Current Status

- Sprints 0-5 complete: scaffolding, schema, OCR pipeline, CRUD API, review UI
- Sprint 6 in progress: pantry CRUD, matching, and shopping list workflows

See `docs/NOW.md` for the live sprint checklist and `docs/SPEC.md` for the
canonical V1 blueprint.

## Stack (Pinned Versions)

- API: FastAPI 0.128.0, SQLAlchemy 2.0.25, psycopg 3.3.2
- Worker: ARQ 0.26.3 + Redis 7
- OCR: PaddleOCR 3.3.2
- Web: Next.js 16.1.0, React 19
- DB: Postgres 16

## Repo Layout

```
apps/
  api/        FastAPI backend
  web/        Next.js frontend
  worker/     OCR/parse/normalize jobs
packages/
  schema/     Pydantic + TS types
  ocr/        OCR adapters + preprocess
  parser/     Structured parsing + provenance
  matcher/    Pantry matching logic
infra/
  docker-compose.yml
  migrations/
docs/
  SPEC.md
  NOW.md
  SESSION_NOTES.md
```

## Quickstart (Docker)

```bash
docker compose -f infra/docker-compose.yml up --build
```

Services:
- API: http://localhost:8000
- Web: http://localhost:3000
- MinIO console (optional): http://localhost:9001

## Local Dev (Without Docker)

API:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
DATABASE_URL=postgresql+psycopg://recipenow:recipenow@localhost:5432/recipenow \
REDIS_URL=redis://localhost:6379 \
uvicorn apps.api.main:app --reload
```

Worker:
```bash
source .venv/bin/activate
pip install -r apps/worker/requirements.txt
DATABASE_URL=postgresql+psycopg://recipenow:recipenow@localhost:5432/recipenow \
REDIS_URL=redis://localhost:6379 \
arq apps.worker.worker.WorkerSettings
```

Web:
```bash
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Core Principles

- Source-of-truth only: no inferred values without OCR evidence or user edits
- Provenance per field: every extracted field has SourceSpans or is marked missing
- Verification gating: title + >= 1 ingredient + >= 1 step required before verify
- Review-first workflow: split-view UI is the primary workflow, not a power user path

## Documentation

- `docs/SPEC.md`: canonical V1 blueprint and API contract
- `docs/IMPLEMENTATION_PLAN.md`: build plan + pinned versions
- `docs/PROJECT_CONTEXT.md`: long-term project context
