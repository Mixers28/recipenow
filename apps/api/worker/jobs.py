"""
Background jobs and async task processing for RecipeNow.

Implements the three-stage recipe ingestion pipeline per SPEC.md:
1. Ingest Job: Store uploaded asset, run OCR with rotation detection
2. Structure Job: Parse OCR results, use LLM fallback if critical fields missing
3. Normalize Job: Standardize extracted data (dedupe ingredients, fix times, etc.)
"""
import json
import logging
import re
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


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
) -> Dict[str, Any]:
    """
    Ingest Job (Sprint 2): Extract text from uploaded media with OCR.
    
    Steps:
    1. Store uploaded asset file
    2. Detect and correct image orientation (if image)
    3. Run OCR (PaddleOCR)
    4. Create MediaAsset and OCRLines in database
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
            # Create MediaAsset record
            asset = MediaAsset(
                id=asset_id,
                user_id=user_id,
                asset_type=asset_type,
                file_size=len(file_data),
                ocr_status="completed" if ocr_lines_data else "failed",
            )
            db.add(asset)
            db.flush()
            
            # Bulk insert OCR lines
            if ocr_lines_data:
                ocr_lines = [
                    {
                        "asset_id": asset_id,
                        "page": line.page,
                        "text": line.text,
                        "bbox": line.bbox,  # [x, y, w, h]
                        "confidence": line.confidence,
                    }
                    for line in ocr_lines_data
                ]
                db.execute(insert(OCRLine), ocr_lines)
            
            db.commit()
            logger.info(f"MediaAsset {asset_id} stored with {len(ocr_lines_data)} OCR lines")
            
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


async def structure_recipe(
    asset_id: str,
    user_id: str,
    recipe_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Structure Job (Sprint 3): Parse OCR into structured recipe.
    
    Steps:
    1. Fetch OCR lines from asset
    2. Run deterministic parser
    3. If critical fields missing, invoke LLM vision fallback
    4. Create Recipe and SourceSpans in database
    5. Queue Normalize Job
    
    Critical fields: title, ingredients, steps
    
    Args:
        asset_id: UUID of asset
        user_id: UUID of user
        recipe_id: Optional; if not provided, new recipe created
    
    Returns:
        Job result dict with recipe_id and field statuses
    """
    from apps.api.db.session import SessionLocal
    from apps.api.db.models import OCRLine, Recipe, SourceSpan
    from apps.api.services.parser import RecipeParser
    from apps.api.services.llm_vision import get_llm_vision_service
    from sqlalchemy import select
    
    logger.info(f"Structure Job: Starting for asset {asset_id}, user {user_id}")
    
    try:
        db = SessionLocal()
        try:
            # Fetch OCR lines
            ocr_lines_query = db.execute(
                select(OCRLine).where(OCRLine.asset_id == asset_id)
            )
            ocr_line_models = ocr_lines_query.scalars().all()
            
            if not ocr_line_models:
                logger.warning(f"No OCR lines found for asset {asset_id}")
                return {
                    "status": "failed",
                    "asset_id": asset_id,
                    "error": "No OCR lines found",
                }
            
            # Convert to parser format
            from apps.api.services.parser import OCRLineData
            ocr_lines_data = [
                OCRLineData(
                    page=line.page,
                    text=line.text,
                    bbox=line.bbox,
                    confidence=line.confidence,
                )
                for line in ocr_line_models
            ]
            
            # Parse with deterministic parser
            parser = RecipeParser()
            parse_result = parser.parse(ocr_lines_data, asset_id)
            
            recipe_data = parse_result.get("recipe", {})
            source_spans = parse_result.get("spans", [])
            field_statuses = parse_result.get("field_statuses", [])
            
            logger.info(f"Parser extracted: title={bool(recipe_data.get('title'))}, "
                       f"ingredients={len(recipe_data.get('ingredients', []))}, "
                       f"steps={len(recipe_data.get('steps', []))}")
            
            # Check for critical fields
            missing_critical = _check_missing_critical_fields(recipe_data)
            
            if missing_critical:
                logger.info(f"Critical fields missing: {missing_critical}. Invoking LLM fallback.")
                
                # Get the original file data from asset
                from apps.api.db.models import MediaAsset
                asset = db.query(MediaAsset).filter(MediaAsset.id == asset_id).first()
                
                if asset and asset.file_data:
                    try:
                        # Invoke LLM vision fallback
                        llm_service = get_llm_vision_service()
                        llm_result = llm_service.extract_recipe_from_image(asset.file_data)
                        logger.info(f"LLM fallback returned: {list(llm_result.keys())}")
                        
                        # Merge LLM results with OCR results
                        recipe_data = _merge_llm_fallback(
                            ocr_result=recipe_data,
                            llm_result=llm_result,
                            missing_critical=missing_critical,
                        )
                        
                        # Mark merged fields with source_method="llm-vision"
                        for span in source_spans:
                            if span.get("field_path") in missing_critical:
                                span["source_method"] = "llm-vision"
                        
                        logger.info("LLM fallback merged successfully")
                    
                    except Exception as e:
                        logger.warning(f"LLM fallback failed (proceeding with OCR only): {e}")
                else:
                    logger.warning("MediaAsset file data not available; cannot invoke LLM fallback")
            
            # Store in database
            recipe = Recipe(
                id=recipe_id or _generate_uuid(),
                user_id=user_id,
                asset_id=asset_id,
                title=recipe_data.get("title"),
                servings=recipe_data.get("servings"),
                ingredients=recipe_data.get("ingredients", []),
                steps=recipe_data.get("steps", []),
                tags=recipe_data.get("tags", []),
                times=recipe_data.get("times", {}),
                status="draft",
            )
            db.add(recipe)
            db.flush()
            
            # Store source spans with source_method attribution
            for span in source_spans:
                source_method = span.get("source_method", "ocr")
                source_span = SourceSpan(
                    recipe_id=recipe.id,
                    field_path=span.get("field_path"),
                    source_asset_id=span.get("asset_id"),
                    page=span.get("page"),
                    bbox=span.get("bbox"),
                    extracted_text=span.get("extracted_text"),
                    ocr_confidence=span.get("confidence", 0.0),
                    source_method=source_method,
                )
                db.add(source_span)
            
            db.commit()
            logger.info(f"Recipe {recipe.id} created with {len(source_spans)} source spans")
            
            return {
                "status": "success",
                "asset_id": asset_id,
                "recipe_id": recipe.id,
                "field_statuses": field_statuses,
            }
        
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Structure Job failed for asset {asset_id}: {e}", exc_info=True)
        return {
            "status": "failed",
            "asset_id": asset_id,
            "error": str(e),
        }


