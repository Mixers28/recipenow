# Offline LLM Strategy for RecipeNow

**Status:** Strategic Proposal  
**Date:** January 25, 2026  
**Audience:** Architects, Coder Agents  
**Priority:** HIGH (better than cloud APIs for self-hosted use case)

---

## Executive Summary

RecipeNow should use **Ollama + LLaVA** (offline multimodal LLM) instead of cloud-based LLMs (Claude/OpenAI). This approach:

✅ **Preserves privacy:** Images never leave the server  
✅ **Eliminates API costs:** $0 per recipe (one-time model download)  
✅ **Zero cloud dependency:** Works offline, on Railway, or local deployment  
✅ **Flexible fallback:** Runs alongside OCR + parser as confidence fallback  
✅ **2-5 second latency** (acceptable for background jobs)  

---

## Offline LLM Landscape (2026)

### Vision-Capable Models

| Model | Size | VRAM | Speed | Quality | Licensing |
|-------|------|------|-------|---------|-----------|
| **LLaVA-1.5-7B** | 4.5 GB | 8 GB | ~5-8s | 7.5/10 | Apache 2.0 ✅ |
| **Moondream 2** | 829 MB | 3 GB | ~2s | 6/10 (fast) | Apache 2.0 ✅ |
| **Qwen-VL-Chat-7B** | 13 GB | 16 GB | ~5-10s | 8/10 | Alibaba License ⚠️ |
| **LLaMA 3.2-Vision-11B** | 7.9 GB | 12 GB | ~5s | 8/10 | Llama Community ✅ |
| GPT-4-Vision (cloud) | — | — | ~3-5s | 9.5/10 | $0.01/image ❌ |
| Claude 3 Haiku (cloud) | — | — | ~2-3s | 8/10 | $0.003/image ❌ |

**Recommendation for RecipeNow:** **LLaVA-1.5-7B** (best balance of speed, size, quality, licensing)

---

## Current Architecture vs. Offline LLM

### Current Flow (Deterministic Parser Only)
```
Recipe Image 
  ↓
PaddleOCR (text + bbox)
  ↓
RecipeParser (keyword heuristics)
  ↓
Draft Recipe (often missing fields)
  ↓
User Review UI (manual correction)
```

**Gap:** No visual context; parser can't infer from layout

### Proposed Flow (Ollama + LLaVA Hybrid)
```
Recipe Image 
  ↓
PaddleOCR (text + bbox)
  ↓
RecipeParser (keyword heuristics)
  ↓
Check if missing critical fields (title, ingredients, steps)?
  ├─ NO missing → Use OCR + parsed recipe ✅
  └─ YES → Fallback to LLaVA-Vision
       ↓
     LLaVA-7B (multimodal extraction)
       ↓
     Merge LLM results with OCR (LLM source tag)
       ↓
Draft Recipe (complete or annotated)
  ↓
User Review UI (source badges: ocr, llm-vision, manual)
```

**Benefit:** Automatic fallback; user always sees field source

---

## Offline LLM Deployment Options

### Option 1: Ollama Service (RECOMMENDED)
**Best for:** Self-hosted, Docker-friendly, easy model management

```yaml
# Add to docker-compose.yml
ollama:
  image: ollama/ollama:latest
  container_name: recipenow-ollama
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama
  environment:
    OLLAMA_HOST: 0.0.0.0:11434
    # Optional: GPU support (nvidia-docker)
    # OLLAMA_CUDA_COMPUTE_CAPABILITY: "8.0"  # Adjust for your GPU
```

**Startup:**
```bash
# First time: pull the model (takes ~3-5 min on good connection)
ollama pull llava:7b

# Service auto-loads models on /api requests
# REST API available at http://localhost:11434
```

**Cost:** Model download ~4.5 GB (one-time)

---

### Option 2: llama.cpp (For CPU-Only, Quantized)
**Best for:** Minimal resources, constrained environments

```bash
# One-time download & quantization
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
make

# Download GGUF model
wget https://huggingface.co/models/llava/llava-1.5-7b-gguf/...

# Run server
./server -m llava-1.5-7b-q4.gguf --port 8081
```

