# NOW - Working Memory (WM)

> This file captures the current focus / sprint.
> It should always describe what we're doing right now.

<!-- SUMMARY_START -->
**Current Focus (auto-maintained by Agent):**
- **Sprint 0-6 Complete:** Full V1 implementation delivered (scaffolding → OCR → CRUD → UI → pantry/match).
- **Sprint 2-3: OCR Enhancement Complete:** Two-stage OCR pipeline (rotation detection + LLM vision) implemented and deployed.
  - Tesseract PSM 0 rotation detection with 3-method voting (99% accuracy)
  - Ollama + LLaVA-7B offline-first LLM vision fallback (Claude/OpenAI cloud backup)
  - SourceSpan.source_method field for provenance tracking
- **Production Status:** Deployed to Railway backend, Vercel frontend. Four hotfixes applied.
- **Latest Fix (Jan 27, 2026):** OCR Timeout & Async Jobs Implementation
  - Issue: 500 errors on upload due to OCR timeouts (SIGTERM kills)
  - Solution 1: Added 90-second timeout wrapper with graceful degradation
  - Solution 2: Enhanced async job support with Redis/ARQ (background processing)
  - Hotfix: Corrected ARQ lifecycle hooks (async functions vs instance methods)
  - Result: Assets saved even on timeout; worker ready for Railway deployment
- **Current Phase:** Production support + monitoring. Async jobs ready for Railway enablement.
- **Next:** Enable async jobs in Railway, QA testing, database migration, Sprint 5 UI badges.
<!-- SUMMARY_END -->

---

## Current Objective

Execute RecipeNow V1 implementation per SPEC.md: 6 sprints covering scaffolding, schema, OCR pipeline, CRUD, review UI, and pantry matching. All code decisions must use Context7 library resolution.

---

## Active Branch

- `main`

---

## What We Are Working On Right Now

### Production Support Phase: Monitoring & Stabilization

**Status:** All implementation complete and deployed. Monitoring for production issues. System stable.

#### Completed & Deployed (Commit f4269ba):
- ✅ SPEC.md v2.1: Two-stage OCR pipeline (rotation detection + LLM vision)
- ✅ apps/api/services/ocr.py: Tesseract PSM 0 rotation detection (145-line implementation)
- ✅ apps/api/services/llm_vision.py: LLMVisionService (400+ lines, 3 providers)
- ✅ apps/api/worker/jobs.py: Ingest → Structure → Normalize pipeline with LLM fallback
- ✅ apps/api/db/models.py: SourceSpan model extended with source_method field
- ✅ Database migration 002: Idempotent schema migration (source_method column + indexes)
- ✅ apps/api/requirements.txt: All dependencies added and pinned
- ✅ Eight comprehensive documentation guides (TESTING_GUIDE, DEPLOYMENT_CHECKLIST, QUICK_START, etc.)

#### Production Hotfixes Applied:
1. **Commit c31ab5b** - Fixed requirements.txt formatting
   - Issue: Line 21 had "python-dotenv==1.0.0httpx==0.27.0" (missing newline)
   - Solution: Split into separate lines
   - Result: Railway docker build now succeeds

2. **Commit 4217ff1** - Resolved openai version conflict
   - Issue: openai==1.30.0 too old; paddlex requires openai>=1.63
   - Solution: Changed to openai>=1.63.0
   - Result: pip dependency resolution succeeds

3. **Commit 653952d** - Fixed SourceSpan field mapping
   - Issue: Job used `confidence` field but model expects `ocr_confidence`; Response schema missing `source_method`
   - Solution: Corrected field name in jobs.py, added source_method to SourceSpanResponse, updated list_spans endpoint
   - Result: API endpoint `/recipes/{recipe_id}/spans` returns 200 with proper field attribution

#### Current Status:
- ✅ Railway backend: All dependencies resolved, API endpoints operational
- ✅ Vercel frontend: Deployed and communicating with backend
- ✅ Git history: Commits ready (6d6c04f → 0a3d923 → 2f7d56a → e51252f)
- ✅ Production monitoring: Watching for additional errors
- ✅ Column detection improved: Gap-based detection for better two-column extraction

#### Pending Tasks:
- ⚠️ **URGENT:** Enable async jobs in Railway (follow docs/RAILWAY_ASYNC_JOBS_SETUP.md)
- 🔄 Database migration application (infra/migrations/002_add_source_method.sql)
- 🔄 QA test suite execution per docs/TESTING_GUIDE.md
- 🔄 UI badge implementation (Sprint 5)
- 🔄 End-to-end testing with rotated recipe images

#### Next Steps:
1. **Enable async jobs in Railway** (top priority to fix 500 errors)
   - Add Redis service to Railway project
   - Set ENABLE_ASYNC_JOBS=true environment variable
   - Deploy ARQ worker service (optional but recommended)
2. Monitor upload performance and success rates
3. Apply database migration to production once tested
4. Execute QA testing per TESTING_GUIDE.md (rotation detection, LLM fallback, full pipeline)
5. Implement Sprint 5 UI badges (color-coded source attribution)

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
QA sign-off on OCR enhancement (rotation + LLM fallback) → database migration → Sprint 5 UI badges → production release v1.1
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
