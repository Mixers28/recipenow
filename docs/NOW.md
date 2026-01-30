# NOW - Working Memory (WM)

> This file captures the current focus / sprint.
> It should always describe what we're doing right now.

<!-- SUMMARY_START -->
**Current Focus (auto-maintained by Agent):**
- **Session Jan 30, 2026:** Worker pipeline debugging session - multiple fixes applied.
- **Status:** PaddleOCR + Redis + ARQ worker pipeline operational. OpenAI Vision API configured but recipe population not completing.
- **Blockers Resolved:** ctx parameters, prepared statements, API key permissions, file storage access.
- **Current Blocker:** Vision extraction succeeds but recipe fields not being populated (database timeout or extract_job issue).
- **Next:** Debug extract_job to ensure vision results save to Recipe model; optimize DB pool.
<!-- SUMMARY_END -->

---

## Session Summary: Jan 30, 2026 (Late Night Debugging)

### What's Working
- ✅ **Railway API Service:** Deployed, endpoints operational
- ✅ **Railway Worker Service:** Deployed, processing jobs from Redis
- ✅ **Redis Job Queue:** Jobs queuing and dequeuing correctly
- ✅ **PaddleOCR Extraction:** Successfully extracting 50+ OCR lines per image
- ✅ **OpenAI API Key:** Configured with full permissions (401 error resolved)
- ✅ **Database Prepared Statements:** Fixed with `prepare_threshold=None`
- ✅ **ARQ Worker Functions:** All ctx parameters added correctly
- ✅ **Tabbed UI:** Recipe review page changed from split-screen to tabs per user request

### What's NOT Working
- ❌ **Recipe Population:** Vision extraction runs but ingredients/steps not saved to Recipe
- ❌ **Database Pool Timeout:** `Unable to check out connection from the pool due to timeout`
- ⚠️ **extract_job:** May be failing silently after OCR completes

### Fixes Applied This Session

| Commit | Fix |
|--------|-----|
| `f662798` | Add `prepare_threshold=None` to worker DB connections |
| `3a8f41b` | Pass ctx parameter to extract_job call in ingest_job |
| `774be85` | Add ctx parameter and file_data to ingest_recipe job |
| `c30ed13` | Rewrite ingest_recipe for LLM vision PRIMARY |
| `a164215` | Add ctx parameter to all ARQ worker functions |
| `4116032` | Correct storage import path in worker |
| `e729ab6` | Fix MediaMediaAsset double-replacement typo |
| `276b669` | Restore WorkerSettings class |
| `802e0cc` | Upgrade SQLAlchemy for Python 3.13 compatibility |

### Environment Variables Required

**recipenow-worker service needs:**
- `OPENAI_API_KEY` - OpenAI API key with full permissions (not restricted)
- `DATABASE_URL` - Supabase connection string
- `REDIS_URL` - Redis connection string

---

## Next Steps (Priority Order)

### 1. Debug extract_job Recipe Population (HIGH)
- Add logging before/after recipe update in `apps/worker/jobs.py` line ~380
- Verify vision_result contains title, ingredients, steps
- Check if database commit succeeds after recipe update

### 2. Fix Database Connection Pool Timeout (HIGH)
- Current error: `Unable to check out connection from the pool due to timeout`
- Add `pool_timeout=30` to create_engine calls
- Consider `pool_pre_ping=True` for connection validation

### 3. Add Vision Extraction Logging (MEDIUM)
- Log vision API response before parsing
- Log recipe fields before database save
- Track source_method='vision-api' attribution

### 4. Test with Smaller Image (LOW)
- Rule out timeout caused by large image processing
- Verify pipeline works end-to-end with simple recipe card

---

## Architecture Notes

### Pipeline Flow
```
Upload → API saves file → Queue ingest_job → Worker:
  1. PaddleOCR extracts text (WORKING)
  2. Save OCR lines to DB (WORKING)
  3. Call extract_job with ctx (FIXED)
  4. Vision API extracts recipe (CONFIGURED)
  5. Save Recipe fields to DB (NOT WORKING)
```

### Key Files
- `apps/worker/jobs.py` - Main worker job definitions (NOT apps/api/worker/jobs.py)
- `apps/api/services/llm_vision.py` - OpenAI Vision service
- `apps/api/services/ocr.py` - PaddleOCR service
- `apps/api/routers/assets.py` - Upload endpoint with job queuing

---

## Key Constraints (Non-negotiable)

- **No deletions:** Preserve all files in `apps/`, `packages/`, `infra/`, `docs/`.
- **Context7 required:** Resolve library IDs + get current docs before finalizing decisions.
- **Memory discipline:** Update SESSION_NOTES.md and NOW.md after each sprint.
- **Provenance-first:** Every extracted field must have SourceSpan or be marked missing.

---

## Notes / Scratchpad

- Worker uses `apps/worker/jobs.py`, NOT `apps/api/worker/jobs.py` (two different files!)
- Supabase transaction pooler requires `prepare_threshold=None` on all connections
- ARQ worker functions require `ctx` as first parameter
- OpenAI API key needs full permissions, not restricted scope
