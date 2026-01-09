"""
OCR service using PaddleOCR for text extraction.
Handles OCR processing and returns structured OCRLine data.
"""
import logging
from dataclasses import dataclass
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

        self.ocr = PaddleOCR(use_gpu=use_gpu, lang=lang)
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
            # Run OCR
            result = self.ocr.ocr(tmp_path, cls=True)

            # Parse results
            ocr_lines = []
            for page_idx, page_result in enumerate(result):
                if page_result is None:
                    continue

                for line_result in page_result:
                    # line_result format: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]], (text, confidence)
                    bbox_coords, (text, confidence) = line_result

                    # Convert to [x, y, width, height] format
                    x1, y1 = bbox_coords[0]
                    x2, y2 = bbox_coords[2]
                    bbox = [float(x1), float(y1), float(x2 - x1), float(y2 - y1)]

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


def get_ocr_service(use_gpu: bool = False) -> OCRService:
    """Factory function to get OCRService instance."""
    return OCRService(use_gpu=use_gpu)
