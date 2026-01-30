"""
Background jobs for RecipeNow using ARQ.
Jobs: ingest (OCR), structure (parse), normalize.
"""
import logging
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


def _union_bboxes(bboxes: list[list[float]]) -> list[float]:
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
    evidence_ids: list[str],
    ocr_line_map: dict[str, Any],
    asset_id: str,
    source_method: str = "vision-api",
) -> Optional[dict]:
    """Build span from ORM objects (used by ingest_job)."""
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


def _build_span_from_evidence_dict(
    field_path: str,
    extracted_text: str,
    evidence_ids: list[str],
    ocr_line_map: dict[str, dict],
    asset_id: str,
    source_method: str = "vision-api",
) -> Optional[dict]:
    """Build span from plain dicts (used by extract_job to avoid detached ORM instances)."""
    evidence_ids = [str(eid) for eid in evidence_ids or []]
    lines = [ocr_line_map[eid] for eid in evidence_ids if eid in ocr_line_map]
    if not lines:
        return None
    bboxes = [line["bbox"] for line in lines]
    bbox = _union_bboxes(bboxes)
    page = lines[0]["page"]
    confidence = sum(line["confidence"] for line in lines) / len(lines)
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


def _vision_to_recipe_payload(vision_result: dict) -> dict:
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


def _build_field_statuses(recipe_data: dict) -> list[dict]:
    statuses: list[dict] = []

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


# Type hints for imports used in jobs
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
except ImportError:
    pass  # Will be imported dynamically in job functions


async def ingest_job(
    ctx,
    asset_id: str,
    use_gpu: bool = False,
    user_id: Optional[str] = None,
    recipe_id: Optional[str] = None,
    file_data: Optional[bytes] = None,
    asset_type: str = "image",
) -> dict:
    """
    Ingest job: OCR an uploaded asset and store OCRLines.
    Args:
        asset_id: UUID of MediaAsset to process
        use_gpu: Use GPU acceleration for OCR
    Returns:
        Job result with status and line count
    """
    import os
    import sys
    from io import BytesIO

    # Add packages and api code to path for imports
    sys.path.insert(0, "/app/packages")
    sys.path.insert(0, "/app/apps")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from schema.python.models import OCRLine as PydanticOCRLine
    from api.db.models import MediaAsset, OCRLine as ORMOCRLine
    from api.services.ocr import get_ocr_service
    from api.services.storage import get_storage_backend

    logger.info(f"Starting ingest job for asset {asset_id}")

    try:
        # Get database session
        db_url = os.getenv("DATABASE_URL", "postgresql://recipenow:recipenow@postgres:5432/recipenow")
        engine = create_engine(db_url, connect_args={"prepare_threshold": None})
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            # Get asset from DB
            asset = db.query(MediaAsset).filter_by(id=UUID(asset_id)).first()
            if not asset:
                logger.error(f"Asset {asset_id} not found")
                return {"status": "failed", "error": "Asset not found"}

            if file_data is None:
                storage = get_storage_backend()
                file_data = storage.get(asset.storage_path)
            file_bytes = BytesIO(file_data)

            # Run OCR
            ocr_service = get_ocr_service(use_gpu=use_gpu)
            ocr_lines_data = ocr_service.extract_text(file_bytes, asset_type=asset_type or asset.type)

            # Store OCRLines in DB
            from uuid import uuid4

            for line_data in ocr_lines_data:
                ocr_line = ORMOCRLine(
                    id=uuid4(),
                    asset_id=UUID(asset_id),
                    page=line_data.page,
                    text=line_data.text,
                    bbox=line_data.bbox,
                    confidence=line_data.confidence,
                )
                db.add(ocr_line)

            db.commit()
            line_count = len(ocr_lines_data)
            logger.info(f"Stored {line_count} OCR lines for asset {asset_id}")

            # Clear OCR references to free memory before queueing extract job
            del ocr_lines_data
            del ocr_service
            import gc
            gc.collect()
            logger.info("Freed OCR memory")

            # Queue extract_job as separate job to allow memory cleanup between jobs
            if recipe_id:
                logger.info(f"Queueing extract_job for recipe {recipe_id}")
                # Use ctx["redis"] to enqueue the next job
                await ctx["redis"].enqueue_job(
                    "extract_job",
                    str(asset.id),
                    str(user_id or asset.user_id),
                    str(recipe_id),
                    file_data,  # Pass image bytes to avoid re-reading from storage
                )

            return {
                "status": "success",
                "asset_id": asset_id,
                "line_count": line_count,
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Ingest job failed for asset {asset_id}: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
        }


