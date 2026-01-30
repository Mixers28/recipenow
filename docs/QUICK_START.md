# Quick Start - Vision-Primary Extraction

## TL;DR

✅ **Implementation complete.** OCR pipeline with rotation detection + OpenAI Vision extraction (primary).

**Start testing with:**
```bash
cd apps/api
python -m pytest tests/ -v
```

---

## 60-Second Overview

### What Changed
1. **OCR now detects & corrects rotated images** (Tesseract voting)
2. **Vision extraction is primary** (OpenAI Vision API with OCR evidence)
3. **Tracked extraction source** (source_method: "ocr" or "vision-api")
4. **3-stage job pipeline** (ingest → extract → normalize)

### Architecture
```
Upload → [Rotation Detection] → [OCR] → [Vision Extract]
           (Tesseract PSM 0)     (PaddleOCR)     (OpenAI)
                                    ↓
                                [Spans]
                                    ↓
                               [Normalize] → [Ready]
```

### Files Changed
- `apps/api/services/ocr.py` - Rotation detection
- `apps/api/services/llm_vision.py` - Vision extraction (OpenAI)
- `apps/api/worker/jobs.py` - Job pipeline (ingest → extract → normalize)
- `apps/api/db/models.py` - Added source_method field
- `infra/migrations/002_add_source_method.sql` - DB schema

---

## Installation (5 Minutes)

### 1. System Dependencies
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr imagemagick

# macOS
brew install tesseract imagemagick

# Verify
tesseract --version && convert --version
```

### 2. Python Dependencies
```bash
cd apps/api
pip install -r requirements.txt
```

### 3. Database Migration
```bash
# Run migration to add source_method column
psql -U postgres -d recipenow -f infra/migrations/002_add_source_method.sql
```

## Testing (10 Minutes)

### Quick Test
```bash
# Test OCR with rotation detection
python -c "
from apps.api.services.ocr import get_ocr_service
from io import BytesIO

service = get_ocr_service(use_gpu=False)
with open('tests/fixtures/recipe_90deg.jpg', 'rb') as f:
    lines = service.extract_text(BytesIO(f.read()), 'image')
print(f'✓ Extracted {len(lines)} lines (rotation detection worked)')
"

# Test Vision extraction (OpenAI)
python -c "
from apps.api.services.llm_vision import get_llm_vision_service

service = get_llm_vision_service()
with open('tests/fixtures/recipe_sparse.jpg', 'rb') as f:
    result = service.extract_recipe_from_image(f.read())
print(f'✓ Vision returned: {list(result.keys())}')
"
```

### Full Test Suite
```bash
cd apps/api
pytest tests/ -v

# Run specific test
pytest tests/test_ocr_rotation.py -v
pytest tests/test_llm_vision.py -v
```

---

## Configuration

### Environment Variables (in .env or deployment config)
```bash
# Rotation detection
ENABLE_ROTATION_DETECTION=true

# Vision API (OpenAI)
OPENAI_API_KEY=sk-...
VISION_MODEL=gpt-4o-mini
VISION_MAX_OUTPUT_TOKENS=1024
VISION_STRICT_JSON=true
```

---

## Common Tasks

### Test Rotation Detection
```bash
python -c "
from apps.api.services.ocr import OCRService

service = OCRService(use_gpu=False, enable_rotation_detection=True)

# Try each angle
for angle in [0, 90, 180, 270]:
    path = f'tests/fixtures/recipe_{angle}deg.jpg'
    result, detected = service._detect_and_correct_rotation(path)
    print(f'{angle}° → detected {detected}°')
"
```

### Test Vision Extraction
```bash
python -c "
from apps.api.services.llm_vision import get_llm_vision_service

service = get_llm_vision_service()
with open('tests/fixtures/recipe.jpg', 'rb') as f:
    result = service.extract_recipe_from_image(f.read())
    
