"""
Background jobs and async task processing for RecipeNow.

Implements the vision-primary ingestion pipeline per SPEC.md:
1. Ingest Job: Run OCR with rotation detection (provenance only)
2. Extract Job: Vision API extraction with OCR evidence IDs
3. Normalize Job: Standardize extracted data (dedupe ingredients, fix times, etc.)
"""
import json
import logging
import os
import re
from typing import Optional, Dict, List, Any
from urllib.parse import urlparse
from uuid import UUID

logger = logging.getLogger(__name__)


def _redis_settings_from_env():
    try:
        from arq.connections import RedisSettings
    except ImportError as exc:
        raise RuntimeError("ARQ RedisSettings is required for worker startup") from exc

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    parsed = urlparse(redis_url)
    db = int(parsed.path.lstrip("/")) if parsed.path and parsed.path != "/" else 0
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=db,
    )


def _union_bboxes(bboxes: List[List[float]]) -> List[float]:
    if not bboxes:
        return [0, 0, 0, 0]
    x_min = min(b[0] for b in bboxes)
    y_min = min(b[1] for b in bboxes)
    x_max = max(b[0] + b[2] for b in bboxes)
    y_max = max(b[1] + b[3] for b in bboxes)
    return [x_min, y_min, x_max - x_min, y_max - y_min]


def _build_span_from_evidence(
    field_path: str,
    extracted_text: str,
    evidence_ids: List[str],
    ocr_line_map: Dict[str, Any],
    asset_id: str,
    source_method: str = "vision-api",
) -> Optional[Dict[str, Any]]:
    evidence_ids = [str(eid) for eid in evidence_ids or []]
    lines = [ocr_line_map[eid] for eid in evidence_ids if eid in ocr_line_map]
    if not lines:
        return None
    bboxes = [line.bbox for line in lines]
    bbox = _union_bboxes(bboxes)
    page = lines[0].page
    confidence = sum(line.confidence for line in lines) / len(lines)
    return {
        "field_path": field_path,
        "asset_id": asset_id,
        "page": page,
        "bbox": bbox,
        "extracted_text": extracted_text,
        "confidence": confidence,
        "source_method": source_method,
        "evidence": {"ocr_line_ids": evidence_ids},
    }


def _vision_to_recipe_payload(vision_result: Dict[str, Any]) -> Dict[str, Any]:
    recipe = {
        "title": None,
        "servings": None,
        "servings_estimate": None,
        "times": {"prep_min": None, "cook_min": None, "total_min": None},
        "ingredients": [],
        "steps": [],
        "tags": [],
    }

    title = vision_result.get("title")
    if isinstance(title, dict):
        recipe["title"] = title.get("text") or None

    servings = vision_result.get("servings") or {}
    if isinstance(servings, dict):
        if servings.get("is_estimate"):
            recipe["servings_estimate"] = {
                "value": servings.get("value"),
                "confidence": servings.get("confidence"),
                "basis": None,
                "approved_by_user": False,
            }
        else:
            recipe["servings"] = servings.get("value")

    servings_estimate = vision_result.get("servings_estimate")
    if isinstance(servings_estimate, dict):
        recipe["servings_estimate"] = {
            "value": servings_estimate.get("value"),
            "confidence": servings_estimate.get("confidence"),
            "basis": servings_estimate.get("basis"),
            "approved_by_user": False,
        }

    times = vision_result.get("times") or {}
    if isinstance(times, dict):
        for key in ["prep_min", "cook_min", "total_min"]:
            entry = times.get(key)
            if isinstance(entry, dict):
                recipe["times"][key] = entry.get("value")

    ingredients = vision_result.get("ingredients") or []
    for item in ingredients:
        if isinstance(item, dict) and item.get("text"):
            recipe["ingredients"].append(
                {
                    "original_text": item.get("text"),
                    "name_norm": None,
                    "quantity": None,
                    "unit": None,
                    "optional": False,
                }
            )

    steps = vision_result.get("steps") or []
    for item in steps:
        if isinstance(item, dict) and item.get("text"):
            recipe["steps"].append({"text": item.get("text")})

    return recipe


