# Deployment Checklist - Vision-Primary Extraction

## Pre-Deployment Verification

### Code Quality
- [ ] All Python files pass syntax check
- [ ] No import errors (all dependencies installed)
- [ ] Type hints pass Pylance check
- [ ] Logging statements present for audit trail
- [ ] Error handling for all external service calls

### Database Schema
- [ ] Migration 002_add_source_method.sql is idempotent
- [ ] source_method column added to source_spans table
- [ ] Indexes created on source_method and (recipe_id, source_method)
- [ ] Backward compatible (default="ocr" for existing data)

### Dependencies
- [ ] `paddleocr` - OCR engine (already in requirements)
- [ ] `paddlepaddle` - PaddleOCR dependency (already in requirements)
- [ ] `openai>=1.63.0` - OpenAI API (required for vision extraction)

### System Tools
- [ ] Tesseract OCR installed (`tesseract --version`)
- [ ] ImageMagick installed (`convert --version`)
- [ ] Python 3.10+ (`python --version`)

## Deployment Steps

### 1. Code Deployment
```bash
# Pull latest changes
git pull origin main

# Install/update dependencies
cd apps/api
pip install -r requirements.txt

# Verify imports work
python -c "
from apps.api.services.ocr import OCRService
from apps.api.services.llm_vision import LLMVisionService
from apps.api.worker.jobs import ingest_recipe, structure_recipe
print('All imports successful')
"
```

### 2. Database Migration
```bash
# Run migration to add source_method column
# (Use your database migration tool: Alembic, manual SQL, etc.)

# Example with psql:
psql -U postgres -d recipenow -f infra/migrations/002_add_source_method.sql

# Verify migration applied
psql -U postgres -d recipenow -c "
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name='source_spans' AND column_name='source_method';
"
```

### 3. Environment Configuration

#### Required Environment Variables
```bash
# Set in your deployment environment (.env file or secrets):

# OCR Service (optional - defaults shown)
ENABLE_ROTATION_DETECTION=true

# Vision API (OpenAI)
OPENAI_API_KEY=...
VISION_MODEL=gpt-4o-mini
VISION_MAX_OUTPUT_TOKENS=1024
VISION_STRICT_JSON=true
```

#### Docker Compose Updates (if using containers)
```yaml
# In infra/docker-compose.yml, ensure services have:

services:
  api:
    image: recipenow-api:latest
    environment:
      - ENABLE_ROTATION_DETECTION=true
      - OPENAI_API_KEY=...
      - VISION_MODEL=gpt-4o-mini
    depends_on:
      - postgres
      - redis
    # Tesseract and ImageMagick already in Dockerfile
```

### 5. System Tool Installation

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr imagemagick

# Verify
tesseract --version
convert --version
```

#### macOS
```bash
brew install tesseract imagemagick

# Verify
tesseract --version
convert --version
```

#### Alpine (for Docker)
```dockerfile
# Add to Dockerfile:
RUN apk add --no-cache \
    tesseract-ocr \
    imagemagick
```

### 6. Smoke Tests
```bash
# Test OCR service loads
python -c "
from apps.api.services.ocr import get_ocr_service
service = get_ocr_service()
print('✓ OCRService loaded')
"

# Test Vision service loads
python -c "
from apps.api.services.llm_vision import get_llm_vision_service
service = get_llm_vision_service()
print('✓ Vision service loaded')
"

# Test jobs module loads
python -c "
from apps.api.worker.jobs import ingest_recipe, extract_recipe
print('✓ Jobs module loaded')
"

# Test Tesseract
python -c "
import subprocess
result = subprocess.run(['tesseract', '--version'], capture_output=True)
if result.returncode == 0:
    print('✓ Tesseract available')
"

# Test ImageMagick
python -c "
import subprocess
result = subprocess.run(['convert', '--version'], capture_output=True)
if result.returncode == 0:
    print('✓ ImageMagick available')
"
```

### 7. Integration Smoke Test
```bash
# Start API server
uvicorn apps.api.main:app --reload

