# OCR Enhancement Plan — Integrating Pearson Method Insights

**Date:** January 25, 2026  
**Status:** Strategic Proposal  
**Audience:** Architects, Coder Agents, QA

---

## Executive Summary

Carl Pearson's blog post demonstrates a **multi-stage pipeline** (scan → split → rotate detect → vision extraction) that achieves high-quality recipe extraction. RecipeNow now uses the **OpenAI Vision API as the primary extractor** with OCR supplying bbox evidence. This plan focuses on **OCR reliability improvements** that strengthen provenance.

1. **Orientation Detection w/ Confidence Voting** (Tesseract-based)
2. **Vision API Extraction (primary, OpenAI)** with OCR evidence

This doc focuses on OCR accuracy improvements in a hosted-vision architecture.

**Note:** Any legacy "offline LLM" or "cloud fallback" sections below are deprecated and kept for historical context only.

---

## Current State Analysis

### RecipeNow Strengths
- ✅ Interactive review workflow (users control final truth)
- ✅ Privacy-first with hosted vision extraction (OpenAI Vision API)
- ✅ Provenance tracking per field (source pixels → spans)
- ✅ Stateful field editing (missing, ambiguous, verified)

### RecipeNow Gaps (vs. Pearson Method)
- ❌ **No rotation detection:** PaddleOCR fails on skewed/rotated images
- ❌ **No confidence voting:** Single-pass OCR can miss orientation errors
- ❌ **No visual context:** Deterministic parser can't infer quantities from layout
- ❌ **No fallback mechanism:** Ambiguous/complex recipes stuck at "missing"
- ❌ **Railway deployment broken:** System deps (libgl1, libglib2.0-0) missing in API/worker images

---

## Recommended Enhancements

### Phase 1: Fix Immediate OCR Pipeline (URGENT)
**Goal:** Get Railway OCR working; handle rotation better  
**Timeline:** 1-2 sprints  
**Owner:** Coder Agent

#### 1.1 System Dependencies (Docker)
**Action:** Update Dockerfile for `apps/api` and `apps/worker`

```dockerfile
# apps/api/Dockerfile + apps/worker/Dockerfile
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    tesseract-ocr \
    ghostscript \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*
```

**Why:** PaddleOCR + Tesseract + GhostScript system libs needed for image processing.

#### 1.2 Rotation Detection (Tesseract-Based)
**Action:** Add preprocessing step before PaddleOCR

**File:** `apps/api/services/ocr.py` → new `OCRService.preprocess_image()`

```python
def preprocess_image(self, image_path: str) -> tuple[str, int]:
    """
    Detect image orientation using Tesseract + voting.
    Returns: (processed_image_path, rotation_degrees)
    """
    import subprocess
    import tempfile
    from pathlib import Path
    
    # Run Tesseract with 3 thresholding methods (vote on best rotation)
    votes = {}
    for method in [0, 1, 2]:
        try:
            result = subprocess.run(
                ["tesseract", "--dpi", "300", 
                 f"-c", f"thresholding_method={method}",
                 image_path, "stdout", "--psm", "0"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse Tesseract output for Orientation + confidence
            for line in result.stdout.split('\n'):
                if 'Rotate:' in line:
                    rotation = int(line.split()[-1])
                    if 'Orientation confidence:' in result.stdout:
                        conf_line = [l for l in result.stdout.split('\n') 
                                    if 'Orientation confidence:' in l][0]
                        confidence = float(conf_line.split()[-1])
                        if confidence > 3:  # Confidence threshold
                            votes[rotation] = votes.get(rotation, 0) + 1
        except Exception as e:
            logger.warning(f"Tesseract method {method} failed: {e}")
    
    # Majority vote on rotation
    if not votes:
        return image_path, 0  # No confident detection
    
    best_rotation = max(votes, key=votes.get)
    logger.info(f"Detected rotation: {best_rotation}° (votes: {votes})")
    
    # Apply rotation using ImageMagick
    rotated_path = str(Path(image_path).with_stem(f"{Path(image_path).stem}_rotated"))
    subprocess.run(
        ["convert", "-rotate", str(best_rotation), image_path, rotated_path],
        check=True
    )
    
    return rotated_path, best_rotation
```