def _build_field_statuses(recipe_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    statuses = []

    def mark(field_path: str, present: bool, note_missing: str):
        statuses.append(
            {
                "field_path": field_path,
                "status": "extracted" if present else "missing",
                "notes": None if present else note_missing,
            }
        )

    mark("title", bool(recipe_data.get("title")), "Could not detect title")
    mark(
        "ingredients",
        bool(recipe_data.get("ingredients")),
        "Could not detect ingredients",
    )
    mark("steps", bool(recipe_data.get("steps")), "Could not detect steps")
    mark("servings", bool(recipe_data.get("servings")), "Servings not found")

    return statuses


def _extract_ingredient_name(original_text: str) -> Optional[str]:
    """
    Extract ingredient name from text containing quantities and units.

    Examples:
        "2 cups all-purpose flour" -> "flour"
        "1.5 tbsp olive oil" -> "olive oil"
        "salt" -> "salt"

    Args:
        original_text: Raw ingredient text with possible quantities/units

    Returns:
        Normalized ingredient name, or None if cannot extract
    """
    if not original_text or not original_text.strip():
        return None

    text = original_text.strip().lower()

    # Common quantity and unit patterns
    quantity_pattern = r'^[\d\s\-./½⅓¼¾⅔⅛⅜⅝⅞\(\)]+(?:tsp|tbsp|cup|cups|oz|ml|l|g|kg|lb|lbs|pinch|dash|handful|to\s+)?'

    # Remove leading quantities and units
    text = re.sub(quantity_pattern, '', text, flags=re.IGNORECASE).strip()

    # Remove common qualifier words at the start
    qualifiers = r'^(fresh|dried|ground|powdered|minced|chopped|sliced|grated|melted|softened|cooked|raw|roasted)\s+'
    text = re.sub(qualifiers, '', text, flags=re.IGNORECASE).strip()

    # Remove trailing qualifiers
    text = re.sub(r'\s+(or\s+)?(.*)$', '', text).strip()

    # Clean up remaining whitespace and special characters
    text = re.sub(r'\s+', ' ', text).strip()

    return text if text else None


async def ingest_recipe(
    asset_id: str,
    user_id: str,
    file_data: bytes,
    asset_type: str = "image",
    recipe_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingest Job (Sprint 2): Extract text from uploaded media with OCR.
    
    Steps:
    1. Store uploaded asset file
    2. Detect and correct image orientation (if image)
    3. Run OCR (PaddleOCR)
    4. Create Asset and OCRLines in database
    5. Queue Structure Job
    
    Args:
        asset_id: UUID of asset
        user_id: UUID of user
        file_data: Raw file bytes
        asset_type: "image" or "pdf"
    
    Returns:
        Job result dict with status and OCR line count
    """
    from apps.api.db.session import SessionLocal
    from apps.api.services.ocr import get_ocr_service
    from apps.api.db.models import MediaAsset, OCRLine
    from sqlalchemy import insert
    
    logger.info(f"Ingest Job: Starting for asset {asset_id}, user {user_id}")
    
    try:
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        # Get OCR service
        ocr_service = get_ocr_service(use_gpu=False, lang="en")
        
        # Extract text with rotation detection
        ocr_lines_data = ocr_service.extract_text(
            file_data=file_data,
            asset_type=asset_type,
        )
        
        logger.info(f"OCR extracted {len(ocr_lines_data)} lines for asset {asset_id}")
        
        # Store in database
        db = SessionLocal()
        try:
            asset_uuid = UUID(asset_id) if isinstance(asset_id, str) else asset_id
            asset = db.query(MediaAsset).filter(MediaAsset.id == asset_uuid).first()
            if not asset:
                asset = MediaAsset(
                    id=asset_uuid,
                    user_id=user_uuid,
                    type=asset_type,
                    sha256="",
                    storage_path="",
                )
                db.add(asset)
                db.flush()
            
            # Bulk insert OCR lines
            if ocr_lines_data:
                ocr_lines = [
                    {
                        "asset_id": asset_uuid,
                        "page": line.page,
                        "text": line.text,
                        "bbox": line.bbox,  # [x, y, w, h]
                        "confidence": line.confidence,
                    }
                    for line in ocr_lines_data
                ]
                db.execute(insert(OCRLine), ocr_lines)
            
            db.commit()
            logger.info(f"Asset {asset_id} stored with {len(ocr_lines_data)} OCR lines")

            if recipe_id:
                await extract_recipe(
                    asset_id=asset_id,
                    user_id=user_id,
                    recipe_id=recipe_id,
                    image_bytes=file_data,
                )
            
            return {
                "status": "success",
                "asset_id": asset_id,
                "ocr_line_count": len(ocr_lines_data),
                "message": f"Ingested {len(ocr_lines_data)} OCR lines",
            }
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Ingest Job failed for asset {asset_id}: {e}", exc_info=True)
        return {
            "status": "failed",
            "asset_id": asset_id,
            "error": str(e),
        }


async def extract_recipe(
    asset_id: str,
    user_id: str,
    recipe_id: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
) -> Dict[str, Any]:
    """
    Extract Job (Vision-Primary): Use vision API with OCR evidence to build recipe draft.
    """
    from apps.api.db.session import SessionLocal
    from apps.api.db.models import OCRLine, Recipe, SourceSpan, FieldStatus, MediaAsset
    from apps.api.services.llm_vision import get_llm_vision_service
    from apps.api.services.parser import RecipeParser, OCRLineData
    from apps.api.services.storage import get_storage_backend
    from sqlalchemy import select

    logger.info(f"Extract Job: Starting for asset {asset_id}, user {user_id}")

    db = SessionLocal()
    try:
        asset_uuid = UUID(asset_id) if isinstance(asset_id, str) else asset_id
        ocr_lines_query = db.execute(
            select(OCRLine).where(OCRLine.asset_id == asset_uuid)
        )
        ocr_line_models = ocr_lines_query.scalars().all()
        if not ocr_line_models:
            return {"status": "failed", "error": "No OCR lines found"}

        ocr_line_map = {str(line.id): line for line in ocr_line_models}
        ocr_lines_payload = [
            {"id": str(line.id), "text": line.text, "page": line.page}
            for line in ocr_line_models
        ]

        if image_bytes is None:
            asset = db.query(MediaAsset).filter(MediaAsset.id == asset_uuid).first()
            if not asset:
                return {"status": "failed", "error": "Asset not found"}
            storage = get_storage_backend()
            image_bytes = storage.get(asset.storage_path)

        vision_service = get_llm_vision_service()
        try:
            vision_result = vision_service.extract_with_evidence(image_bytes, ocr_lines_payload)
            recipe_data = _vision_to_recipe_payload(vision_result)
            field_statuses = _build_field_statuses(recipe_data)

            spans: List[Dict[str, Any]] = []
            title = vision_result.get("title") or {}
            if isinstance(title, dict) and title.get("text"):
                span = _build_span_from_evidence(
                    "title",
                    title.get("text"),
                    title.get("evidence_ocr_line_ids", []),
                    ocr_line_map,
                    asset_id,
                    source_method="vision-api",
                )
                if span:
                    spans.append(span)

            for idx, item in enumerate(vision_result.get("ingredients") or []):
                if not isinstance(item, dict):
                    continue
                span = _build_span_from_evidence(
                    f"ingredients[{idx}].original_text",
                    item.get("text") or "",
                    item.get("evidence_ocr_line_ids", []),
                    ocr_line_map,
                    asset_id,
                    source_method="vision-api",
                )
                if span:
                    spans.append(span)

            for idx, item in enumerate(vision_result.get("steps") or []):
                if not isinstance(item, dict):
                    continue
                span = _build_span_from_evidence(
                    f"steps[{idx}].text",
                    item.get("text") or "",
                    item.get("evidence_ocr_line_ids", []),
                    ocr_line_map,
                    asset_id,
                    source_method="vision-api",
                )
                if span:
                    spans.append(span)

            servings = vision_result.get("servings") or {}
            if isinstance(servings, dict) and servings.get("value") is not None:
                span = _build_span_from_evidence(
                    "servings",
                    str(servings.get("value")),
                    servings.get("evidence_ocr_line_ids", []),
                    ocr_line_map,
                    asset_id,
                    source_method="vision-api",
                )
                if span:
                    spans.append(span)

            times = vision_result.get("times") or {}
            if isinstance(times, dict):
                for key in ["prep_min", "cook_min", "total_min"]:
                    entry = times.get(key)
                    if isinstance(entry, dict) and entry.get("value") is not None:
                        span = _build_span_from_evidence(
                            f"times.{key}",
                            str(entry.get("value")),
                            entry.get("evidence_ocr_line_ids", []),
                            ocr_line_map,
                            asset_id,
                            source_method="vision-api",
                        )
                        if span:
                            spans.append(span)

        except Exception as exc:
            logger.warning(f"Vision extraction failed; falling back to parser: {exc}")
            parser_lines = [
                OCRLineData(
                    page=line.page,
                    text=line.text,
                    bbox=line.bbox,
                    confidence=line.confidence,
                )
                for line in ocr_line_models
            ]
            parser = RecipeParser()
            parse_result = parser.parse(parser_lines, asset_id)
            recipe_data = parse_result.get("recipe", {})
            spans = parse_result.get("spans", [])
            field_statuses = parse_result.get("field_statuses", [])
            for span in spans:
                span["source_method"] = "ocr"

        recipe_uuid = UUID(recipe_id) if recipe_id else None
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        recipe = db.query(Recipe).filter(Recipe.id == recipe_uuid).first() if recipe_uuid else None
        if not recipe:
            recipe = Recipe(
                id=recipe_uuid or _generate_uuid(),
                user_id=user_uuid,
                status="draft",
            )
            db.add(recipe)
            db.flush()

        recipe.title = recipe_data.get("title")
        recipe.servings = recipe_data.get("servings")
        recipe.servings_estimate = recipe_data.get("servings_estimate")
        recipe.times = recipe_data.get("times", {})
        recipe.ingredients = recipe_data.get("ingredients", [])
        recipe.steps = recipe_data.get("steps", [])
        recipe.tags = recipe_data.get("tags", [])

        db.query(SourceSpan).filter_by(recipe_id=recipe.id).delete()
        db.query(FieldStatus).filter_by(recipe_id=recipe.id).delete()

        for span in spans:
            asset_value = span.get("asset_id") or asset_id
            asset_uuid = UUID(asset_value) if isinstance(asset_value, str) else asset_value
            source_span = SourceSpan(
                recipe_id=recipe.id,
                field_path=span.get("field_path"),
                asset_id=asset_uuid,
                page=span.get("page", 0),
                bbox=span.get("bbox"),
                extracted_text=span.get("extracted_text"),
                ocr_confidence=span.get("confidence", span.get("ocr_confidence", 0.0)),
                source_method=span.get("source_method", "ocr"),
                evidence=span.get("evidence"),
            )
            db.add(source_span)

        for status in field_statuses:
            db.add(
                FieldStatus(
                    recipe_id=recipe.id,
                    field_path=status.get("field_path"),
                    status=status.get("status"),
                    notes=status.get("notes"),
                )
            )

        db.commit()
        return {"status": "success", "recipe_id": str(recipe.id)}
    finally:
        db.close()


async def structure_recipe(
    asset_id: str,
    user_id: str,
    recipe_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Legacy structure job retained for compatibility.
    Delegates to vision-primary extract job.
    """
    logger.info("Structure job is deprecated; delegating to extract_recipe.")
    return await extract_recipe(asset_id=asset_id, user_id=user_id, recipe_id=recipe_id)


def _generate_uuid() -> UUID:
    """Generate a UUID for recipe ID."""
    import uuid
    return uuid.uuid4()


async def normalize_recipe(
    recipe_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Normalize Job (Sprint 4): Standardize extracted recipe data.
    
    Steps:
    1. Deduplicate and normalize ingredients
    2. Fix time formats
    3. Standardize tags/categories
    4. Quality checks
    5. Update recipe status
    
    Args:
        recipe_id: UUID of recipe
        user_id: UUID of user
    
    Returns:
        Job result dict with normalization status
    """
    from apps.api.db.session import SessionLocal
    from apps.api.db.models import Recipe
    
    logger.info(f"Normalize Job: Starting for recipe {recipe_id}, user {user_id}")
    
    db = SessionLocal()
    try:
        recipe = db.query(Recipe).filter(
            Recipe.id == recipe_id,
            Recipe.user_id == user_id,
        ).first()
        
        if not recipe:
            logger.warning(f"Recipe {recipe_id} not found for user {user_id}")
            return {
                "status": "failed",
                "recipe_id": recipe_id,
                "error": "Recipe not found",
            }
        
        # Deduplicate ingredients
        if recipe.ingredients:
            recipe.ingredients = _deduplicate_ingredients(recipe.ingredients)
        
        # Fix time formats
        if recipe.times:
            recipe.times = _normalize_times(recipe.times)
        
        # Standardize tags
        if recipe.tags:
            recipe.tags = _standardize_tags(recipe.tags)
        
        # Run quality checks
        issues = _quality_check(recipe)
        
        # Mark as ready for review
        recipe.status = "review" if not issues else "draft_with_issues"
        
        db.commit()
        logger.info(f"Recipe {recipe_id} normalized. Issues: {len(issues)}")
        
        return {
            "status": "success",
            "recipe_id": recipe_id,
            "quality_issues": issues,
            "message": f"Recipe normalized with {len(issues)} issues",
        }
    except Exception as e:
        logger.error(f"Normalize Job failed for recipe {recipe_id}: {e}", exc_info=True)
        return {
            "status": "failed",
            "recipe_id": recipe_id,
            "error": str(e),
        }
    finally:
        db.close()


# ARQ compatibility wrappers (used by worker.jobs.WorkerSettings)
async def ingest_job(
    ctx,
    asset_id: str,
    use_gpu: bool = False,
    user_id: Optional[str] = None,
    recipe_id: Optional[str] = None,
    file_data: Optional[bytes] = None,
    asset_type: str = "image",
) -> Dict[str, Any]:
    if not user_id or file_data is None:
        return {"status": "failed", "error": "user_id and file_data are required"}
    return await ingest_recipe(
        asset_id=asset_id,
        user_id=user_id,
        file_data=file_data,
        asset_type=asset_type,
        recipe_id=recipe_id,
    )


async def extract_job(
    ctx,
    asset_id: str,
    user_id: str,
    recipe_id: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
) -> Dict[str, Any]:
    return await extract_recipe(
        asset_id=asset_id,
        user_id=user_id,
        recipe_id=recipe_id,
        image_bytes=image_bytes,
    )


async def structure_job(
    ctx,
    asset_id: str,
    user_id: str,
    recipe_id: Optional[str] = None,
) -> Dict[str, Any]:
    return await structure_recipe(
        asset_id=asset_id,
        user_id=user_id,
        recipe_id=recipe_id,
    )


async def normalize_job(
    ctx,
    recipe_id: str,
    user_id: str,
) -> Dict[str, Any]:
    return await normalize_recipe(recipe_id=recipe_id, user_id=user_id)


class WorkerSettings:
    redis_settings = _redis_settings_from_env()
    functions = [ingest_job, extract_job, structure_job, normalize_job]
    max_jobs = int(os.getenv("ARQ_MAX_JOBS", "10"))
    job_timeout = int(os.getenv("ARQ_JOB_TIMEOUT", str(30 * 60)))
    result_ttl = int(os.getenv("ARQ_RESULT_TTL", str(24 * 60 * 60)))


def _deduplicate_ingredients(ingredients: List[str]) -> List[str]:
    """Deduplicate and normalize ingredient list."""
    seen = set()
    unique = []
    for ing in ingredients:
        normalized = ing.lower().strip()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(ing)
    return unique


def _normalize_times(times: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize time values (ensure minutes, handle invalid values)."""
    normalized = {}
    for key, value in times.items():
        if value is not None and isinstance(value, (int, float)) and value > 0:
            normalized[key] = int(value)
    return normalized


def _standardize_tags(tags: List[str]) -> List[str]:
    """Standardize recipe tags/categories."""
    return list(set(tag.lower().strip() for tag in tags if tag))


def _quality_check(recipe: Any) -> List[str]:
    """
    Run quality checks on normalized recipe.
    
    Args:
        recipe: Recipe model instance
    
    Returns:
        List of quality issue strings
    """
    issues = []
    
    if not recipe.title or len(recipe.title.strip()) < 3:
        issues.append("Title too short or missing")
    
    if not recipe.ingredients or len(recipe.ingredients) < 1:
        issues.append("No ingredients found")
    
    if not recipe.steps or len(recipe.steps) < 1:
        issues.append("No steps found")
    
    if recipe.servings and recipe.servings < 1:
        issues.append("Invalid servings value")
    
    return issues
