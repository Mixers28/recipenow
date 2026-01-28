# Project Context - Long-Term Memory (LTM)

> High-level design, tech decisions, constraints for this project.
> This is the **source of truth** for agents and humans.

<!-- SUMMARY_START -->
**Summary (auto-maintained by Agent):**
- RecipeNow converts uploaded recipe media into canonical recipes with per-field provenance and a review-first UI. V1 complete and production-deployed.
- **Full Pipeline:** LLM vision primary (Ollama + LLaVA-7B) → OCR fallback (PaddleOCR + Tesseract rotation) → normalization → review UI → pantry matching.
- **Stack (Finalized):** FastAPI 0.128.0 + Postgres 16 + Next.js 16.1.0 + ARQ 0.26.3 + PaddleOCR 3.3.2 + Tesseract PSM 0 + Ollama/LLaVA-7B.
- **LLM Vision PRIMARY (Jan 28, 2026):** Ollama + LLaVA-7B runs first for all recipes. OCR parser serves as fallback. Better handles complex layouts.
- **Deployment:** Railway (API + Worker + Ollama + Redis, live) + Vercel (frontend, live). Docker Compose for local dev.
- **Auth:** Multi-user with JWT tokens and user-scoped data isolation.
- **Provenance:** SourceSpan.source_method field tracks llm-vision vs ocr attribution per field.
- **Status:** All 6 sprints complete, LLM vision pipeline deployed, async jobs operational (927cb3d, 1510e83, cde9cf9), ready for testing.
<!-- SUMMARY_END -->

---

## 1. Project Overview

- **Name:** RecipeNow
- **Owner:** TBD
- **Purpose:** Turn screenshots/photos/PDF pages of recipes into structured, searchable recipes with traceable provenance.
- **Primary Users:** Home cooks and small teams digitizing personal recipe collections.
- **V1 Goals:**
  - Upload recipe media, OCR it, and create draft recipes.
  - Review and correct extracted fields in a split-view UI with highlights.
  - Tag recipes and match against pantry items to suggest what to cook.
- **Out of Scope (V1):**
  - Public sharing/community features.
  - URL auto-import (unless user uploads screenshots/PDFs).
  - Perfect nutrition/macros without explicit user approval.
  - Automatic unit conversion beyond basic servings multiplier.

---

## 2. Core Design Pillars

- **Source-of-truth only:** If it is not in uploaded media, it is missing.
- **No silent inference:** Ambiguous or missing values become questions.
- **Provenance per field:** Every field stores one or more SourceSpans.
- **User is final editor:** Review UI is the primary workflow.

---

## 3. Technical Decisions & Constraints

- **Backend:** FastAPI 0.128.0 (API + workers), Python 3.11.
- **Frontend:** Next.js 16.1.0 (App Router).
- **Database:** Postgres 16.
- **Job Queue:** ARQ 0.26.3 (Redis-backed async jobs).
- **Extraction Pipeline:** LLM vision primary, OCR fallback:
  - **PRIMARY: LLM Vision** - Ollama + LLaVA-7B (7B parameter multimodal model, 4.7 GB)
    - Runs first for ALL recipes in async worker
    - Deployed to Railway as separate Ollama service
    - Internal networking: `http://Ollama.railway.internal:11434`
    - Vision reading only (extract visible text), not inference
    - Cloud fallback: Claude 3 Haiku + GPT-4V (optional, via API keys)
  - **FALLBACK: OCR Parser** - Used when LLM vision fails
    - **Stage 1 (Rotation):** Tesseract PSM 0 with 3-method voting (0°/90°/180°/270°)
    - **Stage 2 (Extraction):** PaddleOCR 3.3.2 on corrected image
    - **Parsing:** Deterministic heuristics for ingredient/step extraction
