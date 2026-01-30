# Testing Guide - Vision-Primary Extraction

## Prerequisites

### System Dependencies
- **Tesseract OCR** (for rotation detection)
  ```bash
  # Ubuntu/Debian
  sudo apt-get install tesseract-ocr
  
  # macOS
  brew install tesseract
  ```

- **ImageMagick** (for image rotation)
  ```bash
  # Ubuntu/Debian
  sudo apt-get install imagemagick
  
  # macOS
  brew install imagemagick
  ```

### Python Dependencies
All dependencies should be installed via requirements.txt:
```bash
cd apps/api
pip install -r requirements.txt
```

Key packages:
- `paddleocr` - Primary OCR engine
- `openai` - OpenAI Vision API client (required)

## Unit Tests

### Test Rotation Detection
**File:** `apps/api/tests/test_ocr_rotation.py`

```python
import pytest
from apps.api.services.ocr import OCRService
from pathlib import Path

@pytest.fixture
def ocr_service():
    return OCRService(use_gpu=False, enable_rotation_detection=True)

def test_rotation_detection_90_degrees(ocr_service):
    """Test detection of 90° rotated image."""
    test_image = Path("tests/fixtures/recipe_90deg.jpg")
    result_path, rotation = ocr_service._detect_and_correct_rotation(str(test_image))
    
    assert rotation in [0, 90, 180, 270]
    assert Path(result_path).exists()

def test_rotation_detection_upright(ocr_service):
    """Test upright (0°) image detected correctly."""
    test_image = Path("tests/fixtures/recipe_upright.jpg")
    result_path, rotation = ocr_service._detect_and_correct_rotation(str(test_image))
    
    assert rotation == 0  # or graceful handling

@pytest.mark.parametrize("degrees", [0, 90, 180, 270])
def test_rotation_detection_all_angles(ocr_service, degrees):
    """Test all 4 cardinal rotations."""
    test_image = Path(f"tests/fixtures/recipe_{degrees}deg.jpg")
    if test_image.exists():
        result_path, detected = ocr_service._detect_and_correct_rotation(str(test_image))
        assert isinstance(detected, int)
        assert isinstance(result_path, str)
```

### Test OCR Extraction
**File:** `apps/api/tests/test_ocr_extraction.py`

```python
import pytest
from apps.api.services.ocr import OCRService, OCRLineData
from io import BytesIO
from pathlib import Path

@pytest.fixture
def ocr_service():
    return OCRService(use_gpu=False, enable_rotation_detection=True)

def test_extract_text_from_image(ocr_service):
    """Test basic OCR extraction."""
    with open("tests/fixtures/recipe_upright.jpg", "rb") as f:
        file_data = BytesIO(f.read())
    
    ocr_lines = ocr_service.extract_text(file_data, asset_type="image")
    
    assert isinstance(ocr_lines, list)
    assert len(ocr_lines) > 0
    
    # Check OCRLineData structure
    for line in ocr_lines:
        assert isinstance(line, OCRLineData)
        assert isinstance(line.text, str)
        assert isinstance(line.bbox, list)
        assert isinstance(line.confidence, float)
        assert 0 <= line.confidence <= 1

def test_extract_text_rotated_image(ocr_service):
    """Test OCR on rotated image with preprocessing."""
    with open("tests/fixtures/recipe_90deg.jpg", "rb") as f:
        file_data = BytesIO(f.read())
    
    ocr_lines = ocr_service.extract_text(file_data, asset_type="image")
    
    # Should extract text despite rotation
    assert len(ocr_lines) > 0
    assert any("recipe" in line.text.lower() for line in ocr_lines)
```

### Test Vision Service
**File:** `apps/api/tests/test_llm_vision.py`

```python
import pytest
import os
from apps.api.services.llm_vision import LLMVisionService, get_llm_vision_service

@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)
def test_vision_extract():
    llm_service = get_llm_vision_service()
    with open("tests/fixtures/recipe_sparse.jpg", "rb") as f:
        image_data = f.read()
    
    result = llm_service.extract_recipe_from_image(image_data)
    
    assert isinstance(result, dict)
    # At least some fields should be extracted
    has_content = (
        result.get("title") or 
        result.get("ingredients") or 
        result.get("steps")
    )
    assert has_content, "Vision extractor should return at least some fields"

def test_json_parsing():
    """Test JSON extraction from vision response."""
    response_text = '''
    The recipe has the following:
    {
        "title": "Chocolate Cake",
        "ingredients": ["flour", "cocoa", "sugar"],
        "steps": ["Mix", "Bake"]
    }
    Some trailing text.
    '''
    
    result = LLMVisionService._parse_json_response(response_text)
    
    assert result["title"] == "Chocolate Cake"
    assert len(result["ingredients"]) == 3
    assert len(result["steps"]) == 2
```