async def extract_job(
    ctx,
    asset_id: str,
    user_id: str,
    recipe_id: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
) -> dict:
    """
    Vision-primary extract job: uses OCRLines + image to populate recipe draft.

    NOTE: This job uses two separate database sessions to avoid connection timeouts
    during the long-running Vision API call (~60s). Supabase's PgBouncer in transaction
    mode will kill idle connections, so we:
    1. Open session 1 to fetch asset/OCR data, then close it
    2. Make the Vision API call (no DB connection held)
    3. Open session 2 to save the results
    """
    import gc
    import os
    import sys
    from uuid import uuid4

    # Force garbage collection to free any leftover memory from previous jobs
    gc.collect()
    logger.info(f"Starting extract job for asset {asset_id} (memory cleaned)")

    # Add packages and api code to path for imports
    sys.path.insert(0, "/app/packages")
    sys.path.insert(0, "/app/apps")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from api.db.models import MediaAsset, OCRLine as ORMOCRLine, Recipe, SourceSpan, FieldStatus
    from api.services.llm_vision import get_llm_vision_service
    from api.services.parser import RecipeParser, OCRLineData
    from api.services.storage import get_storage_backend

    try:
        db_url = os.getenv("DATABASE_URL", "postgresql://recipenow:recipenow@postgres:5432/recipenow")
        engine = create_engine(db_url, connect_args={"prepare_threshold": None})
        SessionLocal = sessionmaker(bind=engine)

        # ============================================================
        # PHASE 1: Fetch data from DB (short-lived connection)
        # ============================================================
        logger.info(f"[Phase 1] Fetching asset and OCR data for {asset_id}")
        db = SessionLocal()
        try:
            asset = db.query(MediaAsset).filter_by(id=UUID(asset_id)).first()
            if not asset:
                logger.error(f"Asset {asset_id} not found")
                return {"status": "failed", "error": "Asset not found"}

            # Store asset info we need for later
            asset_user_id = asset.user_id
            asset_storage_path = asset.storage_path

            ocr_lines = (
                db.query(ORMOCRLine)
                .filter_by(asset_id=UUID(asset_id))
                .order_by(ORMOCRLine.page, ORMOCRLine.id)
                .all()
            )
            if not ocr_lines:
                return {"status": "failed", "error": "No OCR lines found"}

            # Build data structures we need for vision extraction
            # Store as plain dicts to avoid detached instance issues
            ocr_line_data = [
                {
                    "id": str(line.id),
                    "text": line.text,
                    "page": line.page,
                    "bbox": line.bbox,
                    "confidence": line.confidence,
                }
                for line in ocr_lines
            ]
            ocr_line_map = {d["id"]: d for d in ocr_line_data}
            ocr_lines_payload = [
                {"id": d["id"], "text": d["text"], "page": d["page"]}
                for d in ocr_line_data
            ]

            if image_bytes is None:
                storage = get_storage_backend()
                image_bytes = storage.get(asset_storage_path)

            logger.info(f"[Phase 1] Fetched {len(ocr_line_data)} OCR lines, closing DB connection")
        finally:
            db.close()

        # ============================================================
        # PHASE 2: Call Vision API (no DB connection held)
        # ============================================================
        logger.info(f"[Phase 2] Calling Vision API for {asset_id} (DB connection closed)")

        try:
            vision_service = get_llm_vision_service()
            logger.info(f"[DEBUG] Calling OpenAI Vision API for asset {asset_id}...")
            vision_result = vision_service.extract_with_evidence(image_bytes, ocr_lines_payload)
            logger.info(f"[DEBUG] Vision API returned: title={vision_result.get('title')}, ingredients={len(vision_result.get('ingredients', []))}, steps={len(vision_result.get('steps', []))}")
            recipe_data = _vision_to_recipe_payload(vision_result)
            logger.info(f"[DEBUG] Parsed recipe_data: title={recipe_data.get('title')}, ingredients={len(recipe_data.get('ingredients', []))}, steps={len(recipe_data.get('steps', []))}")
            field_statuses = _build_field_statuses(recipe_data)

            spans: list[dict] = []
            title = vision_result.get("title") or {}
            if isinstance(title, dict) and title.get("text"):
                span = _build_span_from_evidence_dict(
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
                span = _build_span_from_evidence_dict(
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
                span = _build_span_from_evidence_dict(
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
                span = _build_span_from_evidence_dict(
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
                        span = _build_span_from_evidence_dict(
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
                    page=d["page"],
                    text=d["text"],
                    bbox=d["bbox"],
                    confidence=d["confidence"],
                )
                for d in ocr_line_data
            ]
            parser = RecipeParser()
            parse_result = parser.parse(parser_lines, str(asset_id))
            recipe_data = parse_result.get("recipe", {})
            spans = parse_result.get("spans", [])
            field_statuses = parse_result.get("field_statuses", [])
            for span in spans:
                span["source_method"] = "ocr"

        # ============================================================
        # PHASE 3: Save results to DB (fresh connection)
        # ============================================================
        logger.info(f"[Phase 3] Saving results to DB for {asset_id}")
        db = SessionLocal()
        try:
            logger.info(f"[DEBUG] Starting recipe update for recipe_id={recipe_id}")
            recipe = db.query(Recipe).filter_by(id=UUID(recipe_id)).first() if recipe_id else None
            if not recipe:
                recipe = Recipe(
                    id=uuid4(),
                    user_id=asset_user_id,
                    title=recipe_data.get("title"),
                    servings=recipe_data.get("servings"),
                    ingredients=recipe_data.get("ingredients", []),
                    steps=recipe_data.get("steps", []),
                    tags=recipe_data.get("tags", []),
                    status="draft",
                )
                db.add(recipe)
                db.flush()
            else:
                recipe.title = recipe_data.get("title")
                recipe.servings = recipe_data.get("servings")
                recipe.ingredients = recipe_data.get("ingredients", [])
                recipe.steps = recipe_data.get("steps", [])
                recipe.tags = recipe_data.get("tags", [])

            db.query(SourceSpan).filter_by(recipe_id=recipe.id).delete()
            db.query(FieldStatus).filter_by(recipe_id=recipe.id).delete()

            for span in spans:
                db.add(
                    SourceSpan(
                        id=uuid4(),
                        recipe_id=recipe.id,
                        field_path=span.get("field_path"),
                        asset_id=UUID(span.get("asset_id", asset_id)),
                        page=span.get("page", 0),
                        bbox=span.get("bbox"),
                        ocr_confidence=span.get("confidence", span.get("ocr_confidence", 0.0)),
                        extracted_text=span.get("extracted_text"),
                        source_method=span.get("source_method", "ocr"),
                        evidence=span.get("evidence"),
                    )
                )

            for status in field_statuses:
                db.add(
                    FieldStatus(
                        id=uuid4(),
                        recipe_id=recipe.id,
                        field_path=status.get("field_path"),
                        status=status.get("status"),
                        notes=status.get("notes"),
                    )
                )

            logger.info(f"[DEBUG] Committing recipe {recipe.id} with {len(recipe_data.get('ingredients', []))} ingredients, {len(recipe_data.get('steps', []))} steps")
            db.commit()
            logger.info(f"[DEBUG] Commit successful for recipe {recipe.id}")
            return {"status": "success", "recipe_id": str(recipe.id)}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Extract job failed for asset {asset_id}: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


async def structure_job(ctx, asset_id: str) -> dict:
    """
    Legacy structure job retained for compatibility.
    Delegates to vision-primary extract job.
    """
    logger.info("Structure job is deprecated; delegating to extract_job.")
    return await extract_job(asset_id=asset_id, user_id="", recipe_id=None)


async def normalize_job(ctx, recipe_id: str) -> dict:
    """
    Normalize job: Compute name_norm for ingredients without altering original_text.
    Args:
        recipe_id: UUID of Recipe to normalize
    Returns:
        Job result with normalization count
    """
    import os
    import sys

    # Add packages and api code to path for imports
    sys.path.insert(0, "/app/packages")
    sys.path.insert(0, "/app/apps")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from api.db.models import Recipe, FieldStatus

    logger.info(f"Starting normalize job for recipe {recipe_id}")

    try:
        # Get database session
        db_url = os.getenv("DATABASE_URL", "postgresql://recipenow:recipenow@postgres:5432/recipenow")
        engine = create_engine(db_url, connect_args={"prepare_threshold": None})
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            # Get recipe from DB
            recipe = db.query(Recipe).filter_by(id=UUID(recipe_id)).first()
            if not recipe:
                logger.error(f"Recipe {recipe_id} not found")
                return {"status": "failed", "error": "Recipe not found"}

            # Normalize ingredients
            normalized_count = 0
            for i, ingredient in enumerate(recipe.ingredients or []):
                if not ingredient.get("name_norm"):
                    # Extract name from original_text
                    original_text = ingredient.get("original_text", "")
                    name_norm = _extract_ingredient_name(original_text)

                    if name_norm:
                        ingredient["name_norm"] = name_norm
                        normalized_count += 1
                        logger.debug(f"Normalized ingredient {i}: {original_text} -> {name_norm}")

            # Update recipe
            recipe.ingredients = recipe.ingredients  # Trigger update
            db.commit()

            logger.info(f"Normalized {normalized_count} ingredients for recipe {recipe_id}")

            return {
                "status": "success",
                "recipe_id": recipe_id,
                "normalized_count": normalized_count,
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Normalize job failed for recipe {recipe_id}: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
        }


def _extract_ingredient_name(original_text: str) -> Optional[str]:
    """
    Extract normalized ingredient name from original text.
    Examples:
        "2 cups all-purpose flour" -> "flour"
        "3 large eggs" -> "egg"
        "salt and pepper to taste" -> "salt and pepper"
    """
    if not original_text:
        return None

    # Remove leading quantity/unit patterns
    text = original_text.strip()
    text = __import__("re").sub(r"^[\d\s\-/\.]*\s*([a-z]*)\s+", "", text, flags=__import__("re").IGNORECASE)

    # Remove trailing notes in parentheses or after comma
    text = __import__("re").sub(r"\s*\(.*?\)\s*", " ", text)
    text = __import__("re").sub(r"\s*,.*$", "", text)

    # Remove common descriptors (optional, to taste, etc.)
    text = __import__("re").sub(
        r"\s*(optional|to taste|if desired|fresh|dried|ground|powdered)\s*",
        " ",
        text,
        flags=__import__("re").IGNORECASE,
    )

    text = text.strip()

    # Singularize common plurals
    if text.endswith("es"):
        singular = text[:-2]
        if singular in {"tomato", "potato", "onion", "carrot"}:
            text = singular
    elif text.endswith("s") and not text.endswith("ss"):
        singular = text[:-1]
        if singular in {"egg", "cup", "tablespoon", "teaspoon", "ounce", "pound"}:
            text = singular

    return text.lower() if text else None


# ARQ job registry
JOBS = [ingest_job, extract_job, structure_job, normalize_job]