**Integration in OCRService:**
```python
def extract_text(self, file_data: BinaryIO, asset_type: str = "image") -> List[OCRLineData]:
    """Extract text with preprocessing."""
    # ... existing temp file handling ...
    
    # NEW: Preprocess for rotation
    processed_path, rotation = self.preprocess_image(tmp_path)
    
    # Run OCR on corrected image
    result = self.ocr.ocr(processed_path, cls=True)
    
    # Log rotation for audit/debugging
    logger.info(f"OCR processed image with {rotation}° rotation correction")
    
    # ... existing parsing ...
```

**Trade-offs:**
- ✅ Self-hosted, no API cost
- ✅ Handles 99% of rotation cases (proven in Pearson's 152 recipes)
- ❌ Slower (~5-10s per image for Tesseract voting)
- ❌ Requires Tesseract system binary

---

### Phase 2: Vision LLM Fallback (OPTIONAL)
**Goal:** Handle ambiguous/complex layouts; structured extraction as fallback  
**Timeline:** 2-3 sprints (post-Phase-1)  
**Owner:** Coder + Architecture  
**Cost:** ~$0.03–0.05 per image (Claude 3 Haiku or GPT-4 Mini)

#### 2.1 Conditional LLM Extraction
**Trigger:** When parser produces `field_status == "ambiguous"` or too many `missing` fields

**File:** `apps/api/services/parser.py` → new `LLMFallback` class

```python
class LLMFallback:
    """Vision LLM extraction when deterministic parser fails."""
    
    SCHEMA = {
        "name": "Recipe name",
        "servings": "Number of servings (integer or null)",
        "times": {
            "prep_min": "Prep time in minutes (integer or null)",
            "cook_min": "Cook time in minutes (integer or null)",
            "total_min": "Total time in minutes (integer or null)"
        },
        "ingredients": [
            {
                "name": "Ingredient name",
                "quantity": "Numeric quantity (e.g., 2, 1/2) or null",
                "unit": "Unit (e.g., cup, tsp, g) or null",
                "notes": "Optional prep notes"
            }
        ],
        "instructions": ["Step 1", "Step 2", "..."],
        "notes": ["Note 1", "..."]
    }
    
    def extract_from_image(self, image_path: str, model: str = "claude-3-haiku") -> dict:
        """
        Use vision LLM to extract recipe.
        
        Args:
            image_path: Path to recipe image (JPEG/PNG, <= 768x2000px)
            model: "claude-3-haiku" (cheaper) or "gpt-4-vision" (better)
        
        Returns:
            dict matching SCHEMA, or empty if LLM fails
        """
        import base64
        import json
        from anthropic import Anthropic  # or OpenAI
        
        # Read image
        with open(image_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')
        
        # Prompt
        prompt = f"""Extract recipe data from the image.
        
        Return ONLY valid JSON matching this schema (no markdown, no explanation):
        {json.dumps(self.SCHEMA, indent=2)}
        
        Rules:
        - If a value is missing or unreadable, use null.
        - Convert non-ASCII to ASCII (e.g., "é" → "e").
        - Quantities must be numeric (2, 1/2, 0.5) or null.
        - Do not invent or guess values.
        """
        
        try:
            if model.startswith("claude"):
                client = Anthropic()
                msg = client.messages.create(
                    model=model,
                    max_tokens=1024,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_data
                                    }
                                },
                                {"type": "text", "text": prompt}
                            ]
                        }
                    ]
                )
                result_text = msg.content[0].text
            else:
                # OpenAI fallback
                from openai import OpenAI
                client = OpenAI()
                msg = client.chat.completions.create(
                    model=model,
                    max_tokens=1024,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_data}"
                                    }
                                }
                            ]
                        }
                    ]
                )
                result_text = msg.choices[0].message.content
            
            return json.loads(result_text)
        
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {}
```

**Integration in Structure Job:**
```python
# apps/api/worker/jobs.py
def structure_recipe(ingest_id: UUID, asset_id: UUID):
    """Parse OCRLines → Recipe + spans."""
    
    ocr_lines = get_ocr_lines(asset_id)
    parser = RecipeParser()
    recipe_draft = parser.parse(ocr_lines, asset_id)
    
    # Count missing/ambiguous fields
    statuses = recipe_draft.get("field_statuses", [])
    missing_count = sum(1 for s in statuses if s["status"] == "missing")
    
    # If too many missing, try LLM fallback
    if missing_count > 3:
        logger.info(f"Too many missing fields ({missing_count}); trying LLM fallback")
        fallback = LLMFallback()
        
        # Get image from asset
        image_path = get_asset_image_path(asset_id)
        llm_result = fallback.extract_from_image(image_path, model="claude-3-haiku")
        
        # Merge LLM results into recipe_draft (with LLM attribution in spans)
        recipe_draft = merge_llm_results(recipe_draft, llm_result, asset_id, "llm-fallback")
    
    # Save recipe + spans + statuses
    save_recipe(ingest_id, recipe_draft)
```

**Trade-offs:**
- ✅ Handles complex/ambiguous layouts
- ✅ Structured output (no post-processing needed)
- ✅ Cheap: ~$0.03–0.05 per recipe (Haiku) or $0.10+ (GPT-4-Vision)
- ❌ Cloud dependency (requires API key)
- ❌ Privacy: images sent to third-party
- ❌ Slower: network latency
- **Mitigation:** Use only as **fallback** (not default); log LLM usage; allow users to disable

---

### Phase 3: Hybrid Review Workflow
**Goal:** Give users confidence in which fields came from OCR vs. LLM vs. manual edit  
**Timeline:** 1 sprint (post-Phase-2)  
**UI Update:** Badge each field with source tag

**File:** `apps/web/components/RecipeForm.tsx`

```tsx
<FieldWithProvenance
  fieldPath="title"
  value={recipe.title}
  source="ocr"  // or "llm-fallback" or "user-edit"
  confidence={0.87}
  onEdit={handleFieldChange}
/>
```

---

## Implementation Priority

| Phase | Action | Self-Hosted? | Cost/Effort | Impact | Owner |
|-------|--------|-------------|------------|--------|-------|
| **NOW (Urgent)** | Fix Docker deps; add Tesseract rotation detection | ✅ Yes | Low / 2-3 days | Unblocks OCR on Railway | Coder |
| **Phase 1** | Rotation detection + Tesseract voting | ✅ Yes | Medium / 3-5 days | 99% rotation fix rate | Coder |
| **Phase 2** | LLM fallback (Claude/GPT-4-Vision) | ❌ No (optional) | Medium / 1 week | Handles ambiguous recipes | Coder + Arch |
| **Phase 3** | Source tagging in Review UI | ✅ Yes | Low / 2-3 days | User confidence + transparency | Frontend |

---

## Open Questions

1. **LLM Fallback—Claude or OpenAI?**
   - Recommendation: **Claude 3 Haiku** (cheaper, offline vision model coming Q2 2025)
   - Resolution: Run Context7 query before implementation

2. **Rotation Detection—Tesseract or alternative?**
   - Tesseract proven in Pearson's 152 recipes; recommendation: **keep Tesseract + voting**
   - Cost: ~5-10s per image (acceptable for background job)

3. **Privacy concern: LLM fallback sends images to API?**
   - Mitigation: Make it **opt-in per-recipe** or **disabled by default**
   - Allow self-hosted users to skip LLM entirely

4. **Where to run Tesseract?**
   - Recommendation: In **worker** (background job), not in API (faster)

---

## Success Criteria

- ✅ OCR pipeline stable on Railway (no init errors)
- ✅ 90%+ recipes parsed correctly without manual intervention
- ✅ Rotated/skewed images corrected automatically
- ✅ Field statuses reflect confidence (missing, extracted, verified)
- ✅ Users can see which fields came from OCR vs. LLM vs. manual edit
- ✅ Zero privacy regression (LLM optional, self-hosted by default)

---

## References

- **Carl Pearson's Method:** https://carlpearson.net/post/20240102-digitize-recipe/
- **Tesseract Orientation Detection:** https://github.com/tesseract-ocr/tesseract/wiki/ImproveQuality
- **PaddleOCR:** https://github.com/PaddlePaddle/PaddleOCR
- **Claude Vision API:** https://docs.anthropic.com/en/docs/vision/vision-models
- **RecipeNow SPEC.md:** `docs/SPEC.md`