print('Extracted:')
print(f'  Title: {result.get(\"title\")}')
print(f'  Ingredients: {len(result.get(\"ingredients\", []))}')
print(f'  Steps: {len(result.get(\"steps\", []))}')
"
```

### Test Job Pipeline
```python
import asyncio
from apps.api.worker.jobs import ingest_recipe, extract_recipe

async def test():
    with open('tests/fixtures/recipe.jpg', 'rb') as f:
        file_data = f.read()
    
    # Ingest
    ingest = await ingest_recipe('asset-1', 'user-1', file_data)
    print(f'Ingest: {ingest[\"status\"]} ({ingest[\"ocr_line_count\"]} lines)')
    
    # Extract (vision-primary)
    extract = await extract_recipe('asset-1', 'user-1')
    print(f'Extract: {extract[\"status\"]} (recipe {extract[\"recipe_id\"]})')
    
    # Normalize
    from apps.api.worker.jobs import normalize_recipe
    normalize = await normalize_recipe(extract['recipe_id'], 'user-1')
    print(f'Normalize: {normalize[\"status\"]} ({len(normalize[\"quality_issues\"])} issues)')

asyncio.run(test())
```

### Debug Rotation Detection
```bash
# Enable debug logging
export LOGLEVEL=DEBUG

# Run OCR with detailed output
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)

from apps.api.services.ocr import OCRService
service = OCRService(use_gpu=False, enable_rotation_detection=True)
service._detect_and_correct_rotation('test.jpg')
"
```

---

## Troubleshooting

### "tesseract: command not found"
```bash
# Install Tesseract
sudo apt-get install tesseract-ocr  # Ubuntu
brew install tesseract              # macOS
```

### "convert: command not found"
```bash
# Install ImageMagick
sudo apt-get install imagemagick   # Ubuntu
brew install imagemagick            # macOS
```

### "Vision response parsing failed"
```bash
# Verify OpenAI env vars and strict JSON settings
export OPENAI_API_KEY=...
export VISION_MODEL=gpt-4o-mini
export VISION_STRICT_JSON=true
```

### OCR returns empty
- Check image quality (too blurry?)
- Verify image is actual recipe (not graphics)
- Try with rotation detection: enable in config
- Verify vision extraction runs after OCR

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `apps/api/services/ocr.py` | OCR with rotation detection |
| `apps/api/services/llm_vision.py` | Vision extraction (OpenAI) |
| `apps/api/worker/jobs.py` | Job pipeline (ingest→extract→normalize) |
| `apps/api/db/models.py` | SourceSpan with source_method field |
| `infra/migrations/002_add_source_method.sql` | Database schema |
| `docs/SPEC.md` | Canonical specification |
| `docs/TESTING_GUIDE.md` | Comprehensive testing |
| `docs/DEPLOYMENT_CHECKLIST.md` | Deployment steps |

---

## What Works Now

- ✅ Rotation detection (0°, 90°, 180°, 270°)
- ✅ OCR on rotated images
- ✅ Field attribution (source_method tracking)
- ✅ Job pipeline (ingest, extract, normalize)
- ✅ Database schema ready

## What's Next

- ⏳ Integration testing (user-provided recipe cards)
- ⏳ UI badges for source display
- ⏳ Performance optimization
- ⏳ Pantry & matching (Sprint 6)

---

## Documentation

- **Overview:** `docs/IMPLEMENTATION_SUMMARY.md`
- **Details:** `docs/IMPLEMENTATION_PROGRESS.md`
- **Testing:** `docs/TESTING_GUIDE.md`
- **Deployment:** `docs/DEPLOYMENT_CHECKLIST.md`
- **Specification:** `docs/SPEC.md` (canonical)

---

**Questions?** Check the docs or review the code comments.  
**Ready to test?** Run `pytest tests/ -v` and check CI.  
**Ready to deploy?** Follow DEPLOYMENT_CHECKLIST.md.