- **Auth:** Multi-user with JWT tokens; user-scoped data isolation (user_id foreign key on all assets/recipes/pantry).
- **Deployment:** Railway (backend API + worker, LIVE), Vercel (Next.js frontend, LIVE), Docker Compose (local development).
- **Storage:** MinIO (configured in docker-compose; default for local dev).
- **Parsing:** Deterministic heuristics + optional LLM vision fallback (Sprint 2-3 enhancement). No inference or guessing.
- **Data integrity rules:**
  - All extracted fields must have provenance or be marked user-entered.
  - Do not invent quantities/units.
  - Verification requires title, at least 1 ingredient, and 1 step.
  - Missing times/servings are allowed only with explicit user confirmation.
- **Privacy:** Keep assets private; no sharing in V1.

---

## 4. Architecture Snapshot

- **Pipeline:** Ingest job -> Structure job -> Normalize job.
- **Key data types:** MediaAsset, OCRLine/OCRToken, Recipe, SourceSpan, FieldStatus.
- **Core screens:** Library, Recipe Review (split view), Pantry, Recipe Match, Cook Mode.
- **API surface:** assets upload/ocr/structure, recipes CRUD + verify, provenance spans, pantry CRUD, match + shopping list.

---

## 5. Recent Enhancement: LLM Vision Primary Extraction (Jan 25-28, 2026)

**Problem:** PaddleOCR fails on rotated recipe cards and two-column layouts; deterministic parser insufficient for complex recipes.

**Solution v1 (Jan 25):** Two-stage OCR pipeline with LLM vision fallback
- Rotation detection (Tesseract PSM 0) + LLM vision when critical fields missing
- 99% rotation accuracy on 152 recipe cards

**Solution v2 (Jan 28):** LLM vision as PRIMARY extraction method
- **Pipeline Reversal:** LLM vision runs first, OCR serves as fallback
- **Rationale:** Better handles complex layouts, two-column recipes, handwriting
- **Deployment:** Ollama + LLaVA-7B deployed to Railway as separate service
- **Worker Service:** Python 3.13 compatible, async job processing with ARQ
- **Performance:** Faster responses (async), better extraction quality

**Code Changes:**
- apps/api/services/llm_vision.py: LLMVisionService (Ollama + cloud fallback)
- apps/api/worker/jobs.py: LLM vision primary, OCR fallback
- apps/api/routers/assets.py: Fixed async job enqueuing (ingest_recipe)
- apps/api/requirements-worker.txt: Minimal deps for worker (no PaddleOCR)
- apps/api/db/session.py: Supabase pooler fix (prepare_threshold=None)
- apps/web/app/review/[id]/page.tsx: Tabbed UI (Image/Recipe tabs)

**Production Status:** Deployed (927cb3d, 1510e83, cde9cf9), all services operational, ready for testing.

---

## 6. Memory Hygiene (Drift Guards)

- Keep this summary block current and <= 400 tokens.
- Move stable decisions into the Change Log so they persist across sessions.
- Keep NOW to 5-12 active tasks; archive or remove completed items.
- Roll up SESSION_NOTES into summaries weekly (or every few sessions).

---

## 6. Links & Related Docs

- Spec: `docs/SPEC.md`
- Working memory: `docs/NOW.md`
- Session log: `docs/SESSION_NOTES.md`
- Workflow: `docs/AGENT_SESSION_PROTOCOL.md`
- UI notes: `docs/UI_NOTES.md`
- Implementation plan: `docs/IMPLEMENTATION_PLAN.md`

---

## 7. Change Log (High-Level Decisions)

Use this section for **big decisions** only:

- `2026-01-09` - **Auth Mode:** Decided on multi-user with JWT tokens (not single-user) for user-scoped data isolation.
- `2026-01-09` - **Deployment:** Decided on Railway (backend + worker) + Vercel (frontend) for production; Docker Compose for local dev.
- `2026-01-09` - **LLM for Block Classification:** Deferred to Sprint 3; V1 uses deterministic heuristics only.
- `2026-01-09` - **Context7 Library Versions:** Locked FastAPI 0.128.0, Next.js 16.1.0, psycopg 3.3.2, ARQ 0.26.3, PaddleOCR 3.3.2.