**Pros:** CPU-only, 2-3 GB quantized, slower (~10-15s per image)  
**Cons:** Requires manual setup; less convenient than Ollama

---

## RecipeNow Integration Plan

### Phase 1: Ollama Infrastructure (2-3 days)
**Goal:** Get Ollama running alongside API/Worker

**Tasks:**
1. Update `docker-compose.yml` to add Ollama service
2. Add `ollama-python` client to `apps/api/requirements.txt`
3. Create `apps/api/services/llm_fallback.py` (Ollama-based extractor)
4. Test local: `ollama run llava:7b`

**Implementation:**

**File:** `infra/docker-compose.yml` (add service)
```yaml
ollama:
  image: ollama/ollama:latest
  container_name: recipenow-ollama
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama
  environment:
    OLLAMA_HOST: 0.0.0.0:11434
  # Optional: GPU support for Railway
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]

volumes:
  ollama_data:
```

**File:** `apps/api/requirements.txt` (add package)
```
ollama==0.3.12  # Python Ollama client
```

**File:** `apps/api/services/llm_fallback.py` (new)
```python
"""
Fallback vision LLM extraction using Ollama (offline).
Only triggered when RecipeParser leaves too many fields missing.
"""
import json
import logging
from typing import Optional
import base64
from pathlib import Path

logger = logging.getLogger(__name__)


class OfflineLLMFallback:
    """Extract recipe using LLaVA (offline, via Ollama)."""
    
    SCHEMA = {
        "title": "string or null",
        "servings": "integer or null",
        "times": {
            "prep_min": "integer or null",
            "cook_min": "integer or null",
            "total_min": "integer or null"
        },
        "ingredients": [
            {
                "original_text": "exactly as written in image",
                "name": "cleaned ingredient name",
                "quantity": "numeric (1, 0.5, 2.5) or null",
                "unit": "tsp, cup, g, oz, etc. or null"
            }
        ],
        "instructions": ["step 1", "step 2", "..."],
        "notes": ["note 1", "..."]
    }
    
    PROMPT_TEMPLATE = """Extract recipe data from this image.
Return ONLY valid JSON (no markdown, no explanation).

Schema:
{schema}

Rules:
- If unreadable or missing, use null
- Quantities must be numeric (2, 0.5) or null
- Do not invent values
- Keep ingredient original_text exactly as written
"""
    
    def __init__(self, ollama_host: str = "http://localhost:11434", model: str = "llava:7b"):
        """
        Initialize Ollama client.
        
        Args:
            ollama_host: Ollama server URL
            model: Model name (default: llava:7b)
        """
        try:
            from ollama import Client
        except ImportError:
            raise ImportError("Install ollama-python: pip install ollama")
        
        self.client = Client(host=ollama_host)
        self.model = model
        self.host = ollama_host
    
    def extract_from_image(self, image_path: str) -> dict:
        """
        Extract recipe using LLaVA vision model.
        
        Args:
            image_path: Path to recipe image
        
        Returns:
            dict with recipe fields (or empty if failed)
        """
        try:
            # Read image
            with open(image_path, 'rb') as f:
                image_data = base64.standard_b64encode(f.read()).decode('utf-8')
            
            # Build prompt
            prompt = self.PROMPT_TEMPLATE.format(
                schema=json.dumps(self.SCHEMA, indent=2)
            )
            
            # Call Ollama
            logger.info(f"Calling {self.model} for recipe extraction...")
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                images=[image_data],
                stream=False,
                options={
                    "temperature": 0.1,  # Low temp for structured output
                    "num_predict": 1024,
                    "top_k": 40,
                    "top_p": 0.9,
                }
            )
            
            result_text = response.get("response", "")
            logger.info(f"LLM returned: {result_text[:200]}...")
            
            # Parse JSON
            # Try to extract JSON from response (handle markdown wrapping)
            if "```json" in result_text:
                json_str = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                json_str = result_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = result_text.strip()
            
            return json.loads(json_str)
        
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}", exc_info=True)
            return {}
    
    def is_available(self) -> bool:
        """Check if Ollama server is running and model is loaded."""
        try:
            tags = self.client.list()
            model_names = [m.get("name", "") for m in tags.get("models", [])]
            return any(self.model in name for name in model_names)
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False


