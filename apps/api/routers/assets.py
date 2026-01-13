"""
Assets router: upload, retrieve, and re-process recipe images/PDFs.
"""
import logging
from io import BytesIO
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from db.models import OCRLine
from db.session import get_session
from repositories.assets import AssetRepository
from repositories.recipes import RecipeRepository
from services.ocr import OCRLineData, get_ocr_service
from services.storage import compute_sha256, get_storage_backend

logger = logging.getLogger(__name__)
router = APIRouter()


class AssetUploadResponse(BaseModel):
    """Response for asset upload."""

    asset_id: str
    recipe_id: str
    storage_path: str
    sha256: str
    job_id: Optional[str] = None


class AssetResponse(BaseModel):
    """Asset metadata response."""

    asset_id: str
    type: str
    sha256: str
    storage_path: str
    source_label: Optional[str] = None
    created_at: Optional[str] = None


class JobKickResponse(BaseModel):
    """Response for job enqueuing."""

    job_id: str
    status: str
    asset_id: str


@router.post("/upload", response_model=AssetUploadResponse)
async def upload_asset(
    file: UploadFile = File(...),
    source_label: Optional[str] = Form(None),
    user_id: str = Form(...),
    db: Session = Depends(get_session),
) -> AssetUploadResponse:
    """
    Upload a recipe image/PDF.
    Args:
        file: Recipe image or PDF file
        source_label: Optional label (e.g., 'Cookbook photo')
        user_id: User UUID uploading the file
    Returns:
        Asset metadata with storage info
    """
    try:
        # Determine file type
        if file.content_type == "application/pdf":
            asset_type = "pdf"
        elif file.content_type in ["image/jpeg", "image/png", "image/jpg"]:
            asset_type = "image"
        else:
            raise HTTPException(status_code=400, detail="Invalid file type. Use image (JPEG/PNG) or PDF.")

        # Read file and compute hash
        file_content = await file.read()
        from io import BytesIO

        file_bytes = BytesIO(file_content)
        sha256 = compute_sha256(file_bytes)

        storage = get_storage_backend()

        # Check for duplicates
        repo = AssetRepository(db)
        existing = repo.get_by_sha256(UUID(user_id), sha256)
        if existing:
            logger.info(f"File already uploaded: {existing.id}")

            # Ensure the file still exists in storage (handle cleaned volumes)
            if not storage.exists(existing.storage_path):
                logger.warning(
                    f"Asset record {existing.id} missing on disk at {existing.storage_path}; re-saving file."
                )
                file_bytes.seek(0)
                storage.save(file_bytes, existing.storage_path)

            # Create a new recipe for the duplicate asset
            recipe_repo = RecipeRepository(db)
            recipe = recipe_repo.create(
                user_id=UUID(user_id),
                title=f"Recipe from {file.filename}" if file.filename else "New Recipe",
                status="draft",
            )
            # Populate the new recipe using existing OCR lines
            _populate_recipe_from_ocr(db, str(existing.id), recipe)
            return AssetUploadResponse(
                asset_id=str(existing.id),
                recipe_id=str(recipe.id),
                storage_path=existing.storage_path,
                sha256=existing.sha256,
                source_label=existing.source_label,
            )

        # Store file
        storage_path = f"assets/{user_id}/{file.filename}"
        file_bytes.seek(0)
        storage.save(file_bytes, storage_path)

        # Create MediaAsset record
        asset = repo.create(
            user_id=UUID(user_id),
            asset_type=asset_type,
            sha256=sha256,
            storage_path=storage_path,
            source_label=source_label,
        )

        # Create initial recipe for this asset
        recipe_repo = RecipeRepository(db)
        recipe = recipe_repo.create(
            user_id=UUID(user_id),
            title=f"Recipe from {file.filename}" if file.filename else "New Recipe",
            status="draft",
        )
        logger.info(f"Recipe created: {recipe.id} for asset: {asset.id}")

        # Enqueue ingest job (OCR) or run synchronously if async jobs disabled
        job_id = None
        if settings.ENABLE_ASYNC_JOBS:
            try:
                from arq import create_pool

                redis_pool = await create_pool(settings.REDIS_URL)
                job = await redis_pool.enqueue_job("ingest_job", str(asset.id), use_gpu=False)
                job_id = job.job_id if job else None
                logger.info(f"Asset uploaded: {asset.id}, queued async job: {job_id}")
            except Exception as e:
                logger.warning(f"Failed to enqueue async job, falling back to sync OCR: {e}")
                # Fall back to synchronous OCR
                try:
                    _run_ocr_sync(db, str(asset.id))
                except Exception as ocr_error:
                    logger.error(f"Synchronous OCR failed: {ocr_error}", exc_info=True)
        else:
            # Run OCR synchronously (default for local/testing)
            try:
                _run_ocr_sync(db, str(asset.id))
                logger.info(f"Asset uploaded: {asset.id}, OCR completed synchronously")
            except Exception as e:
                logger.error(f"Failed to run OCR: {e}", exc_info=True)

        return AssetUploadResponse(
            asset_id=str(asset.id),
            recipe_id=str(recipe.id),
            storage_path=asset.storage_path,
            sha256=asset.sha256,
            job_id=job_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/{asset_id}")
def get_asset(asset_id: str, db: Session = Depends(get_session)):
    """
    Get asset file by ID.
    Returns the actual image/PDF file as binary data.
    Args:
        asset_id: Asset UUID
    Returns:
        File blob (image or PDF)
    """
    try:
        repo = AssetRepository(db)
        asset = repo.get_by_id(UUID(asset_id))

        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Retrieve file from storage
        storage = get_storage_backend()
        if not storage.exists(asset.storage_path):
            logger.error(f"Asset file missing at {asset.storage_path}")
            raise HTTPException(status_code=404, detail="Asset file missing on disk")

        file_data = storage.get(asset.storage_path)

        # Return as binary with appropriate content type
        media_type = "image/jpeg" if asset.type == "image" else "application/pdf"
        return StreamingResponse(
            BytesIO(file_data),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={asset.storage_path.split('/')[-1]}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get asset failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{asset_id}/metadata", response_model=AssetResponse)
def get_asset_metadata(asset_id: str, db: Session = Depends(get_session)) -> AssetResponse:
    """
    Get asset metadata by ID.
    Args:
        asset_id: Asset UUID
    Returns:
        Asset metadata (JSON)
    """
    try:
        repo = AssetRepository(db)
        asset = repo.get_by_id(UUID(asset_id))

        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        return AssetResponse(
            asset_id=str(asset.id),
            type=asset.type,
            sha256=asset.sha256,
            storage_path=asset.storage_path,
            source_label=asset.source_label,
            created_at=asset.created_at.isoformat() if asset.created_at else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get asset metadata failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{asset_id}/debug")
def debug_asset(asset_id: str, db: Session = Depends(get_session)):
    """
    Debug endpoint to inspect OCRLines and recipe data for an asset.
    Shows what was extracted during OCR and parsing.
    """
    try:
        from db.models import Recipe

        # Validate UUID format
        try:
            asset_uuid = UUID(asset_id)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid asset_id format. Expected UUID, got '{asset_id}'. Error: {str(e)}"
            )

        repo = AssetRepository(db)
        asset = repo.get_by_id(asset_uuid)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Get OCRLines
        ocr_lines = (
            db.query(OCRLine)
            .filter_by(asset_id=asset_uuid)
            .order_by(OCRLine.page, OCRLine.id)
            .all()
        )

        # Get recipe for this asset
        recipe = (
            db.query(Recipe)
            .filter_by(user_id=asset.user_id)
            .order_by(Recipe.created_at.desc())
            .first()
        )

        return {
            "asset_id": str(asset.id),
            "asset_type": asset.type,
            "ocr_line_count": len(ocr_lines),
            "ocr_lines": [
                {
                    "page": line.page,
                    "text": line.text[:100],  # First 100 chars
                    "confidence": line.confidence,
                    "bbox": line.bbox,
                }
                for line in ocr_lines[:20]  # First 20 lines
            ],
            "recipe": {
                "id": str(recipe.id) if recipe else None,
                "title": recipe.title if recipe else None,
                "servings": recipe.servings if recipe else None,
                "ingredients_count": len(recipe.ingredients) if recipe else 0,
                "ingredients": recipe.ingredients[:3] if recipe and recipe.ingredients else [],
                "steps_count": len(recipe.steps) if recipe else 0,
                "steps": recipe.steps[:2] if recipe and recipe.steps else [],
            },
            "message": "Debug info - use this to verify OCR extraction and parsing worked"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Debug failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{asset_id}/ocr", response_model=JobKickResponse)
async def run_ocr(asset_id: str, use_gpu: bool = False) -> JobKickResponse:
    """
    Re-run OCR on an asset.
    Args:
        asset_id: Asset UUID
        use_gpu: Use GPU acceleration
    Returns:
        Job info
    """
    try:
        from arq import create_pool

        arq = await create_pool()
        job = await arq.enqueue_job("ingest_job", asset_id, use_gpu=use_gpu)

        logger.info(f"Enqueued OCR job for asset {asset_id}: {job.job_id if job else 'unknown'}")

        return JobKickResponse(
            job_id=job.job_id if job else "unknown",
            status="queued",
            asset_id=asset_id,
        )

    except Exception as e:
        logger.error(f"Failed to enqueue OCR job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{asset_id}/structure", response_model=JobKickResponse)
async def run_structure(asset_id: str, page: Optional[int] = None) -> JobKickResponse:
    """
    Run structure job (parsing) on an asset.
    Args:
        asset_id: Asset UUID
        page: Optional page number (for PDFs)
    Returns:
        Job info
    """
    try:
        from arq import create_pool

        arq = await create_pool()
        job = await arq.enqueue_job("structure_job", asset_id)

        logger.info(f"Enqueued structure job for asset {asset_id}: {job.job_id if job else 'unknown'}")

        return JobKickResponse(
            job_id=job.job_id if job else "unknown",
            status="queued",
            asset_id=asset_id,
        )

    except Exception as e:
        logger.error(f"Failed to enqueue structure job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class NormalizeRecipeResponse(BaseModel):
    """Response for normalize operation."""

    recipe_id: str
    job_id: Optional[str] = None
    status: str = "queued"


@router.post("/recipes/{recipe_id}/normalize", response_model=NormalizeRecipeResponse)
async def normalize_recipe(recipe_id: str) -> NormalizeRecipeResponse:
    """
    Run normalize job on a recipe to compute name_norm for ingredients.
    Args:
        recipe_id: Recipe UUID
    Returns:
        Job info
    """
    try:
        from arq import create_pool

        arq = await create_pool()
        job = await arq.enqueue_job("normalize_job", recipe_id)

        logger.info(f"Enqueued normalize job for recipe {recipe_id}: {job.job_id if job else 'unknown'}")

        return NormalizeRecipeResponse(
            recipe_id=recipe_id,
            job_id=job.job_id if job else "unknown",
            status="queued",
        )

    except Exception as e:
        logger.error(f"Failed to enqueue normalize job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _run_ocr_sync(db: Session, asset_id: str) -> None:
    """
    Run OCR synchronously on an asset, then parse the results.
    Fallback when async jobs (arq/Redis) are not available.

    Args:
        db: Database session
        asset_id: Asset UUID string
    """
    try:
        # Get asset from DB
        repo = AssetRepository(db)
        asset = repo.get_by_id(UUID(asset_id))

        if not asset:
            logger.error(f"Asset {asset_id} not found for OCR")
            return

        # Retrieve file from storage
        storage = get_storage_backend()
        file_data = storage.get(asset.storage_path)
        file_bytes = BytesIO(file_data)

        # Run OCR
        ocr_service = get_ocr_service(use_gpu=False)
        ocr_lines_data = ocr_service.extract_text(file_bytes, asset_type=asset.type)

        # Store OCRLines in DB
        for line_data in ocr_lines_data:
            ocr_line = OCRLine(
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

        # Run structure parsing to populate recipe fields from OCRLines
        try:
            from db.models import Recipe

            recipe = (
                db.query(Recipe)
                .filter_by(user_id=asset.user_id)
                .order_by(Recipe.created_at.desc())
                .first()
            )
            if recipe:
                _populate_recipe_from_ocr(db, asset_id, recipe)
            else:
                logger.warning(f"Could not find recipe for asset {asset_id}")
        except Exception as parse_error:
            logger.error(f"Failed to parse recipe structure for asset {asset_id}: {parse_error}", exc_info=True)
            # Don't fail the upload if parsing fails - OCRLines were already stored

    except Exception as e:
        logger.error(f"Synchronous OCR failed for asset {asset_id}: {e}", exc_info=True)
        db.rollback()
        raise


def _populate_recipe_from_ocr(db: Session, asset_id: str, recipe) -> None:
    """
    Populate a recipe using existing OCR lines for the asset.
    If OCR lines are missing, this function exits early (upload flow is responsible for creating them).
    """
    try:
        from services.parser import RecipeParser
        from db.models import SourceSpan

        # Retrieve OCRLines for parsing
        ocr_lines = (
            db.query(OCRLine)
            .filter_by(asset_id=UUID(asset_id))
            .order_by(OCRLine.page, OCRLine.id)
            .all()
        )

        if not ocr_lines:
            logger.warning(f"No OCR lines found for parsing asset {asset_id}")
            return

        logger.info(f"Found {len(ocr_lines)} OCR lines for parsing asset {asset_id}")

        # Convert to parser format
        parser_lines = [
            OCRLineData(
                page=line.page,
                text=line.text,
                bbox=line.bbox,
                confidence=line.confidence,
            )
            for line in ocr_lines
        ]

        # Parse recipe structure
        parser = RecipeParser()
        parse_result = parser.parse(parser_lines, asset_id)
        recipe_data = parse_result.get("recipe", {})
        source_spans = parse_result.get("spans", [])

        logger.info(
            f"Parser returned recipe with title='{recipe_data.get('title')}', "
            f"ingredients={len(recipe_data.get('ingredients', []))}, "
            f"steps={len(recipe_data.get('steps', []))}"
        )

        # Update recipe with parsed data
        recipe.title = recipe_data.get("title") or recipe.title
        recipe.servings = recipe_data.get("servings")
        recipe.ingredients = recipe_data.get("ingredients", [])
        recipe.steps = recipe_data.get("steps", [])
        recipe.tags = recipe_data.get("tags", [])

        # Store source spans (if available)
        for span_data in source_spans:
            if isinstance(span_data, dict):
                source_span = SourceSpan(
                    id=uuid4(),
                    recipe_id=recipe.id,
                    asset_id=UUID(asset_id),
                    field_path=span_data.get("field_path", "unknown"),
                    page=span_data.get("page", 0),
                    bbox=span_data.get("bbox", [0, 0, 0, 0]),
                    ocr_confidence=span_data.get("confidence", 0.0),
                    extracted_text=span_data.get("extracted_text", ""),
                )
                db.add(source_span)

        db.commit()
        logger.info(
            f"Updated recipe {recipe.id} with parsed data from asset {asset_id}: "
            f"title='{recipe.title}', ingredients={len(recipe.ingredients)}, "
            f"steps={len(recipe.steps)}"
        )
    except Exception as parse_error:
        logger.error(
            f"Failed to parse recipe structure for asset {asset_id}: {parse_error}",
            exc_info=True,
        )
        db.rollback()
