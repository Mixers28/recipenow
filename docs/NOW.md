# NOW - Working Memory (WM)

> This file captures the current focus / sprint.
> It should always describe what we're doing right now.

<!-- SUMMARY_START -->
**Current Focus (auto-maintained by Agent):**
- **Sprint 0-6 Complete:** Full V1 implementation delivered (scaffolding → OCR → CRUD → UI → pantry/match).
- **Latest Fix (Jan 30, 2026):** Vision API Pipeline Debugging
  - **Root Cause:** Worker `extract_job` had wrong sys.path, causing Vision API import to fail silently
  - **Symptoms:** Recipe extraction showed wrong title, jumbled steps (OCR-only fallback was used)
  - **Fixes Applied:**
    1. Added missing ORM columns (`servings_estimate`, `evidence`) to match DB migrations
    2. Removed duplicate `apps/api/worker/` dead code (714 lines)
    3. Created shared `services/ingredient_utils.py` module
    4. Fixed sys.path in `extract_job` and `normalize_job` (`/app/packages` + `/app/apps`)
  - **Commits:** 3b9cc9f, dfe6c14, 8ad2f31 (ready to push)
- **Current Phase:** Deploy fixes, test Vision API extraction
- **Next:** Push commits, verify correct recipe extraction, monitor worker logs
<!-- SUMMARY_END -->

---

## Current Objective

Execute RecipeNow V1 implementation per SPEC.md: 6 sprints covering scaffolding, schema, OCR pipeline, CRUD, review UI, and pantry matching. All code decisions must use Context7 library resolution.

---

## Active Branch

- `main`

---

## What We Are Working On Right Now

### Current Phase: Vision API Pipeline Fix Deployment

**Status:** Critical bug found and fixed. Commits ready to push.

#### Session 15 Bug Fixes (Jan 30, 2026):

**Root Cause Identified:** Vision API extraction was failing silently, causing fallback to OCR-only parser. The worker's `extract_job` had incorrect `sys.path` entries.

**Symptoms:**
- Recipe title showing random OCR text ("alt and freshly ground black pepper")
- Steps jumbled and incomplete
- Ingredients missing quantities

**Fixes Applied:**

1. **Commit 3b9cc9f** - Add missing ORM columns and remove duplicate worker
   - Added `servings_estimate` column to Recipe model
   - Added `evidence` column to SourceSpan model
   - Deleted `apps/api/worker/` directory (714 lines of duplicate dead code)

2. **Commit dfe6c14** - Move extract_ingredient_name to shared module
   - Created `apps/api/services/ingredient_utils.py`
   - Updated `pantry.py` to import from shared module
   - Fixes `ModuleNotFoundError: No module named 'worker'`

3. **Commit 8ad2f31** - Fix sys.path in extract_job and normalize_job
   - Changed `/packages` → `/app/packages`
   - Added missing `/app/apps` to path
   - This was the **root cause** - Vision API imports were failing

#### Current Status:
- ✅ All fixes committed locally
- ⏳ Ready to push: `git push origin main`
- ⏳ After push: Railway will auto-deploy

#### Verification Steps (after deploy):
1. Upload a recipe image
2. Check worker logs for `[Phase 2] Calling Vision API` (should NOT show "falling back to parser")
3. Verify extracted recipe has correct title, ingredients, and steps
4. Check that source_method shows "vision-api" not "ocr"

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