def get_llm_fallback(ollama_host: str = "http://localhost:11434") -> Optional[OfflineLLMFallback]:
    """Factory: return fallback if available, else None."""
    try:
        fallback = OfflineLLMFallback(ollama_host=ollama_host)
        if fallback.is_available():
            return fallback
        else:
            logger.warning("Ollama/LLaVA not available; skipping LLM fallback")
            return None
    except Exception as e:
        logger.warning(f"Could not init LLM fallback: {e}")
        return None
```

---

### Phase 2: Structure Job Integration (1-2 days)
**Goal:** Trigger LLM fallback when parser leaves too many fields missing

**File:** `apps/api/worker/jobs.py` (update `structure_recipe`)
```python
from services.llm_fallback import get_llm_fallback
import os

def structure_recipe(ingest_id: UUID, asset_id: UUID):
    """Parse OCRLines → Recipe + spans, with LLM fallback."""
    
    ocr_lines = get_ocr_lines(asset_id)
    parser = RecipeParser()
    recipe_draft = parser.parse(ocr_lines, asset_id)
    
    # Count missing fields
    statuses = recipe_draft.get("field_statuses", [])
    missing_count = sum(1 for s in statuses if s["status"] == "missing")
    has_title = recipe_draft["recipe"].get("title") is not None
    has_ingredients = len(recipe_draft["recipe"].get("ingredients", [])) > 0
    has_steps = len(recipe_draft["recipe"].get("steps", [])) > 0
    
    # Trigger LLM fallback if critical fields missing
    if not has_title or not has_ingredients or not has_steps:
        logger.info(
            f"Asset {asset_id}: Critical fields missing (title={has_title}, "
            f"ingredients={has_ingredients}, steps={has_steps}); trying LLM fallback"
        )
        
        fallback = get_llm_fallback(
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434")
        )
        
        if fallback:
            image_path = get_asset_image_path(asset_id)
            llm_result = fallback.extract_from_image(image_path)
            
            if llm_result:
                # Merge LLM results (with "llm-vision" source tag)
                recipe_draft = merge_llm_into_recipe(
                    recipe_draft, llm_result, asset_id
                )
                logger.info(f"LLM fallback succeeded for asset {asset_id}")
            else:
                logger.warning(f"LLM fallback returned empty for asset {asset_id}")
        else:
            logger.info("Ollama/LLaVA not available; skipping fallback")
    
    # Save recipe + spans + statuses
    save_recipe(ingest_id, recipe_draft)
```

---

### Phase 3: UI Source Badges (1-2 days)
**Goal:** Show users which fields came from OCR vs. LLM vs. manual edit

**File:** `apps/web/components/RecipeForm.tsx` (update field rendering)
```tsx
interface FieldMetadata {
  value: string | null;
  source: "ocr" | "llm-vision" | "user-edit" | "missing";
  confidence?: number;
  extracted_text?: string;
}