# In another terminal, test upload endpoint
curl -X POST \
  -H "Authorization: Bearer YOUR_TEST_TOKEN" \
  -F "file=@tests/fixtures/recipe_upright.jpg" \
  http://localhost:8000/api/recipes/upload

# Should return: asset_id, ocr_status: "completed"
```

## Post-Deployment Checks

### Monitoring
- [ ] API server starts without errors
- [ ] Logs show OCR service initialized
- [ ] Logs show Vision service initialized
- [ ] No rotation detection timeouts (should be < 5 sec)
- [ ] No OCR failures (unless image truly unreadable)

### Database Health
- [ ] New recipes have source_spans created
- [ ] source_spans.source_method is populated correctly
  ```sql
  SELECT DISTINCT source_method FROM source_spans LIMIT 5;
  -- Should see "ocr" or "vision-api" for recent recipes
  ```
- [ ] Recipe titles, ingredients, steps populated
  ```sql
  SELECT COUNT(*) FROM recipes WHERE title IS NOT NULL;
  -- Should be > 0 for recent uploads
  ```

### Log Review
```bash
# Check for errors
grep -i "error\|failed" logs/api.log

# Check OCR performance
grep "OCR extracted" logs/api.log | head -5

# Check vision extraction usage
grep -i "vision" logs/api.log | head -5
```

## Rollback Plan

If issues found post-deployment:

### Option 1: Revert Code
```bash
git revert HEAD  # Revert last commit
git push origin main
# Redeploy API
```

### Option 2: Disable Features
```bash
# Disable rotation detection
export ENABLE_ROTATION_DETECTION=false

# Restart API
```

### Option 3: Database Rollback
```bash
# If migration needs rollback
psql -U postgres -d recipenow -c "
ALTER TABLE source_spans DROP COLUMN IF EXISTS source_method;
DROP INDEX IF EXISTS idx_source_spans_source_method;
DROP INDEX IF EXISTS idx_source_spans_recipe_method;
"
```

## Known Issues & Mitigations

| Issue | Symptoms | Mitigation |
|-------|----------|-----------|
| Tesseract not found | Rotation detection fails | Ensure `tesseract` CLI installed |
| ImageMagick not found | Rotation not applied | Ensure `convert` CLI available |
| Vision returns unparseable JSON | Vision extraction fails | Ensure strict JSON + retry; verify OpenAI config |
| OCR memory exhaustion | API crashes on large images | Reduce image size, use GPU |
| PaddleOCR initialization slow | First request delayed | Pre-load OCR on startup |

## Verification Checklist (Go/No-Go)

Before marking deployment as complete:

- [ ] Code deployed and API starts
- [ ] Database migration applied without errors
- [ ] All dependencies installed
- [ ] System tools available (Tesseract, ImageMagick)
- [ ] Environment variables configured
- [ ] Smoke tests all pass
- [ ] Sample recipe upload succeeds
- [ ] OCR extracts text (upright image)
- [ ] Rotation detection works (rotated image)
- [ ] Source spans created with source_method
- [ ] No error logs in last 5 minutes
- [ ] Performance within targets (OCR < 10 sec)

## Post-Deployment Monitoring

### Weekly Checks
```bash
# Check OCR success rate
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN title IS NOT NULL THEN 1 ELSE 0 END) as with_title,
  SUM(CASE WHEN array_length(ingredients, 1) > 0 THEN 1 ELSE 0 END) as with_ingredients
FROM recipes
WHERE created_at >= NOW() - INTERVAL '7 days';
```

### Performance Monitoring
```bash
# Track OCR extraction time
SELECT 
  AVG(extraction_time_ms) as avg_time,
  MAX(extraction_time_ms) as max_time,
  MIN(extraction_time_ms) as min_time
FROM ocr_metrics
WHERE date >= NOW() - INTERVAL '7 days';
```

### Vision Usage
```bash
SELECT 
  source_method,
  COUNT(*) as count
FROM source_spans
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY source_method;

-- Expected: mix of "ocr" and "vision-api"
```

---

**Last Updated:** Sprint 2-3 Completion  
**Deployment Target:** Production  
**SPEC.md Version:** V1.1 (vision-primary)
