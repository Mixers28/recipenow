# NOW - Working Memory (WM)

> This file captures the current focus / sprint.
> It should always describe what we're doing right now.

<!-- SUMMARY_START -->
**Current Focus (auto-maintained by Agent):**
- **Sprint 0 Complete:** Scaffolding, router wiring, Next.js App Router, Context7 library versions locked.
- **Sprint 1 Complete:** Pydantic/TS/SQLAlchemy models with UUIDs + user_id, Postgres migration, CRUD tests.
- **Sprint 2 Complete:** Ingest job + file upload + OCR pipeline wiring.
- **Sprint 3 Complete:** Deterministic parsing (RecipeParser) + structure job + normalize job.
- **Sprint 4 Complete:** Repository layer + CRUD endpoints for recipes/spans/pantry with user isolation.
- **Sprint 5 Complete:** Review UI (split-view in Next.js with image viewer + field highlights + badges).
- **Sprint 6 In Progress:** Pantry & Match (pantry CRUD, matching logic, shopping list).
- **Active Issue:** Railway OCR pipeline failing; fields remain missing due to PaddleOCR init errors.
- **Context:** Multi-user JWT auth, Railway + Vercel deployment, **full V1 UI and backend complete**.
<!-- SUMMARY_END -->

---

## Current Objective

Execute RecipeNow V1 implementation per SPEC.md: 6 sprints covering scaffolding, schema, OCR pipeline, CRUD, review UI, and pantry matching. All code decisions must use Context7 library resolution.

---

## Active Branch

- `main`

---

## What We Are Working On Right Now

### Sprint 2-3: OCR Enhancement + LLM Vision Fallback Implementation In Progress

**Status:** Implementation underway. Foundational code changes complete, integration in progress.

#### Completed:
- ✅ SPEC.md: Two-stage OCR pipeline integrated as canonical specification.
- ✅ SourceSpan model: `source_method: enum("ocr", "llm-vision")` field added.
- ✅ OCRService: `_detect_and_correct_rotation()` method implemented (Tesseract voting + ImageMagick).
- ✅ OCRService: `extract_text()` method updated with rotation detection integration.
- ✅ Database migration: 002_add_source_method.sql created (adds source_method column with indexes).
- ✅ LLMVisionService: Complete service with Ollama + LLaVA support (offline-first + cloud fallback).
- ✅ Job implementations: Ingest, Structure, Normalize jobs with LLM fallback logic.
- ✅ Requirements: Updated with httpx, anthropic, openai dependencies.

#### In Progress:
- 🔄 Testing rotation detection end-to-end with test images.
- 🔄 Testing LLM vision extraction with Ollama + LLaVA-7B.
- 🔄 Verify Structure Job LLM fallback trigger logic.
- 🔄 Database schema validation (migration application).

#### Next Steps:
- Test OCR with rotated recipe card images.
- Test LLM fallback when OCR yields sparse results.
- Implement review UI source badges.
- Sprint 4: Quality checks and normalization.

- Sprint 4-5: CRUD + UI with source badges.
- Sprint 6: Pantry & Match (unchanged).

### Sprint 6 – Pantry & Match

- [ ] **Sprint 6.1:** Implement GET /pantry endpoint with pagination and user isolation.
- [ ] **Sprint 6.2:** Implement POST /pantry/items endpoint for creating pantry items.
- [ ] **Sprint 6.3:** Implement PATCH /pantry/items/{id} and DELETE /pantry/items/{id} endpoints.
- [ ] **Sprint 6.4:** Build matching logic: score recipes against pantry items (name_norm matching).
- [ ] **Sprint 6.5:** Implement POST /match endpoint that returns match % per recipe.
- [ ] **Sprint 6.6:** Create shopping list generation from match results.
- [ ] **Sprint 6.7:** Build Pantry UI page with CRUD operations and "What Can I Cook?" matching.
- [ ] **Sprint 6.8:** Create Match Results page showing recipe scores and missing ingredients.

---

## Upcoming Sprints (After Sprint 2)

- **Sprint 3:** Structure & Normalize (parse OCRLines → Recipe + SourceSpans + FieldStatus).
- **Sprint 4:** CRUD & Persistence (DB repositories + Recipe/SourceSpan endpoints with FieldStatus updates).
- **Sprint 5:** Review UI (split-view in Next.js with image viewer + field highlights + badges).
- **Sprint 6:** Pantry & Match (pantry CRUD + matching logic + shopping list).

---

## Key Constraints (Non-negotiable)

- **No deletions:** Preserve all files in `apps/`, `packages/`, `infra/`, `docs/`.
- **Context7 required:** Resolve library IDs + get current docs before finalizing decisions.
- **Memory discipline:** Update SESSION_NOTES.md and NOW.md after each sprint.
- **Provenance-first:** Every extracted field must have SourceSpan or be marked missing.

---

## Next Milestone

Railway OCR pipeline stable → parsed fields populate and field statuses render correctly.

---

## Drift Guards (keep NOW fresh)

- Keep NOW to 5-12 active tasks; remove completed items.
- Refresh summary block every session.
- Move completed sprints to SESSION_NOTES; archive outdated tasks.

---

## Notes / Scratchpad

- SPEC.md is now the single source of truth; all implementation must follow it.
- Open questions (job queue, OCR lib, auth mode) are documented in SPEC.md and resolved by Context7.
- If NOW grows beyond 12 items, roll up to SESSION_NOTES and keep only active tasks here.
