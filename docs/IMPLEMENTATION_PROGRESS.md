# Implementation Progress - Vision-Primary Extraction

**Status:** Core implementation complete; ready for testing.

## What Was Implemented

### 1. OCRService with Rotation Detection
**File:** [apps/api/services/ocr.py](../apps/api/services/ocr.py)

**Method:** `_detect_and_correct_rotation(image_path: str) -> Tuple[str, int]`
- Tesseract PSM 0 (orientation detection mode) with 3 thresholding methods
- Confidence voting with threshold ≥3
- Supports 0°, 90°, 180°, 270° rotations
- ImageMagick fallback for rotation application
- Robust error handling (timeouts, missing tools)

**Method:** `extract_text(file_data, asset_type) -> List[OCRLineData]`
- Temp file management for uploaded assets
- Integrated rotation detection for images
- PaddleOCR invocation on (potentially rotated) image
- Result parsing into OCRLineData objects
- Comprehensive logging for audit trail

### 2. Database Schema Updates
**File:** [apps/api/db/models.py](../apps/api/db/models.py)

**SourceSpan Model:**
- Added `source_method: Mapped[str] = mapped_column(String(20), default="ocr")`
- Enables tracking of extraction source ("ocr" or "vision-api")
- Facilitates audit trails and source attribution

**Migration File:** [infra/migrations/002_add_source_method.sql](../infra/migrations/002_add_source_method.sql)
- Idempotent migration (uses `IF NOT EXISTS`)
- Adds source_method column with "ocr" default
- Creates indexes on source_method and (recipe_id, source_method)
- Column documentation for team reference

**File:** [apps/api/services/llm_vision.py](../apps/api/services/llm_vision.py) (New)

**LLMVisionService Class:**
- OpenAI Vision API primary extraction (no local/self-hosted LLMs)
- Configuration via environment variables:
  - `OPENAI_API_KEY`: Required API key
  - `VISION_MODEL`: Vision model name (e.g., `gpt-4o-mini`)
  - `VISION_MAX_OUTPUT_TOKENS`: Output token cap
  - `VISION_STRICT_JSON`: Enforce strict JSON

**Key Methods:**
- `extract_with_evidence(image_data: bytes, ocr_lines: list) -> dict`: Vision extraction with OCR evidence
- `extract_recipe_from_image(image_data: bytes) -> dict`: Convenience wrapper

**Extraction Prompt:**
- Instructs vision model to read visible text only (no inference)
- Extracts: title, ingredients, steps, servings, times
- Returns strict JSON with `evidence_ocr_line_ids`

### 4. Job Implementation Suite
**File:** [apps/api/worker/jobs.py](../apps/api/worker/jobs.py) (Enhanced)

**Ingest Job:** `async ingest_recipe(asset_id, user_id, file_data, asset_type)`
1. Stores uploaded asset file
2. Detects and corrects image orientation (Tesseract voting)
3. Runs OCR (PaddleOCR)
4. Creates Asset and OCRLines in database
5. Queues Extract Job
- Returns: Status, asset_id, ocr_line_count

**Extract Job:** `async extract_recipe(asset_id, user_id, recipe_id=None)`
1. Fetches OCR lines from asset
2. Runs OpenAI Vision extraction (primary)
3. Builds SourceSpans from OCR evidence IDs
4. Falls back to deterministic parser only if vision extraction fails
5. Tags extracted fields with `source_method="vision-api"`
7. Creates Recipe and SourceSpans with provenance
8. Queues Normalize Job
- Returns: Status, recipe_id, field_statuses

**Normalize Job:** `async normalize_recipe(recipe_id, user_id)`
1. Deduplicates and normalizes ingredients
2. Fixes time formats
3. Standardizes tags/categories
4. Runs quality checks
5. Updates recipe status (draft → review or draft_with_issues)
- Returns: Status, quality_issues

**Helper Functions:**
- `_build_span_from_evidence(...)`: Computes bbox from OCR line evidence
- `_vision_to_recipe_payload(...)`: Normalizes vision JSON to recipe payload
- `_parse_time_to_minutes(time_str)`: Parses time strings (e.g., "1 hour 30 min" → 90)
- `_deduplicate_ingredients(ingredients)`: Removes duplicate ingredients
- `_normalize_times(times)`: Ensures time values are valid positive integers
- `_standardize_tags(tags)`: Normalizes tag case and removes duplicates
- `_quality_check(recipe)`: Validates recipe completeness

