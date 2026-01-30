"""
OCR service using PaddleOCR for text extraction.
Handles OCR processing with image preprocessing (orientation detection + rotation).
Returns structured OCRLine data.
"""
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO, List, Optional, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class OCRLineData:
    """Single OCR line result."""

    page: int
    text: str
    bbox: List[float]  # [x, y, width, height]
    confidence: float


class OCRService:
    """Service for OCR processing using PaddleOCR with preprocessing."""

    def __init__(self, use_gpu: bool = False, lang: str = "en", enable_rotation_detection: bool = True):
        """
        Initialize OCR service.
        Args:
            use_gpu: Use GPU acceleration (requires CUDA)
            lang: Language code (default: 'en')
            enable_rotation_detection: Enable Tesseract orientation detection (default: True)
        """
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            raise ImportError("Install PaddleOCR with: pip install paddleocr[all]")

        try:
            self.ocr = PaddleOCR(use_gpu=use_gpu, lang=lang)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "PaddleOCR init without use_gpu due to error: %s",
                exc,
            )
            self.ocr = PaddleOCR(lang=lang)
        self.use_gpu = use_gpu
        self.enable_rotation_detection = enable_rotation_detection

    def _detect_and_correct_rotation(self, image_path: str) -> Tuple[str, int]:
        """
        Detect image orientation using Tesseract + confidence voting.
        
        Uses 3 thresholding methods and majority voting to determine best rotation.
        Returns: (processed_image_path, rotation_degrees)
        
        Rotations: 0, 90, 180, 270 degrees.
        """
        if not self.enable_rotation_detection:
            return image_path, 0
        
        try:
            # Check if tesseract is available
            result = subprocess.run(["which", "tesseract"], capture_output=True, check=False)
            if result.returncode != 0:
                logger.warning("Tesseract not available; skipping rotation detection")
                return image_path, 0
        except Exception as e:
            logger.warning(f"Could not check for tesseract: {e}")
            return image_path, 0
        
        votes = {}
        
        # Try 3 thresholding methods for robust detection
        for method in [0, 1, 2]:
            try:
                result = subprocess.run(
                    ["tesseract", image_path, "stdout", "--psm", "0", 
                     "-c", f"thresholding_method={method}"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                
                # Parse Tesseract output for Rotate and Orientation confidence
                rotation = None
                confidence = None
                
                for line in result.stdout.split('\n'):
                    if 'Rotate:' in line:
                        try:
                            rotation = int(line.split()[-1])
                        except (ValueError, IndexError):
                            pass
                    if 'Orientation confidence:' in line:
                        try:
                            confidence = float(line.split()[-1])
                        except (ValueError, IndexError):
                            pass
                
                # Only count if confidence >= 3 (SPEC.md threshold)
                if rotation is not None and confidence is not None and confidence >= 3:
                    votes[rotation] = votes.get(rotation, 0) + 1
                    logger.debug(f"Tesseract method {method}: rotation={rotation}°, confidence={confidence}")
                elif rotation is not None:
                    logger.debug(f"Tesseract method {method}: rotation={rotation}°, confidence={confidence} (below threshold)")
            
            except subprocess.TimeoutExpired:
                logger.warning(f"Tesseract method {method} timed out")
            except Exception as e:
                logger.warning(f"Tesseract method {method} failed: {e}")
        
        # Majority vote on rotation
        if not votes:
            logger.info("No confident rotation detection; proceeding with original orientation")
            return image_path, 0
        
        best_rotation = max(votes, key=votes.get)
        logger.info(f"Detected rotation: {best_rotation}° (votes: {votes})")
        
        # Apply rotation using ImageMagick
        if best_rotation == 0:
            return image_path, 0
        
        try:
            rotated_path = str(Path(image_path).with_stem(f"{Path(image_path).stem}_rotated"))
            subprocess.run(
                ["convert", "-rotate", str(best_rotation), image_path, rotated_path],
                check=True,
                timeout=30,
            )
            logger.info(f"Applied {best_rotation}° rotation: {image_path} -> {rotated_path}")
            return rotated_path, best_rotation
        except subprocess.TimeoutExpired:
            logger.warning(f"ImageMagick rotation timed out; using original image")
            return image_path, 0
        except Exception as e:
            logger.warning(f"ImageMagick rotation failed: {e}; using original image")
            return image_path, 0

    def extract_text(self, file_data: BinaryIO, asset_type: str = "image") -> List[OCRLineData]:
        """
        Extract text from image/PDF using PaddleOCR with preprocessing.
        
        Steps:
        1. Save to temp file
        2. Detect and correct orientation (if image)
        3. Run OCR
        4. Parse results into OCRLineData
        
        Args:
            file_data: File-like object (image or PDF)
            asset_type: 'image' or 'pdf'
        Returns:
            List of OCRLineData objects
        """
        tmp_path = None
        rotated_path = None
        
        try:
            # Step 1: Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp_path = tmp.name
                tmp.write(file_data.read())
            
            ocr_image_path = tmp_path
            rotation_applied = 0
            
            # Step 2: Detect and correct orientation (if image)
            if self.enable_rotation_detection and asset_type == "image":
                ocr_image_path, rotation_applied = self._detect_and_correct_rotation(tmp_path)
                if rotation_applied != 0:
                    rotated_path = ocr_image_path
                    logger.info(f"Rotation detection applied {rotation_applied}° to {tmp_path}")
            
            # Step 3: Run OCR
            logger.debug(f"Running OCR on {ocr_image_path}")
            result = self.ocr.ocr(ocr_image_path, cls=True)
            
            if isinstance(result, tuple) and result:
                result = result[0]

            if isinstance(result, dict):
                logger.warning("OCR result keys: %s", list(result.keys()))
                result = (
                    result.get("data")
                    or result.get("res")
                    or result.get("lines")
                    or result.get("result")
                    or result.get("results")
                    or result.get("ocr_result")
                    or result.get("outputs")
                    or [result]
                )

            if not isinstance(result, list):
                logger.warning("Unexpected OCR result type: %s", type(result))
                logger.warning("OCR result repr: %s", _short_repr(result))
                return []

            if not result:
                logger.warning("OCR returned empty result list")
                return []

            sample = result[0]
            if isinstance(sample, dict):
                logger.warning("OCR result sample keys: %s", list(sample.keys()))
            else:
                logger.warning("OCR result sample type: %s", type(sample))

            # Step 4: Parse results into OCRLineData
            ocr_lines = []
            for page_idx, page_result in enumerate(result):
                if page_result is None:
                    continue

                if isinstance(page_result, dict) and "rec_texts" in page_result:
                    ocr_lines.extend(_lines_from_rec_output(page_idx, page_result))
                    continue

                page_items = page_result
                if isinstance(page_result, dict):
                    page_items = (
                        page_result.get("data")
                        or page_result.get("res")
                        or page_result.get("lines")
                        or page_result.get("result")
                        or page_result.get("results")
                        or page_result.get("ocr_result")
                        or page_result.get("outputs")
                        or [page_result]
                    )

                for line_result in page_items:
                    parsed = _parse_ocr_line(line_result)
                    if not parsed:
                        continue
                    text, bbox, confidence = parsed

                    ocr_lines.append(
                        OCRLineData(
                            page=page_idx,
                            text=text.strip(),
                            bbox=bbox,
                            confidence=float(confidence),
                        )
                    )

            logger.info(f"OCR extracted {len(ocr_lines)} lines from {tmp_path}")
            if not ocr_lines:
                logger.warning("OCR parsed 0 lines; sample result: %s", _short_repr(sample))
                first_page = result[0] if result else None
                if first_page is not None:
                    logger.warning("OCR first page repr: %s", _short_repr(first_page))
            return ocr_lines

        except Exception as e:
            logger.error(f"OCR failed: {e}", exc_info=True)
            raise

        finally:
            # Clean up temp files
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            if rotated_path and rotated_path != tmp_path and os.path.exists(rotated_path):
                os.unlink(rotated_path)


def _get_line_value(line_result, keys: list[str]):
    for key in keys:
        if isinstance(line_result, dict) and key in line_result:
            return line_result.get(key)
        if hasattr(line_result, key):
            return getattr(line_result, key)
    return None


def _normalize_bbox(bbox_coords):
    if bbox_coords is None:
        return None
    if hasattr(bbox_coords, "tolist"):
        bbox_coords = bbox_coords.tolist()
    if not bbox_coords:
        return None
    # Already [x, y, w, h]
    if (
        isinstance(bbox_coords, (list, tuple))
        and len(bbox_coords) == 4
        and all(isinstance(v, (int, float)) for v in bbox_coords)
    ):
        x, y, w, h = bbox_coords
        return [float(x), float(y), float(w), float(h)]
    # Polygon [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
    if isinstance(bbox_coords, (list, tuple)) and len(bbox_coords) >= 4:
        first = bbox_coords[0]
        third = bbox_coords[2]
        if (
            isinstance(first, (list, tuple))
            and isinstance(third, (list, tuple))
            and len(first) >= 2
            and len(third) >= 2
        ):
            x1, y1 = first[:2]
            x2, y2 = third[:2]
            return [float(x1), float(y1), float(x2 - x1), float(y2 - y1)]
    return None


def _short_repr(value, limit: int = 800) -> str:
    try:
        text = repr(value)
    except Exception:
        return "<unrepresentable>"
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def _parse_ocr_line(line_result):
    # Legacy PaddleOCR output: [bbox_coords, (text, confidence)]
    if isinstance(line_result, (list, tuple)) and len(line_result) >= 2:
        bbox_coords = line_result[0]
        text_conf = line_result[1]
        if isinstance(text_conf, (list, tuple)) and len(text_conf) >= 2:
            text = text_conf[0]
            confidence = text_conf[1]
            bbox = _normalize_bbox(bbox_coords)
            if text and bbox:
                return text, bbox, confidence

    # Dict/object output
    text = _get_line_value(line_result, ["text", "rec_text", "ocr_text", "value"])
    confidence = _get_line_value(line_result, ["confidence", "score", "rec_score"]) or 0.0
    bbox_coords = _get_line_value(line_result, ["bbox", "box", "points", "poly", "det_poly"])
    bbox = _normalize_bbox(bbox_coords)
    if text and bbox:
        return text, bbox, confidence
    return None


def _lines_from_rec_output(page_idx: int, page_result: dict) -> list[OCRLineData]:
    rec_texts = page_result.get("rec_texts") or []
    rec_scores = page_result.get("rec_scores") or []
    rec_polys = page_result.get("rec_polys") or page_result.get("rec_boxes") or []
    if not rec_polys:
        rec_polys = page_result.get("dt_polys") or []

    lines: list[OCRLineData] = []
    for idx, text in enumerate(rec_texts):
        if not text:
            continue
        bbox_coords = rec_polys[idx] if idx < len(rec_polys) else None
        bbox = _normalize_bbox(bbox_coords)
        if not bbox:
            continue
        confidence = rec_scores[idx] if idx < len(rec_scores) else 0.0
        lines.append(
            OCRLineData(
                page=page_idx,
                text=str(text).strip(),
                bbox=bbox,
                confidence=float(confidence),
            )
        )
    return lines


@lru_cache(maxsize=2)
def get_ocr_service(use_gpu: bool = False, lang: str = "en") -> OCRService:
    """Factory function to get a cached OCRService instance."""
    return OCRService(use_gpu=use_gpu, lang=lang)
