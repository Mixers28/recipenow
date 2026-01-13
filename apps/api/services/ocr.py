"""
OCR service using PaddleOCR for text extraction.
Handles OCR processing and returns structured OCRLine data.
"""
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import BinaryIO, List, Optional
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
    """Service for OCR processing using PaddleOCR."""

    def __init__(self, use_gpu: bool = False, lang: str = "en"):
        """
        Initialize OCR service.
        Args:
            use_gpu: Use GPU acceleration (requires CUDA)
            lang: Language code (default: 'en')
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

    def extract_text(self, file_data: BinaryIO, asset_type: str = "image") -> List[OCRLineData]:
        """
        Extract text from image/PDF using PaddleOCR.
        Args:
            file_data: File-like object (image or PDF)
            asset_type: 'image' or 'pdf'
        Returns:
            List of OCRLineData objects
        """
        import tempfile

        # Save to temp file (PaddleOCR works with file paths)
        with tempfile.NamedTemporaryFile(suffix=".jpg" if asset_type == "image" else ".pdf", delete=False) as tmp:
            tmp.write(file_data.read())
            tmp_path = tmp.name

        try:
            # Run OCR (older PaddleOCR supports cls, newer pipelines do not)
            try:
                result = self.ocr.ocr(tmp_path, cls=True)
            except TypeError as exc:
                logger.warning("PaddleOCR.ocr() without cls due to error: %s", exc)
                result = self.ocr.ocr(tmp_path)

            if isinstance(result, dict):
                result = [result]

            if not isinstance(result, list):
                logger.warning("Unexpected OCR result type: %s", type(result))
                return []

            if result:
                sample = result[0]
                if isinstance(sample, dict):
                    logger.info("OCR result sample keys: %s", list(sample.keys()))
                else:
                    logger.info("OCR result sample type: %s", type(sample))

            # Parse results
            ocr_lines = []
            for page_idx, page_result in enumerate(result):
                if page_result is None:
                    continue

                page_items = page_result
                if isinstance(page_result, dict):
                    page_items = (
                        page_result.get("data")
                        or page_result.get("res")
                        or page_result.get("lines")
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
            return ocr_lines

        except Exception as e:
            logger.error(f"OCR failed for {tmp_path}: {e}")
            raise

        finally:
            # Clean up temp file
            import os

            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


def _get_line_value(line_result, keys: list[str]):
    for key in keys:
        if isinstance(line_result, dict) and key in line_result:
            return line_result.get(key)
        if hasattr(line_result, key):
            return getattr(line_result, key)
    return None


def _normalize_bbox(bbox_coords):
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


@lru_cache(maxsize=2)
def get_ocr_service(use_gpu: bool = False, lang: str = "en") -> OCRService:
    """Factory function to get a cached OCRService instance."""
    return OCRService(use_gpu=use_gpu, lang=lang)
