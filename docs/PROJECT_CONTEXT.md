# Project Context - Long-Term Memory (LTM)

> High-level design, tech decisions, constraints for this project.
> This is the **source of truth** for agents and humans.

<!-- SUMMARY_START -->
**Summary (auto-maintained by Agent):**
- RecipeNow converts uploaded recipe media into canonical recipes with per-field provenance and a review-first UI.
- V1 scope: OCR ingest, constrained parsing, manual correction, pantry matching, and verification; no public sharing or URL import.
- **Stack (Finalized):** FastAPI 0.128.0 + Postgres 16 + Next.js 16.1.0 + ARQ 0.26.3 + PaddleOCR 3.3.2.
- **Deployment:** Railway (backend + worker), Vercel (frontend); Docker Compose for local dev.
- **Auth:** Multi-user with JWT tokens and user-scoped data isolation.
- **Parsing:** Deterministic heuristics; LLM deferred to Sprint 3.
- Sprint 0 complete; now implementing Sprint 1 (schema + persistence).
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
- **OCR:** PaddleOCR 3.3.2 (finalized; superior accuracy for recipes).
- **Auth:** Multi-user with JWT tokens; user-scoped data isolation (user_id foreign key on all assets/recipes/pantry).
- **Deployment:** Railway (backend API + worker), Vercel (Next.js frontend), Docker Compose (local development).
- **Storage:** MinIO (configured in docker-compose; default for local dev; production TBD on Railway).
- **Parsing:** Deterministic heuristics only (V1); LLM deferred to Sprint 3 (optional block classification).
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

## 5. Memory Hygiene (Drift Guards)

- Keep this summary block current and <= 300 tokens.
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
