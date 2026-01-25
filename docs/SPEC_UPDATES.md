# SPEC.md Updates — OCR Enhancement + LLM Vision Fallback

**Date:** January 25, 2026  
**Status:** Integrated into SPEC.md (Canonical)  
**Scope:** V1 Implementation (Sprints 2-5)

---

## Summary of Changes

RecipeNow V1 now includes a **two-stage OCR + LLM Vision approach** to maximize recipe extraction reliability while maintaining the "source-of-truth" invariant.

### What Changed

#### 1. Constraints & Invariants (Updated Invariant 1 & 3)
- **Invariant 1:** Now explicitly allows **Vision LLM fallback** as a secondary extraction method (after OCR fails).
  - Key distinction: LLM reads **visible text from media**, not inferred values.
  - Both OCR and LLM are "readers"; neither guesses.
- **Invariant 3:** SourceSpan now includes `source_method: enum("ocr", "llm-vision")` to track extraction origin.

#### 2. SourceSpan Data Model
Added field:
```python
source_method: enum("ocr", "llm-vision")  # How this field was extracted
```

#### 3. Ingest Job (Sprint 2)
**New:** Orientation detection and correction
- Tesseract PSM 0 with 3 thresholding methods.
- Confidence voting to select best rotation (0°, 90°, 180°, 270°).
- ImageMagick auto-rotation before OCR.
- Proven: ~99% success rate (Carl Pearson: 152/152 recipe cards).

#### 4. Structure Job (Sprint 3)
**New:** LLM Vision fallback when OCR insufficient
- **Trigger:** After deterministic parsing, if title OR ingredients OR steps are missing.
- **Action:** Invoke Ollama + LLaVA-7B (offline) to read the same image.
- **Merge:** LLM extractions tagged as `source_method: "llm-vision"` in SourceSpans.
- **Fallback hierarchy:**
  1. Ollama + LLaVA-7B (default, offline, 4.5 GB model).
  2. Cloud API (Claude Haiku or GPT-4-Vision) if `LLM_FALLBACK_ENABLED=true`.
  3. Missing field (if both fail).

#### 5. Review UI (Sprint 5)
**Updated badges:**
- Old: `extracted`, `user_entered`, `missing`
- New: `OCR` (blue), `LLM Vision` (purple), `User Entered` (green), `Missing` (red)

Badges now show data source, giving users full transparency.

#### 6. High-Level Flow Diagram
Updated to show:
- Rotation detection in Ingest Job.
- LLM Vision fallback decision point in Structure Job.
- Source attribution in both paths.

---

## Key Design Principles

### "Source-of-Truth" Still Upheld
- ✅ **No inference:** LLM reads visible text; doesn't guess/infer values.
- ✅ **Same media:** Both OCR and LLM parse the uploaded image.
- ✅ **Audit trail:** `source_method` field tracks which reader extracted each field.
- ✅ **User control:** Review UI shows source; users can edit/clear any field.

### Privacy-First, Offline Default
- ✅ **Offline by default:** Ollama + LLaVA-7B runs locally (~8 GB RAM, 4.5 GB disk).
- ✅ **Optional cloud:** Cloud APIs (Claude, OpenAI) available only if `LLM_FALLBACK_ENABLED=true`.
- ✅ **Configurable:** `LLM_FALLBACK_PROVIDER` and `LLM_FALLBACK_ENABLED` env vars control behavior.

### Why This Matters
**Problem:** PaddleOCR fails on rotated/skewed/low-contrast images → users stuck with missing fields → must manually re-enter.

**Solution:**
1. Auto-correct rotation (proven 99% success).
2. If OCR still can't extract critical fields, use LLM vision (better visual reader).
3. Both methods read visible media; no guessing.
4. User always sees source and can override.

**Impact:**
- Estimated 90%+ recipes extract title + ≥1 ingredient + ≥1 step automatically.
- Users spend more time reviewing/verifying, less time re-entering.
- Offline-first, no API dependency (unless opted-in).

---

## Implementation Roadmap

| Sprint | Focus | Key Tickets |
|--------|-------|------------|
| **2** | Rotation detection + OCR | 2.1, 2.2 (orientation detection) |
| **3** | Structure + LLM fallback | 3.1 (LLM fallback), 3.2 (normalize) |
| **4** | CRUD + FieldStatus tracking | 4.1, 4.2, 4.3 (include source_method) |
| **5** | Review UI + badges | 5.1, 5.2 (OCR/LLM/User badges) |
| **6** | Pantry & Match | 6.1, 6.2 (no changes to OCR/LLM) |

---

## Configuration

### Environment Variables (Recommended Defaults)

```bash
# OCR & Preprocessing
TESSERACT_ENABLED=true           # Orientation detection (required)
TESSERACT_DPI=300                # Scan resolution
TESSERACT_CONFIDENCE_THRESHOLD=3 # Confidence cutoff for rotation vote

# LLM Vision Fallback
LLM_FALLBACK_ENABLED=true                        # Enable LLM fallback (default: true)
LLM_FALLBACK_PROVIDER=ollama                     # Provider: ollama|claude|openai (default: ollama)
OLLAMA_HOST=http://localhost:11434               # Ollama server URL (offline)
OLLAMA_MODEL=llava:7b                            # Model (4.5 GB, downloads on first use)
LLM_FALLBACK_TRIGGER_THRESHOLD=3                 # Trigger if >N fields missing (default: 3)

# Cloud API (optional, if LLM_FALLBACK_PROVIDER != ollama)
ANTHROPIC_API_KEY=sk-...                         # Claude API key
OPENAI_API_KEY=sk-...                            # OpenAI API key
```

### System Requirements

| Component | Required | Optional |
|-----------|----------|----------|
| Tesseract OCR | ✅ Yes (orientation) | — |
| ImageMagick | ✅ Yes (rotation) | — |
| Ollama + LLaVA | ⭕ Recommended | Cloud fallback |
| PaddleOCR | ✅ Yes (text extraction) | — |
| PostgreSQL | ✅ Yes | — |
| Redis | ✅ Yes (job queue) | — |

---

## Backward Compatibility

- ✅ No deleted files.
- ✅ SourceSpan schema extended (added `source_method`), not broken.
- ✅ Existing recipes have `source_method: "ocr"` (inferred if missing).
- ✅ Review UI badges updated; old badge style not referenced in new code.
- ✅ Validation logic unchanged (title + ≥1 ingredient + ≥1 step).

---

## Success Metrics (End of V1)

- ✅ **Extraction rate:** 90%+ recipes extract title + ≥1 ingredient + ≥1 step without manual re-entry.
- ✅ **Rotation handling:** Rotated images auto-corrected before OCR; logs show correction.
- ✅ **LLM trigger:** LLM fallback invoked only when OCR insufficient; not default path.
- ✅ **Source tracking:** Every field shows source badge (OCR, LLM Vision, User Entered, or Missing).
- ✅ **Privacy:** Ollama offline by default; cloud APIs optional and logged.
- ✅ **Verification gating:** Can only mark verified if title + ≥1 ingredient + ≥1 step present.

---

## References

- **Carl Pearson's digitization method:** https://carlpearson.net/post/20240102-digitize-recipe/ (rotation detection inspiration)
- **Tesseract orientation detection:** https://github.com/tesseract-ocr/tesseract/wiki/ImproveQuality
- **Ollama:** https://github.com/ollama/ollama
- **LLaVA:** https://github.com/haotian-liu/LLaVA (NeurIPS 2023, Apache 2.0)
- **RecipeNow SPEC.md:** The canonical source (updated)

