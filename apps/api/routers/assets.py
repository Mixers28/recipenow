"""
Assets router: upload, retrieve, and re-process recipe images/PDFs.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_session
from repositories.assets import AssetRepository
from repositories.recipes import RecipeRepository
from services.ocr import OCRLineData
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

        # Check for duplicates
        repo = AssetRepository(db)
        existing = repo.get_by_sha256(UUID(user_id), sha256)
        if existing:
            logger.info(f"File already uploaded: {existing.id}")
            # Create a new recipe for the duplicate asset
            recipe_repo = RecipeRepository(db)
            recipe = recipe_repo.create(
                user_id=UUID(user_id),
                title=f"Recipe from {file.filename}" if file.filename else "New Recipe",
                status="draft",
            )
            return AssetUploadResponse(
                asset_id=str(existing.id),
                recipe_id=str(recipe.id),
                storage_path=existing.storage_path,
                sha256=existing.sha256,
                source_label=existing.source_label,
            )

        # Store file
        storage = get_storage_backend()
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

        # Enqueue ingest job (OCR)
        try:
            from arq import create_pool

            arq = await create_pool()
            job = await arq.enqueue_job("ingest_job", str(asset.id), use_gpu=False)
            job_id = job.job_id if job else None
        except Exception as e:
            logger.warning(f"Failed to enqueue job: {e}")
            job_id = None

        logger.info(f"Asset uploaded: {asset.id}, queued job: {job_id}")

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


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: str, db: Session = Depends(get_session)) -> AssetResponse:
    """
    Get asset metadata by ID.
    Args:
        asset_id: Asset UUID
    Returns:
        Asset metadata
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
        logger.error(f"Get asset failed: {e}")
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
