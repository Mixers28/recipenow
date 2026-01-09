"""
Background jobs for RecipeNow using ARQ.
Jobs: ingest (OCR), structure (parse), normalize.
"""
import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


# Type hints for imports used in jobs
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
except ImportError:
    pass  # Will be imported dynamically in job functions


async def ingest_job(asset_id: str, use_gpu: bool = False) -> dict:
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

    # Add packages to path for imports
    sys.path.insert(0, "/packages")

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
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            # Get asset from DB
            asset = db.query(MediaAsset).filter_by(id=UUID(asset_id)).first()
            if not asset:
                logger.error(f"Asset {asset_id} not found")
                return {"status": "failed", "error": "Asset not found"}

            # Retrieve file from storage
            storage = get_storage_backend()
            file_data = storage.get(asset.storage_path)
            file_bytes = BytesIO(file_data)

            # Run OCR
            ocr_service = get_ocr_service(use_gpu=use_gpu)
            ocr_lines_data = ocr_service.extract_text(file_bytes, asset_type=asset.type)

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
            logger.info(f"Stored {len(ocr_lines_data)} OCR lines for asset {asset_id}")

            return {
                "status": "success",
                "asset_id": asset_id,
                "line_count": len(ocr_lines_data),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Ingest job failed for asset {asset_id}: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
        }


async def structure_job(asset_id: str) -> dict:
    """
    Structure job: Parse OCRLines into Recipe draft with SourceSpans and FieldStatus.
    Args:
        asset_id: UUID of MediaAsset to structure
    Returns:
        Job result with recipe_id and field count
    """
    import os
    import sys
    from uuid import uuid4

    # Add packages to path for imports
    sys.path.insert(0, "/packages")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from api.db.models import MediaAsset, OCRLine as ORMOCRLine, Recipe, SourceSpan, FieldStatus
    from api.services.parser import RecipeParser, OCRLineData

    logger.info(f"Starting structure job for asset {asset_id}")

    try:
        # Get database session
        db_url = os.getenv("DATABASE_URL", "postgresql://recipenow:recipenow@postgres:5432/recipenow")
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            # Get asset from DB
            asset = db.query(MediaAsset).filter_by(id=UUID(asset_id)).first()
            if not asset:
                logger.error(f"Asset {asset_id} not found")
                return {"status": "failed", "error": "Asset not found"}

            # Retrieve OCRLines from DB
            ocr_lines = (
                db.query(ORMOCRLine)
                .filter_by(asset_id=UUID(asset_id))
                .order_by(ORMOCRLine.page, ORMOCRLine.id)
                .all()
            )

            if not ocr_lines:
                logger.warning(f"No OCR lines found for asset {asset_id}")
                return {
                    "status": "warning",
                    "message": "No OCR lines to structure",
                }

            # Convert ORM OCRLines to parser format
            parser_lines = [
                OCRLineData(
                    page=line.page,
                    text=line.text,
                    bbox=line.bbox,
                    confidence=line.confidence,
                )
                for line in ocr_lines
            ]

            # Parse OCRLines into recipe structure
            parser = RecipeParser()
            parse_result = parser.parse(parser_lines, str(asset_id))

            # Create Recipe record
            recipe_id = uuid4()
            recipe_data = parse_result["recipe"]

            recipe = Recipe(
                id=recipe_id,
                user_id=asset.user_id,
                title=recipe_data.get("title"),
                servings=recipe_data.get("servings"),
                ingredients=recipe_data.get("ingredients", []),
                steps=recipe_data.get("steps", []),
                tags=recipe_data.get("tags", []),
                status="draft",
            )
            db.add(recipe)
            db.flush()  # Get the recipe ID

            # Create SourceSpan records from parse result
            span_count = 0
            for span_data in parse_result.get("spans", []):
                span = SourceSpan(
                    id=uuid4(),
                    recipe_id=recipe_id,
                    field_path=span_data["field_path"],
                    asset_id=UUID(span_data.get("asset_id", asset_id)),
                    page=span_data["page"],
                    bbox=span_data["bbox"],
                    ocr_confidence=span_data["ocr_confidence"],
                    extracted_text=span_data["extracted_text"],
                )
                db.add(span)
                span_count += 1

            # Create FieldStatus records from parse result
            status_count = 0
            for status_data in parse_result.get("field_statuses", []):
                status = FieldStatus(
                    id=uuid4(),
                    recipe_id=recipe_id,
                    field_path=status_data["field_path"],
                    status=status_data["status"],
                    notes=status_data.get("notes"),
                )
                db.add(status)
                status_count += 1

            db.commit()
            logger.info(
                f"Structured asset {asset_id} into recipe {recipe_id} "
                f"with {span_count} spans and {status_count} field statuses"
            )

            return {
                "status": "success",
                "recipe_id": str(recipe_id),
                "asset_id": asset_id,
                "span_count": span_count,
                "field_status_count": status_count,
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Structure job failed for asset {asset_id}: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
        }


async def normalize_job(recipe_id: str) -> dict:
    """
    Normalize job: Compute name_norm for ingredients without altering original_text.
    Args:
        recipe_id: UUID of Recipe to normalize
    Returns:
        Job result with normalization count
    """
    import os
    import sys

    # Add packages to path for imports
    sys.path.insert(0, "/packages")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from api.db.models import Recipe, FieldStatus

    logger.info(f"Starting normalize job for recipe {recipe_id}")

    try:
        # Get database session
        db_url = os.getenv("DATABASE_URL", "postgresql://recipenow:recipenow@postgres:5432/recipenow")
        engine = create_engine(db_url)
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
JOBS = [ingest_job, structure_job, normalize_job]