### 5. Dependencies
**File:** [apps/api/requirements.txt](../apps/api/requirements.txt)

**Added:**
- `openai>=1.63.0`: OpenAI client (vision primary)

## Architecture Overview

```
Upload API
    ↓
Ingest Job
    ├─ Save file
    ├─ Detect rotation (Tesseract PSM 0)
    └─ Run OCR (PaddleOCR on rotated image)
    ↓
Extract Job
    ├─ Vision extraction (OpenAI, primary)
    ├─ Build spans from OCR evidence IDs
    └─ Fallback to deterministic parser only on vision failure
    ↓
Normalize Job
    ├─ Deduplicate ingredients
    ├─ Normalize times
    └─ Quality checks
    ↓
Recipe Ready (draft → review)
```

## Key Design Decisions

1. **Vision Reader, Not Inference Engine**
   - Vision model reads visible text only
   - Does not infer missing ingredients, guess cooking methods, etc.
   - Maintains "source-of-truth" invariant (all data comes from uploaded media)

2. **Hosted Vision Only**
   - OpenAI Vision API is primary (no local/self-hosted LLMs)
   - OCR supplies line evidence for bbox provenance

3. **Provenance Tracking**
   - `source_method` field tracks extraction source (ocr vs vision-api)
   - SourceSpans provide pixel-level audit trail
   - UI badges show source of each field (blue=OCR, purple=Vision, green=user, red=missing)

4. **Fallback Strategy**
   - Deterministic parser used only if vision extraction fails
   - OCR data preserved for provenance

5. **Confident Rotation Detection**
   - Uses 3 thresholding methods + confidence voting
   - Threshold ≥3 votes required (99% accuracy per Carl Pearson's testing)
   - Graceful fallback to original orientation if uncertain

## Testing Checklist

- [ ] Rotation detection with 4 test images (0°, 90°, 180°, 270°)
- [ ] OCR extraction on rotated vs unrotated images
- [ ] Vision extraction with OpenAI (image + OCR evidence IDs)
- [ ] Source attribution: SourceSpan.source_method correctly tagged
- [ ] Review UI badges: Display source of each field
- [ ] Database migration: source_method column added successfully
- [ ] End-to-end: Upload → Ingest → Extract → Normalize → Ready for review

## Known Limitations

1. **ImageMagick Dependency**
   - Requires ImageMagick CLI (`convert` command)
   - Docker images must have it installed
   - Graceful fallback to original image if missing

2. **Tesseract Dependency**
   - Requires Tesseract OCR (`tesseract` command)
   - For rotation detection only (PSM 0)
   - PaddleOCR remains primary OCR engine

3. **JSON Parsing Brittleness**
   - Vision API responses sometimes have JSON embedded in text
   - Regex fallback for extracting JSON blocks
   - May fail on very unstructured responses (rare for vision task)

## Next Steps (Post-Implementation)

1. **End-to-End Testing**
   - Test with real recipe card images
   - Validate rotation detection on OCR failures
   - Verify vision extraction populates title, ingredients, steps

2. **UI Integration**
   - Implement source badges in RecipeForm component
   - Display OCR→Vision→User flow
   - Allow users to override auto-extracted fields

3. **Performance Optimization**
   - Batch vision requests if multiple assets pending

4. **Configuration Hardening**
   - Environment variable validation at startup
   - Graceful degradation if Vision API unavailable
   - Clear error messages for misconfiguration

5. **Documentation**
   - Vision configuration options reference
   - Troubleshooting guide for common issues

## Files Modified

- `apps/api/services/ocr.py` - Rotation detection integration
- `apps/api/db/models.py` - Added source_method field
- `apps/api/worker/jobs.py` - Complete job suite implementation
- `apps/api/requirements.txt` - Added OpenAI dependency
- `infra/migrations/002_add_source_method.sql` - Database schema
- `apps/api/services/llm_vision.py` - NEW: Vision extraction service

## Remaining Sprints

- **Sprint 4:** Quality checks, tagging, cleanup
- **Sprint 5:** Review UI with source badges and field highlights
- **Sprint 6:** Pantry management and recipe matching

---

*Implementation by: Architect + Coder Agent*  
*Date: Sprint 2-3 completion*  
*SPEC.md Version: V1.1 (vision-primary)*