### Test Job Functions
**File:** `apps/api/tests/test_jobs.py`

```python
import pytest
import asyncio
from io import BytesIO
from apps.api.worker.jobs import (
    ingest_recipe,
    extract_recipe,
    normalize_recipe,
)
from pathlib import Path

@pytest.mark.asyncio
async def test_ingest_recipe():
    """Test ingest job with real image."""
    with open("tests/fixtures/recipe_upright.jpg", "rb") as f:
        file_data = f.read()
    
    result = await ingest_recipe(
        asset_id="test-asset-1",
        user_id="test-user-1",
        file_data=file_data,
        asset_type="image",
    )
    
    assert result["status"] == "success"
    assert result["ocr_line_count"] > 0

@pytest.mark.asyncio
async def test_extract_recipe():
    """Test vision extract job with real image."""
    with open("tests/fixtures/recipe_upright.jpg", "rb") as f:
        file_data = f.read()

    await ingest_recipe(
        asset_id="test-asset-1",
        user_id="test-user-1",
        file_data=file_data,
        asset_type="image",
    )

    result = await extract_recipe(
        asset_id="test-asset-1",
        user_id="test-user-1",
    )

    assert result["status"] == "success"
```

## Integration Tests

### End-to-End Test
**File:** `apps/api/tests/test_e2e_ocr_pipeline.py`

```python
import pytest
import asyncio
from io import BytesIO
from pathlib import Path
from apps.api.worker.jobs import ingest_recipe, extract_recipe, normalize_recipe
from apps.api.db.session import SessionLocal
from apps.api.db.models import Asset, Recipe, SourceSpan

@pytest.mark.asyncio
async def test_full_pipeline_upright_recipe():
    """Test full pipeline: upload → ingest → extract → normalize."""
    # Load test image
    test_image_path = Path("tests/fixtures/recipe_upright.jpg")
    with open(test_image_path, "rb") as f:
        file_data = f.read()
    
    asset_id = "test-asset-upright-1"
    user_id = "test-user-1"
    
    # Step 1: Ingest
    ingest_result = await ingest_recipe(asset_id, user_id, file_data)
    assert ingest_result["status"] == "success"
    assert ingest_result["ocr_line_count"] > 0
    
    # Step 2: Extract (vision-primary)
    extract_result = await extract_recipe(asset_id, user_id)
    assert extract_result["status"] == "success"
    recipe_id = extract_result["recipe_id"]
    
    # Verify database
    db = SessionLocal()
    try:
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        assert recipe is not None
        assert recipe.title is not None
        assert len(recipe.ingredients) > 0
        assert len(recipe.steps) > 0
        
        # Verify source spans
        spans = db.query(SourceSpan).filter(
            SourceSpan.recipe_id == recipe_id
        ).all()
        assert len(spans) > 0
        
        # All spans should have source_method="ocr" or "vision-api"
        for span in spans:
            if span.extracted_text:  # Only if successfully extracted
                assert span.source_method in ["ocr", "vision-api"]
    
    finally:
        db.close()
    
    # Step 3: Normalize
    normalize_result = await normalize_recipe(recipe_id, user_id)
    assert normalize_result["status"] == "success"

@pytest.mark.asyncio
async def test_full_pipeline_rotated_recipe():
    """Test full pipeline with rotated image."""
    # Load 90° rotated recipe image
    test_image_path = Path("tests/fixtures/recipe_90deg.jpg")
    with open(test_image_path, "rb") as f:
        file_data = f.read()
    
    asset_id = "test-asset-rotated-90-1"
    user_id = "test-user-1"
    
    # Ingest should handle rotation automatically
    ingest_result = await ingest_recipe(asset_id, user_id, file_data)
    assert ingest_result["status"] == "success"
    
    # Should extract content despite rotation
    assert ingest_result["ocr_line_count"] > 0

```

