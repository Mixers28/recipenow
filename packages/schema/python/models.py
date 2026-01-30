"""
RecipeNow Pydantic models (V1) — Canonical schema for all services.
All user-scoped entities include user_id for multi-user support.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MediaAsset(BaseModel):
    """Uploaded recipe image/PDF page."""
    id: Optional[UUID] = None
    user_id: UUID
    type: Literal["image", "pdf"]
    sha256: str = Field(..., description="Content hash for deduplication")
    storage_path: str = Field(..., description="Path to file (local or MinIO)")
    source_label: Optional[str] = Field(None, description="e.g. 'Cookbook photo'")
    created_at: Optional[datetime] = None

    class Config:
        json_encoders = {UUID: str, datetime: lambda v: v.isoformat() if v else None}


class OCRLine(BaseModel):
    """OCR-extracted text line/token with bounding box."""
    id: Optional[UUID] = None
    asset_id: UUID
    page: int = Field(0, description="Page number (0 for images)")
    text: str
    bbox: List[float] = Field(..., description="[x, y, width, height] in pixels")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: Optional[datetime] = None

    class Config:
        json_encoders = {UUID: str, datetime: lambda v: v.isoformat() if v else None}


class Times(BaseModel):
    """Recipe time breakdown (in minutes)."""
    prep_min: Optional[int] = None
    cook_min: Optional[int] = None
    total_min: Optional[int] = None


class Ingredient(BaseModel):
    """Recipe ingredient with optional normalized name."""
    id: Optional[UUID] = None
    original_text: str = Field(..., description="Immutable extracted text")
    name_norm: Optional[str] = Field(None, description="Normalized name (derived, editable)")
    quantity: Optional[float] = None
    unit: Optional[str] = None
    optional: bool = False

    class Config:
        json_encoders = {UUID: str}


class Step(BaseModel):
    """Recipe preparation step."""
    id: Optional[UUID] = None
    text: str

    class Config:
        json_encoders = {UUID: str}


class Nutrition(BaseModel):
    """Nutrition information (optional, user-approved)."""
    calories: Optional[int] = None
    estimated: bool = False
    approved_by_user: bool = False


class ServingsEstimate(BaseModel):
    """Derived servings estimate that requires explicit user approval."""
    value: Optional[int] = None
    confidence: Optional[float] = None
    basis: Optional[str] = None
    approved_by_user: bool = False


class Recipe(BaseModel):
    """Complete recipe with provenance tracking."""
    id: Optional[UUID] = None
    user_id: UUID
    title: Optional[str] = None
    servings: Optional[int] = None
    servings_estimate: Optional[ServingsEstimate] = None
    times: Optional[Times] = None
    ingredients: List[Ingredient] = Field(default_factory=list)
    steps: List[Step] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    nutrition: Optional[Nutrition] = None
    status: Literal["draft", "needs_review", "verified"] = "draft"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    class Config:
        json_encoders = {UUID: str, datetime: lambda v: v.isoformat() if v else None}


class SourceSpan(BaseModel):
    """Provenance: links a field to its OCR source."""
    id: Optional[UUID] = None
    recipe_id: UUID
    field_path: str = Field(..., description="e.g. 'title' or 'ingredients[2].original_text'")
    asset_id: UUID
    page: int = 0
    bbox: List[float] = Field(..., description="[x, y, width, height] in pixels")
    ocr_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extracted_text: Optional[str] = Field(None, description="The actual OCR text")
    source_method: Literal["ocr", "vision-api", "user"] = "ocr"
    evidence: Optional[dict] = Field(None, description="Evidence metadata, e.g., OCR line IDs")
    created_at: Optional[datetime] = None

    class Config:
        json_encoders = {UUID: str, datetime: lambda v: v.isoformat() if v else None}


class FieldStatus(BaseModel):
    """Field status badge (missing/extracted/user_entered/verified)."""
    id: Optional[UUID] = None
    recipe_id: UUID
    field_path: str
    status: Literal["missing", "extracted", "user_entered", "verified"]
    notes: Optional[str] = None

    class Config:
        json_encoders = {UUID: str}


class PantryItem(BaseModel):
    """User's pantry ingredient."""
    id: Optional[UUID] = None
    user_id: UUID
    name_original: str = Field(..., description="What user typed")
    name_norm: str = Field(..., description="Normalized for matching")
    quantity: Optional[float] = None
    unit: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        json_encoders = {UUID: str, datetime: lambda v: v.isoformat() if v else None}
