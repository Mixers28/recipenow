# Implementation Progress - Sprint 2-3 (OCR Enhancement + LLM Vision Fallback)

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
- Enables tracking of extraction source ("ocr" or "llm-vision")
- Facilitates audit trails and source attribution

**Migration File:** [infra/migrations/002_add_source_method.sql](../infra/migrations/002_add_source_method.sql)
- Idempotent migration (uses `IF NOT EXISTS`)
- Adds source_method column with "ocr" default
- Creates indexes on source_method and (recipe_id, source_method)
- Column documentation for team reference

### 3. LLM Vision Service (Ollama Integration)
**File:** [apps/api/services/llm_vision.py](../apps/api/services/llm_vision.py) (New)

**LLMVisionService Class:**
- Offline-first design: Ollama + LLaVA-7B as primary
- Optional cloud fallback: Claude 3 Haiku or GPT-4 Vision
- Configuration via environment variables:
  - `OLLAMA_HOST`: Ollama server URL (default: http://localhost:11434)
  - `OLLAMA_MODEL`: Model identifier (default: llava:7b)
  - `LLM_FALLBACK_ENABLED`: Enable cloud fallback (default: true)
  - `LLM_FALLBACK_PROVIDER`: Cloud provider (claude or openai)
  - `LLM_FALLBACK_API_KEY`: API key for cloud provider

**Key Methods:**
- `extract_recipe_from_image(image_data: bytes) -> dict`: Vision-based recipe extraction
- `_extract_via_ollama(image_data)`: Offline extraction using Ollama + LLaVA
- `_extract_via_claude(image_data)`: Cloud fallback using Claude 3 Haiku
- `_extract_via_openai(image_data)`: Cloud fallback using GPT-4 Vision
- `_parse_json_response(response_text)`: Robust JSON extraction from LLM response

**Extraction Prompt:**
- Instructs LLM to read visible text (not infer or guess)
- Extracts: title, ingredients, steps, servings, times, cuisine, dietary notes
- Returns only fields clearly readable from image
- JSON structured response for easy parsing

### 4. Job Implementation Suite
**File:** [apps/api/worker/jobs.py](../apps/api/worker/jobs.py) (Enhanced)

**Ingest Job:** `async ingest_recipe(asset_id, user_id, file_data, asset_type)`
1. Stores uploaded asset file
2. Detects and corrects image orientation (Tesseract voting)
3. Runs OCR (PaddleOCR)
4. Creates Asset and OCRLines in database
5. Queues Structure Job
- Returns: Status, asset_id, ocr_line_count

**Structure Job:** `async structure_recipe(asset_id, user_id, recipe_id=None)`
1. Fetches OCR lines from asset
2. Runs deterministic parser (RecipeParser)
3. Checks for critical fields (title, ingredients, steps)
4. **If missing:** Invokes LLM vision fallback
5. Merges LLM results with OCR data
6. Tags merged fields with `source_method="llm-vision"`
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
- `_check_missing_critical_fields(recipe)`: Identifies missing critical fields
- `_merge_llm_fallback(ocr_result, llm_result, missing_critical)`: Merges results preserving OCR priority
- `_parse_time_to_minutes(time_str)`: Parses time strings (e.g., "1 hour 30 min" → 90)
- `_deduplicate_ingredients(ingredients)`: Removes duplicate ingredients
- `_normalize_times(times)`: Ensures time values are valid positive integers
- `_standardize_tags(tags)`: Normalizes tag case and removes duplicates
- `_quality_check(recipe)`: Validates recipe completeness

### 5. Dependencies
**File:** [apps/api/requirements.txt](../apps/api/requirements.txt)

**Added:**
- `httpx==0.27.0`: HTTP client for Ollama API calls
- `anthropic==0.21.0`: Claude API client (optional for cloud fallback)
- `openai==1.30.0`: OpenAI client (optional for cloud fallback)

## Architecture Overview

```
Upload API
    ↓
Ingest Job
    ├─ Save file
    ├─ Detect rotation (Tesseract PSM 0)
    └─ Run OCR (PaddleOCR on rotated image)
    ↓
Structure Job
    ├─ Parse OCR (deterministic parser)
    ├─ Check critical fields (title, ingredients, steps)
    ├─ If missing: LLM fallback (Ollama + LLaVA-7B)
    │   ├─ If Ollama fails: Cloud fallback (Claude/OpenAI)
    │   └─ Tag results with source_method="llm-vision"
    └─ Merge LLM + OCR results
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
   - LLM is strictly for reading visible text (fallback when OCR fails)
   - Does not infer missing ingredients, guess cooking methods, etc.
   - Maintains "source-of-truth" invariant (all data comes from uploaded media)

2. **Offline-First LLM**
   - Ollama + LLaVA-7B as primary (4.5 GB, local self-hosted)
   - Cloud APIs as optional fallback only
   - Reduces dependency on external services, improves privacy

3. **Provenance Tracking**
   - `source_method` field tracks extraction source (ocr vs llm-vision)
   - SourceSpans provide pixel-level audit trail
   - UI badges show source of each field (blue=OCR, purple=LLM, green=user, red=missing)

4. **Non-Overwriting Merge Strategy**
   - LLM results fill missing critical fields only
   - Never overwrites existing OCR data
   - Preserves OCR extraction as primary source

5. **Confident Rotation Detection**
   - Uses 3 thresholding methods + confidence voting
   - Threshold ≥3 votes required (99% accuracy per Carl Pearson's testing)
   - Graceful fallback to original orientation if uncertain

## Testing Checklist

- [ ] Rotation detection with 4 test images (0°, 90°, 180°, 270°)
- [ ] OCR extraction on rotated vs unrotated images
- [ ] LLM fallback with Ollama + LLaVA-7B (offline)
- [ ] LLM fallback with Claude 3 Haiku (cloud)
- [ ] LLM fallback with GPT-4 Vision (cloud)
- [ ] Merge logic: LLM fills missing title, ingredients, steps
- [ ] Source attribution: SourceSpan.source_method correctly tagged
- [ ] Review UI badges: Display source of each field
- [ ] Database migration: source_method column added successfully
- [ ] End-to-end: Upload → Ingest → Structure → Normalize → Ready for review

## Known Limitations

1. **ImageMagick Dependency**
   - Requires ImageMagick CLI (`convert` command)
   - Docker images must have it installed
   - Graceful fallback to original image if missing

2. **Tesseract Dependency**
   - Requires Tesseract OCR (`tesseract` command)
   - For rotation detection only (PSM 0)
   - PaddleOCR remains primary OCR engine

3. **Ollama Model Size**
   - LLaVA-7B is 4.5 GB
   - Requires adequate disk/memory for self-hosted deployment
   - Cloud fallback recommended if resources limited

4. **JSON Parsing Brittleness**
   - LLM responses sometimes have JSON embedded in text
   - Regex fallback for extracting JSON blocks
   - May fail on very unstructured responses (rare for vision task)

## Next Steps (Post-Implementation)

1. **End-to-End Testing**
   - Test with real recipe card images
   - Validate rotation detection on OCR failures
   - Verify LLM fallback fills missing fields

2. **UI Integration**
   - Implement source badges in RecipeForm component
   - Display OCR→LLM→User flow
   - Allow users to override auto-extracted fields

3. **Performance Optimization**
   - Cache Ollama responses (same recipe card images)
   - Batch LLM requests if multiple assets pending
   - Monitor API latency (both Ollama and cloud)

4. **Configuration Hardening**
   - Environment variable validation at startup
   - Graceful degradation if LLM unavailable
   - Clear error messages for misconfiguration

5. **Documentation**
   - Add Ollama setup guide to DEPLOYMENT_SETUP.md
   - LLM configuration options reference
   - Troubleshooting guide for common issues

## Files Modified

- `apps/api/services/ocr.py` - Rotation detection integration
- `apps/api/db/models.py` - Added source_method field
- `apps/api/worker/jobs.py` - Complete job suite implementation
- `apps/api/requirements.txt` - Added LLM dependencies
- `infra/migrations/002_add_source_method.sql` - Database schema
- `apps/api/services/llm_vision.py` - NEW: LLM vision service

## Remaining Sprints

- **Sprint 4:** Quality checks, tagging, cleanup
- **Sprint 5:** Review UI with source badges and field highlights
- **Sprint 6:** Pantry management and recipe matching

---

*Implementation by: Architect + Coder Agent*  
*Date: Sprint 2-3 completion*  
*SPEC.md Version: 2.1 (with OCR enhancement + LLM fallback)*
