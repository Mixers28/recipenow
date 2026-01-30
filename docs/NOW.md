# NOW - Working Memory (WM)

> This file captures the current focus / sprint.
> It should always describe what we're doing right now.

<!-- SUMMARY_START -->
**Current Focus (auto-maintained by Agent):**
- **Sprint 0-6 Complete:** Full V1 implementation delivered (scaffolding → OCR → CRUD → UI → pantry/match).
- **Latest Feature (Jan 30, 2026):** Meal Photo Selection & Thumbnail Crop
  - **New Components:** ImageCropSelector (drag-to-crop), RecipeThumbnailCard (library grid)
  - **Fixes Applied:**
    1. thumbnail_crop added to repository allowed_fields (was silently ignored)
    2. EXIF orientation handling for rotated phone photos
    3. Crop scaling to fill 4:5 card container
    4. Mobile touch handling (touchAction: none + preventDefault)
  - **Commits:** 846574a, b014cd3, e7b67d0, a56aa38, 2dd2da8, 5e8db33
- **Current Phase:** Feature complete, ready to push
- **Next:** Push commits, test on mobile, add more recipes
<!-- SUMMARY_END -->

---

## Current Objective

Execute RecipeNow V1 implementation per SPEC.md: 6 sprints covering scaffolding, schema, OCR pipeline, CRUD, review UI, and pantry matching. All code decisions must use Context7 library resolution.

---

## Active Branch

- `main`

---

## What We Are Working On Right Now

### Current Phase: Meal Photo Selection Feature Complete

**Status:** Feature implemented and tested. Ready to push.

#### Session 16 Features (Jan 30, 2026):

**Meal Photo Selection:**
- Users can select a crop area on uploaded recipe images to show just the meal photo
- Drag-to-select interface with live preview
- Mobile touch support with scroll prevention

**New Components:**
1. `ImageCropSelector` - Drag-to-select crop UI with percentage-based coordinates
2. `RecipeThumbnailCard` - Library card showing cropped meal photo thumbnail
3. `FlipRecipeCard` updates - Display cropped area filling 4:5 container

**Bug Fixes:**
1. **thumbnail_crop not saving** - Added to repository allowed_fields whitelist
2. **Rotated images** - EXIF orientation handling via PIL ImageOps.exif_transpose
3. **Crop not filling card** - Scale both width/height based on crop percentages
4. **Mobile scroll issue** - touchAction: 'none' + preventDefault on touch handlers

#### Commits Ready:
- `846574a` - fix: Handle EXIF orientation and improve crop display
- `b014cd3` - fix: Add thumbnail_crop to allowed update fields in repository
- `e7b67d0` - fix: Scale cropped image to fill recipe card container
- `a56aa38` - fix: Show full image in crop selector for accurate preview
- `2dd2da8` - fix: Prevent page scroll on mobile when drawing crop box
- `5e8db33` - feat: Add thumbnail cards to library grid

#### Next Steps:
1. Push commits: `git push origin main`
2. Test crop feature on mobile devices
3. Add more recipes to populate library

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
