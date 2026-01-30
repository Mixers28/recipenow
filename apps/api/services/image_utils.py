"""
Image processing utilities for RecipeNow.
Handles resizing and optimization for OCR/Vision API processing.
"""
import logging
from io import BytesIO
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)

# Configuration - these values balance quality with memory usage
MAX_DIMENSION = 2048  # Max width or height in pixels
JPEG_QUALITY = 85     # JPEG quality (1-100)
TARGET_DPI = 150      # Target DPI for recipe text readability


def resize_image_for_processing(
    file_bytes: BytesIO,
    max_dimension: int = MAX_DIMENSION,
    quality: int = JPEG_QUALITY,
) -> Tuple[BytesIO, dict]:
    """
    Resize image to reduce memory usage while retaining detail for OCR.

    Args:
        file_bytes: Input image as BytesIO
        max_dimension: Maximum width or height in pixels
        quality: JPEG quality (1-100)

    Returns:
        Tuple of (processed BytesIO, metadata dict)
        Metadata includes: original_size, new_size, was_resized, format
    """
    file_bytes.seek(0)

    try:
        img = Image.open(file_bytes)
        original_format = img.format or "JPEG"
        original_size = img.size
        was_resized = False

        # Convert RGBA to RGB if needed (for JPEG output)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Calculate new dimensions if image exceeds max
        width, height = img.size
        if width > max_dimension or height > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))

            # Use LANCZOS for high-quality downsampling
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            was_resized = True
            logger.info(
                f"Resized image from {original_size} to {img.size} "
                f"(max_dimension={max_dimension})"
            )

        # Save to BytesIO as JPEG (smaller than PNG, good for photos)
        output = BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        output.seek(0)

        metadata = {
            "original_size": original_size,
            "new_size": img.size,
            "was_resized": was_resized,
            "original_format": original_format,
            "output_format": "JPEG",
            "quality": quality,
        }

        return output, metadata

    except Exception as e:
        logger.error(f"Image resize failed: {e}")
        # Return original on failure
        file_bytes.seek(0)
        return file_bytes, {
            "error": str(e),
            "was_resized": False,
        }


def get_image_info(file_bytes: BytesIO) -> dict:
    """
    Get image metadata without modifying it.

    Args:
        file_bytes: Image as BytesIO

    Returns:
        Dict with size, format, mode, file_size_kb
    """
    file_bytes.seek(0)
    file_size = len(file_bytes.read())
    file_bytes.seek(0)

    try:
        img = Image.open(file_bytes)
        return {
            "width": img.size[0],
            "height": img.size[1],
            "format": img.format,
            "mode": img.mode,
            "file_size_kb": round(file_size / 1024, 1),
        }
    except Exception as e:
        return {
            "error": str(e),
            "file_size_kb": round(file_size / 1024, 1),
        }