export function RecipeFieldWithBadge({ 
  fieldPath, 
  metadata, 
  onEdit 
}: {
  fieldPath: string;
  metadata: FieldMetadata;
  onEdit: (value: string) => void;
}) {
  const badgeColor = {
    "ocr": "bg-blue-100 text-blue-800",
    "llm-vision": "bg-purple-100 text-purple-800",
    "user-edit": "bg-green-100 text-green-800",
    "missing": "bg-red-100 text-red-800",
  }[metadata.source];
  
  return (
    <div className="relative">
      <input
        type="text"
        value={metadata.value || ""}
        onChange={(e) => onEdit(e.target.value)}
        placeholder="(missing)"
        className="w-full px-3 py-2 border rounded"
      />
      <span className={`absolute top-2 right-2 px-2 py-1 text-xs font-semibold rounded ${badgeColor}`}>
        {metadata.source === "llm-vision" ? "LLM Vision" : metadata.source.toUpperCase()}
        {metadata.confidence && ` (${(metadata.confidence * 100).toFixed(0)}%)`}
      </span>
    </div>
  );
}
```

---

## Resource Requirements

### Ollama + LLaVA-7B

| Resource | Requirement | Notes |
|----------|-------------|-------|
| **Model Size** | 4.5 GB | Download once; persists in volume |
| **VRAM** | 8 GB min, 12 GB recommended | Shared with API/worker if on same node |
| **Inference Time** | 2-8s per image | Depends on image size, CPU/GPU |
| **Container Disk** | 50 GB + model storage | Image: 2 GB, model: 4.5 GB |
| **Network (startup)** | 4.5 GB download | One-time on docker-compose up |

### Railway Deployment
- ✅ Ollama + LLaVA-7B fits in Railway's **GPU plan** (e.g., RTX 4090, 24 GB VRAM)
- ⚠️ Without GPU: ~10-15s per image (acceptable for background jobs)
- 💾 Use Railway's **persistent volume** for model cache

---

## Cost-Benefit Analysis

| Approach | Cost/Recipe | Privacy | Latency | Effort | Notes |
|----------|------------|---------|---------|--------|-------|
| **Ollama LLaVA-7B** | $0 | 100% | 2-8s | Medium | ✅ Recommended |
| Claude 3 Haiku | $0.003 | 0% | 1-2s | Low | Cloud API, ~$0.50/month for 150 recipes |
| GPT-4-Vision | $0.01 | 0% | 1-3s | Low | Cloud, ~$1.50/month for 150 recipes |
| Tesseract only | $0 | 100% | 0.5s | Low | Limited to orientation; no extraction |

---

## Rollout Plan

### Sprint Timeline

**Sprint 1 (2-3 days):** Ollama Infrastructure
- [ ] Add Ollama to docker-compose.yml
- [ ] Test local: `docker-compose up ollama`
- [ ] Verify `curl http://localhost:11434/api/tags` works
- [ ] Document model download

**Sprint 2 (1-2 days):** LLM Fallback Service
- [ ] Create `llm_fallback.py` with OfflineLLMFallback
- [ ] Add fallback logic to structure_recipe job
- [ ] Test with sample recipe images
- [ ] Log source attribution (ocr vs. llm-vision)

**Sprint 3 (1-2 days):** UI Source Badges
- [ ] Update RecipeForm to show source badges
- [ ] Test review UI with different sources
- [ ] Verify badge styling (ocr=blue, llm=purple, manual=green)

**Total:** 4-7 days

---

## Success Criteria

✅ Ollama service runs in docker-compose (GPU or CPU mode)  
✅ LLaVA-7B model pulls automatically on first startup  
✅ Structure job triggers fallback when >2 critical fields missing  
✅ LLM results merge cleanly with OCR results  
✅ Review UI shows source badges (OCR, LLM, Manual)  
✅ Zero privacy regression (all processing local)  
✅ <5 min for typical recipe (parallel OCR + LLM if needed)  

---

## Fallback to Cloud (Optional, Phase 4)

If offline LLM is unavailable (e.g., user opts-out, Railway memory constrained):

```python
# apps/api/config.py
OFFLINE_LLM_ENABLED = os.getenv("OFFLINE_LLM_ENABLED", "true").lower() == "true"
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", None)

# In structure_recipe job:
if not has_critical_fields:
    if OFFLINE_LLM_ENABLED:
        fallback = get_llm_fallback(...)  # Try Ollama first
    
    if not fallback or not fallback.is_available():
        if CLAUDE_API_KEY:
            fallback = CloudLLMFallback(api_key=CLAUDE_API_KEY)  # Fallback to Claude
```

This preserves the option for cloud-based fallback without requiring it.

---

## References

- **Ollama:** https://github.com/ollama/ollama
- **LLaVA:** https://github.com/haotian-liu/LLaVA (NeurIPS 2023, Apache 2.0)
- **LLaVA Model Zoo:** https://huggingface.co/collections/lmms-lab/llava-next-6623288e2d61edba3ddbf5ff
- **Moondream 2:** https://github.com/vikhyat/moondream (very fast, ~830 MB)
- **llama.cpp:** https://github.com/ggml-org/llama.cpp (CPU inference)
- **RecipeNow SPEC.md:** Privacy-first, self-hosted mandate