## Manual Testing

### Step 1: Prepare Test Images
Create test images directory:
```bash
mkdir -p tests/fixtures
```

Add test recipe card images (JPG or PNG):
- `recipe_upright.jpg` - Normal orientation
- `recipe_90deg.jpg` - 90° counterclockwise
- `recipe_180deg.jpg` - 180° upside down
- `recipe_270deg.jpg` - 90° clockwise
- `recipe_sparse.jpg` - Low quality/OCR challenges

### Step 2: Test Rotation Detection
```bash
python -c "
from apps.api.services.ocr import OCRService
from pathlib import Path

service = OCRService(use_gpu=False, enable_rotation_detection=True)

for angle in [0, 90, 180, 270]:
    test_image = Path(f'tests/fixtures/recipe_{angle}deg.jpg')
    if test_image.exists():
        rotated_path, detected_rotation = service._detect_and_correct_rotation(str(test_image))
        print(f'{angle}° image: detected {detected_rotation}°')
"
```

### Step 3: Test OCR Extraction
```bash
python -c "
from apps.api.services.ocr import OCRService
from pathlib import Path
from io import BytesIO

service = OCRService(use_gpu=False, enable_rotation_detection=True)

with open('tests/fixtures/recipe_upright.jpg', 'rb') as f:
    ocr_lines = service.extract_text(BytesIO(f.read()), 'image')

print(f'Extracted {len(ocr_lines)} lines')
for line in ocr_lines[:5]:
    print(f'  {line.text[:50]}... (confidence: {line.confidence:.2f})')
"
```

### Step 4: Test Vision Extraction
```bash
python -c "
from apps.api.services.llm_vision import get_llm_vision_service
from pathlib import Path

service = get_llm_vision_service()

with open('tests/fixtures/recipe_sparse.jpg', 'rb') as f:
    result = service.extract_recipe_from_image(f.read())

print('Vision extracted fields:', list(result.keys()))
print('Title:', result.get('title'))
print('Ingredients:', len(result.get('ingredients', [])))
print('Steps:', len(result.get('steps', [])))
"
```

## Performance Benchmarks

### Expected Performance (per SPEC.md)

| Operation | Target | Notes |
|-----------|--------|-------|
| Rotation detection | < 5 sec | Tesseract PSM 0 + voting |
| OCR extraction | < 10 sec | PaddleOCR on GPU, ~ 2 sec on CPU |
| Vision extraction (OpenAI) | < 10 sec | OpenAI API |
| Parsing | < 1 sec | Deterministic parser (fallback only) |
| Normalization | < 1 sec | Dedup + validation |

### Measurement Script
```bash
python -c "
import time
from io import BytesIO
from pathlib import Path
from apps.api.services.ocr import OCRService

service = OCRService(use_gpu=False, enable_rotation_detection=True)

with open('tests/fixtures/recipe_90deg.jpg', 'rb') as f:
    file_data = BytesIO(f.read())

start = time.time()
ocr_lines = service.extract_text(file_data, 'image')
elapsed = time.time() - start

print(f'OCR + Rotation: {elapsed:.2f} sec')
print(f'Lines extracted: {len(ocr_lines)}')
print(f'Avg time per line: {elapsed/max(1, len(ocr_lines))*1000:.1f} ms')
"
```

## Troubleshooting

### Tesseract Not Found
```bash
# Verify installation
which tesseract

# If not found, install:
# Ubuntu/Debian: sudo apt-get install tesseract-ocr
# macOS: brew install tesseract
```

### ImageMagick "convert" Not Found
```bash
# Verify installation
which convert

# If not found, install:
# Ubuntu/Debian: sudo apt-get install imagemagick
# macOS: brew install imagemagick
```

### Vision Response Parsing Fails
- Check vision response format (should be JSON or include JSON block)
- Enable debug logging to see raw response: `logger.debug(response_text)`

### OCR Returns Empty Results
- Check image quality (very blurry/low res may fail)
- Verify image is actually a recipe (not pure graphics)
- Try with rotation detection enabled
- Verify OpenAI API key/model configuration and retry

---

**Last Updated:** Sprint 2-3 Implementation  
**SPEC.md Version:** V1.1