def _check_missing_critical_fields(recipe_data: Dict[str, Any]) -> List[str]:
    """
    Check if any critical fields are missing.
    
    Critical fields: title, ingredients, steps
    
    Args:
        recipe_data: Parsed recipe dict
    
    Returns:
        List of missing field names
    """
    missing = []
    
    if not recipe_data.get("title"):
        missing.append("title")
    
    if not recipe_data.get("ingredients") or len(recipe_data["ingredients"]) == 0:
        missing.append("ingredients")
    
    if not recipe_data.get("steps") or len(recipe_data["steps"]) == 0:
        missing.append("steps")
    
    return missing


def _merge_llm_fallback(
    ocr_result: Dict[str, Any],
    llm_result: Dict[str, Any],
    missing_critical: List[str],
) -> Dict[str, Any]:
    """
    Merge LLM fallback results with OCR results.
    
    LLM results fill in missing critical fields only; does not overwrite OCR data.
    
    Args:
        ocr_result: Original OCR parsing result
        llm_result: LLM vision extraction result
        missing_critical: List of missing critical field names
    
    Returns:
        Merged recipe dict
    """
    merged = ocr_result.copy()
    
    # Only fill missing critical fields from LLM
    if "title" in missing_critical and llm_result.get("title"):
        merged["title"] = llm_result["title"]
        logger.info(f"Filled title from LLM: {llm_result['title'][:50]}")
    
    if "ingredients" in missing_critical and llm_result.get("ingredients"):
        merged["ingredients"] = llm_result["ingredients"]
        logger.info(f"Filled {len(llm_result['ingredients'])} ingredients from LLM")
    
    if "steps" in missing_critical and llm_result.get("steps"):
        merged["steps"] = llm_result["steps"]
        logger.info(f"Filled {len(llm_result['steps'])} steps from LLM")
    
    # Optional: fill non-critical fields if LLM has them
    if not merged.get("servings") and llm_result.get("servings"):
        merged["servings"] = llm_result["servings"]
    
    if not merged.get("times"):
        merged["times"] = {}
    
    if not merged["times"].get("prep_min") and llm_result.get("prep_time"):
        merged["times"]["prep_min"] = _parse_time_to_minutes(llm_result["prep_time"])
    
    if not merged["times"].get("cook_min") and llm_result.get("cook_time"):
        merged["times"]["cook_min"] = _parse_time_to_minutes(llm_result["cook_time"])
    
    if not merged["times"].get("total_min") and llm_result.get("total_time"):
        merged["times"]["total_min"] = _parse_time_to_minutes(llm_result["total_time"])
    
    return merged


