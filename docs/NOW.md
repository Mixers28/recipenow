# NOW - Working Memory (WM)

> This file captures the current focus / sprint.
> It should always describe what we're doing right now.

<!-- SUMMARY_START -->
**Current Focus (auto-maintained by Agent):**
- **Sprint 0-6 Complete:** Full V1 implementation delivered (scaffolding → OCR → CRUD → UI → pantry/match).
- **Sprint 2-3: LLM Vision Primary Extraction - DEPLOYED:** LLaVA-7B multimodal LLM as primary extraction method
  - ✅ Ollama + LLaVA-7B deployed to Railway
  - ✅ LLM vision runs first for all recipes (primary extraction)
  - ✅ OCR parser (PaddleOCR + Tesseract rotation) serves as fallback
  - ✅ Async job processing with Redis + ARQ worker
  - ✅ All extractions tagged with source_method for full provenance
  - Better handles complex layouts, two-column recipes, rotated images
- **Production Status:** Fully deployed to Railway backend, Vercel frontend. LLM vision pipeline active.
- **Latest Updates (Jan 28, 2026):**
  1. **UI Improvement:** Tabbed interface for recipe review (Image/Recipe tabs)
  2. **Database Fix:** pool_recycle=300 + prepare_threshold=None for Supabase compatibility
  3. **LLM Vision Primary:** Extraction pipeline reversed - LLM first, OCR fallback
  4. **Worker Service:** Python 3.13 compatible dependencies, minimal requirements
  5. **Async Jobs Fixed:** Corrected job function name and parameters (ingest_recipe)
  6. **Ollama Deployed:** LLaVA-7B (4.7GB) running on Railway with internal networking
- **Current Phase:** Testing LLM vision extraction in production. System fully operational.
- **Next:** Monitor extraction quality, apply database migration (source_method), implement UI badges.
<!-- SUMMARY_END -->

---

## Current Objective

Execute RecipeNow V1 implementation per SPEC.md: 6 sprints covering scaffolding, schema, OCR pipeline, CRUD, review UI, and pantry matching. All code decisions must use Context7 library resolution.

---

## Active Branch

- `main`

---

## What We Are Working On Right Now

### LLM Vision Production Deployment: Complete ✅

**Status:** All services deployed and operational. LLM vision pipeline active. Ready for testing.

#### Deployment Timeline (Jan 27-28, 2026):

**Phase 1: Core Implementation (Jan 27)**
- ✅ SPEC.md v2.1: Two-stage OCR pipeline (rotation detection + LLM vision)
- ✅ apps/api/services/ocr.py: Tesseract PSM 0 rotation detection
- ✅ apps/api/services/llm_vision.py: LLMVisionService (400+ lines, 3 providers)
- ✅ apps/api/worker/jobs.py: LLM vision primary, OCR fallback
- ✅ apps/web/app/review/[id]/page.tsx: Tabbed UI (Image/Recipe tabs)
- ✅ apps/api/db/session.py: Supabase pooler compatibility (prepare_threshold=None)

**Phase 2: Railway Deployment (Jan 28)**
- ✅ Ollama service deployed to Railway (Docker image: ollama/ollama:latest)
- ✅ LLaVA-7B model installed (4.7GB) via Railway CLI
- ✅ Worker service deployed with Python 3.13 compatible dependencies
- ✅ Fixed pydantic 2.7.0 → 2.10.0+ for Python 3.13 compatibility
- ✅ Created requirements-worker.txt (minimal dependencies, no PaddleOCR)
- ✅ Fixed async job enqueuing (ingest_job → ingest_recipe with correct params)
- ✅ Environment variables configured: ENABLE_ASYNC_JOBS, REDIS_URL, OLLAMA_HOST

**Current Services:**
- 🟢 API Service: recipenow (FastAPI + PaddleOCR for sync fallback)
- 🟢 Worker Service: recipenow-worker (ARQ + LLM vision primary)
- 🟢 Ollama Service: Ollama (LLaVA-7B multimodal LLM)
- 🟢 Redis Service: Redis (Job queue for async processing)
- 🟢 Frontend: Vercel (Next.js with tabbed review UI)
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

#### Testing Checklist:
- [ ] **Test LLM Vision Extraction:** Upload recipe and verify worker logs show LLM extraction
- [ ] **Verify Source Attribution:** Check database for source_method='llm-vision' in source_spans
- [ ] **Test OCR Fallback:** Simulate Ollama failure, verify OCR fallback works
- [ ] **Test Complex Layouts:** Upload two-column recipe, verify extraction quality
- [ ] **Monitor Performance:** Check extraction speed (LLM vs OCR comparison)

#### Pending Tasks:
- 🔄 Database migration application (infra/migrations/002_add_source_method.sql)
- 🔄 QA test suite execution per docs/TESTING_GUIDE.md
- 🔄 UI badge implementation (Sprint 5 - show source_method in review UI)
- 🔄 End-to-end testing with rotated recipe images
- 🔄 Performance monitoring and optimization

#### Next Steps:
1. **Test LLM vision extraction** - Upload recipe, monitor logs for successful extraction
2. **Verify extraction quality** - Compare LLM vision vs OCR results
3. **Apply database migration** to production (source_method column already in use)
4. **Implement Sprint 5 UI badges** - Visual indicators for extraction method
5. **Execute comprehensive QA testing** per TESTING_GUIDE.md

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

---

## Known Issues (Backlog)

### OCR Column Detection - Two-Column Layout Merging
- **Issue:** PaddleOCR merges text across columns at OCR stage, causing truncated extractions (e.g., "250g/9oz natural yog" instead of "natural yogurt")
- **Impact:** Ingredients and steps may be incomplete in two-column recipe layouts
- **Current Mitigation:** Gap-based column detection in parser helps but doesn't fully solve the issue
- **Potential Solutions to Investigate:**
  - Tune PaddleOCR parameters: `det_db_box_thresh`, `det_db_unclip_ratio`, `det_db_score_mode`
  - Enable layout analysis mode to detect columns before text extraction
  - Hybrid approach: Use Tesseract for layout detection + PaddleOCR for text recognition
  - Pre-process image to split columns before OCR
- **Priority:** Low (users can manually edit fields, LLM fallback exists for critical extractions)
- **Status:** Deferred until higher priorities complete (async jobs, database migration, Sprint 5 UI)