def _parse_time_to_minutes(time_str: str) -> Optional[int]:
    """
    Parse time string (e.g. "30 minutes", "1 hour 30 min") to minutes.
    
    Args:
        time_str: Time string from LLM extraction
    
    Returns:
        Time in minutes, or None if cannot parse
    """
    if not time_str:
        return None
    
    time_str = time_str.lower().strip()
    total_minutes = 0
    
    # Parse hours
    hours_match = re.search(r"(\d+)\s*(?:hour|hr|h)", time_str)
    if hours_match:
        total_minutes += int(hours_match.group(1)) * 60
    
    # Parse minutes
    minutes_match = re.search(r"(\d+)\s*(?:minute|min|m)", time_str)
    if minutes_match:
        total_minutes += int(minutes_match.group(1))
    
    return total_minutes if total_minutes > 0 else None


def _generate_uuid() -> str:
    """Generate a UUID for recipe ID."""
    import uuid
    return str(uuid.uuid4())


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
    
    try:
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
        
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Normalize Job failed for recipe {recipe_id}: {e}", exc_info=True)
        return {
            "status": "failed",
            "recipe_id": recipe_id,
            "error": str(e),
        }


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


# ============================================================================
# ARQ Worker Configuration
# ============================================================================

try:
    from arq.connections import RedisSettings
    from config import settings
except ImportError:
    # Allow imports to work even if arq not installed (for development)
    RedisSettings = None
    settings = None


if RedisSettings and settings:
    async def startup(ctx: dict) -> None:
        """Called when worker starts."""
        logger.info("ARQ worker starting...")
        logger.info(f"Redis URL: {settings.REDIS_URL}")
        logger.info("Functions: ingest_recipe, structure_recipe, normalize_recipe")

    async def shutdown(ctx: dict) -> None:
        """Called when worker shuts down."""
        logger.info("ARQ worker shutting down...")

    class WorkerSettings:
        """
        ARQ worker configuration for background job processing.

        Start worker with:
            cd apps/api && python -m arq worker.jobs.WorkerSettings

        Environment variables:
            REDIS_URL: Redis connection URL (required)
            DATABASE_URL: PostgreSQL connection URL (required)
        """

        # Register async job functions
        functions = [ingest_recipe, structure_recipe, normalize_recipe]

        # Parse Redis URL from settings
        redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

        # Worker pool settings
        max_jobs = 10  # Max concurrent jobs
        job_timeout = 300  # 5 minutes max per job
        keep_result = 3600  # Keep results for 1 hour

        # Logging
        log_results = True
        handle_signals = True

        # Lifecycle hooks (async functions, not methods)
        on_startup = startup
        on_shutdown = shutdown
