"""
Deterministic recipe parser for structured extraction from OCRLines.
Uses heuristics to detect recipe blocks (title, ingredients, steps) and extract fields.
"""
import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ParsedField:
    """Represents a parsed field with provenance info."""

    field_path: str
    value: any
    asset_id: str
    page: int
    bbox: List[int]
    extracted_text: str
    confidence: float
    status: str = "extracted"


@dataclass
class OCRLineData:
    """OCR line with text, bbox, and confidence."""

    page: int
    text: str
    bbox: List[int]  # [x, y, w, h]
    confidence: float


class RecipeParser:
    """
    Deterministic parser for extracting recipe data from OCRLines.
    Uses keyword-based heuristics to detect and extract recipe sections.
    """

    # Keywords for detecting recipe sections
    TITLE_INDICATORS = {"recipe", "title", "name"}
    INGREDIENT_INDICATORS = {
        "ingredient",
        "ingredients",
        "what",
        "you",
        "need",
        "component",
        "supplies",
    }
    STEPS_INDICATORS = {
        "instruction",
        "instructions",
        "method",
        "preparation",
        "procedure",
        "direction",
        "directions",
        "steps",
        "step",
    }
    TIME_INDICATORS = {
        "prep",
        "preparation",
        "cook",
        "cooking",
        "bake",
        "baking",
        "total",
        "time",
        "minutes",
        "mins",
        "hours",
        "hrs",
    }
    SERVINGS_INDICATORS = {"serve", "serving", "servings", "yield", "portion", "people"}

    def __init__(self):
        """Initialize parser with compiled regex patterns."""
        # Pattern for extracting quantities from ingredient lines
        self.quantity_pattern = re.compile(
            r"^\s*([\d\s\-/\.]+)\s*([a-z]+)?\s+(.+?)(?:\s*\(.*\))?\s*$", re.IGNORECASE
        )
        # Pattern for detecting time values
        self.time_pattern = re.compile(r"(\d+)\s*(minute|min|hour|hr|second|sec)", re.IGNORECASE)
        # Pattern for detecting servings
        self.servings_pattern = re.compile(r"(?:serve|serving|yield)s?\s*(?:of\s*)?(\d+)", re.IGNORECASE)

    def parse(self, ocr_lines: List[OCRLineData], asset_id: str) -> dict:
        """
        Parse OCRLines into a recipe structure with provenance.

        Args:
            ocr_lines: List of OCRLineData from OCR service
            asset_id: UUID of the asset being parsed

        Returns:
            dict with recipe draft, source spans, and field statuses
        """
        if not ocr_lines:
            logger.warning(f"No OCR lines to parse for asset {asset_id}")
            return {
                "recipe": {
                    "title": None,
                    "servings": None,
                    "times": {"prep_min": None, "cook_min": None, "total_min": None},
                    "ingredients": [],
                    "steps": [],
                    "tags": [],
                },
                "spans": [],
                "field_statuses": [],
            }

        # Combine all OCR text for analysis
        full_text = "\n".join(line.text for line in ocr_lines)
        logger.info(f"Parsing {len(ocr_lines)} OCR lines for asset {asset_id}")

        # Detect recipe sections
        sections = self._detect_sections(ocr_lines)
        logger.debug(f"Detected sections: {sections}")

        # Extract fields from sections
        recipe = {
            "title": None,
            "servings": None,
            "times": {"prep_min": None, "cook_min": None, "total_min": None},
            "ingredients": [],
            "steps": [],
            "tags": [],
        }
        spans = []
        field_statuses = []

        # Extract title (usually first non-header line or detected via keywords)
        title_result = self._extract_title(ocr_lines, sections.get("title_indices", []))
        if title_result:
            recipe["title"], span, status = title_result
            spans.append(span)
            field_statuses.append(status)
        else:
            field_statuses.append(
                {
                    "field_path": "title",
                    "status": "missing",
                    "notes": "Could not detect title in OCR text",
                }
            )

        # Extract ingredients
        ingredient_results = self._extract_ingredients(
            ocr_lines, sections.get("ingredients_indices", []), asset_id
        )
        recipe["ingredients"] = [r[0] for r in ingredient_results]
        spans.extend([r[1] for r in ingredient_results if r[1]])
        field_statuses.extend([r[2] for r in ingredient_results if r[2]])

        if not ingredient_results:
            field_statuses.append(
                {
                    "field_path": "ingredients",
                    "status": "missing",
                    "notes": "Could not detect ingredients section",
                }
            )

        # Extract steps
        step_results = self._extract_steps(ocr_lines, sections.get("steps_indices", []), asset_id)
        recipe["steps"] = [r[0] for r in step_results]
        spans.extend([r[1] for r in step_results if r[1]])
        field_statuses.extend([r[2] for r in step_results if r[2]])

        if not step_results:
            field_statuses.append(
                {
                    "field_path": "steps",
                    "status": "missing",
                    "notes": "Could not detect steps section",
                }
            )

        # Extract times and servings (look in full text for now)
        servings_result = self._extract_servings(ocr_lines, asset_id)
        if servings_result:
            recipe["servings"], span, status = servings_result
            spans.append(span)
            field_statuses.append(status)
        else:
            field_statuses.append(
                {
                    "field_path": "servings",
                    "status": "missing",
                    "notes": "Servings not found in OCR text",
                }
            )

        return {
            "recipe": recipe,
            "spans": spans,
            "field_statuses": field_statuses,
        }

    def _detect_sections(self, ocr_lines: List[OCRLineData]) -> dict:
        """
        Detect recipe sections (title, ingredients, steps) based on keywords.

        Returns:
            dict with section boundaries (line indices)
        """
        sections = {
            "title_indices": [],
            "ingredients_indices": [],
            "steps_indices": [],
        }

        for i, line in enumerate(ocr_lines):
            lower_text = line.text.lower().strip()

            # Check for section headers
            if any(ind in lower_text for ind in self.INGREDIENT_INDICATORS):
                sections["ingredients_indices"].append(i)

            if any(ind in lower_text for ind in self.STEPS_INDICATORS):
                sections["steps_indices"].append(i)

            if any(ind in lower_text for ind in self.TITLE_INDICATORS):
                sections["title_indices"].append(i)

        # If no explicit indicators found, use heuristics
        if not sections["title_indices"] and ocr_lines:
            # Usually title is near the top
            sections["title_indices"] = [0]

        return sections

    def _extract_title(self, ocr_lines: List[OCRLineData], title_indices: List[int]) -> Optional[Tuple]:
        """
        Extract recipe title from OCRLines.

        Returns:
            Tuple of (title_text, span_dict, field_status_dict) or None
        """
        if not ocr_lines:
            return None

        # If we found explicit title indicators, use the line after
        if title_indices:
            idx = title_indices[0]
            if idx + 1 < len(ocr_lines):
                line = ocr_lines[idx + 1]
            else:
                line = ocr_lines[idx]
        else:
            # Otherwise use first substantive line (not too short, not keywords)
            line = ocr_lines[0]
            for candidate in ocr_lines[:5]:
                if len(candidate.text.strip()) > 3 and len(candidate.text.split()) >= 2:
                    line = candidate
                    break

        if not line.text.strip():
            return None

        title_text = line.text.strip()

        span = {
            "field_path": "title",
            "asset_id": "TBD",  # Will be filled by caller
            "page": line.page,
            "bbox": line.bbox,
            "ocr_confidence": line.confidence,
            "extracted_text": title_text,
        }

        status = {
            "field_path": "title",
            "status": "extracted",
        }

        return (title_text, span, status)

    def _extract_ingredients(
        self, ocr_lines: List[OCRLineData], ingredient_indices: List[int], asset_id: str
    ) -> List[Tuple]:
        """
        Extract ingredients from OCRLines.

        Returns:
            List of tuples: (ingredient_dict, span_dict, field_status_dict)
        """
        ingredients = []

        # Find ingredient section start
        start_idx = 0
        if ingredient_indices:
            start_idx = ingredient_indices[0] + 1

        # Find section end (next section header or end of lines)
        end_idx = len(ocr_lines)

        # Parse lines in ingredient section
        for idx in range(start_idx, end_idx):
            line = ocr_lines[idx]
            text = line.text.strip()

            # Skip empty lines and section headers
            if not text or any(ind in text.lower() for ind in self.STEPS_INDICATORS):
                break

            # Skip if looks like a section header
            if any(ind in text.lower() for ind in self.INGREDIENT_INDICATORS):
                continue

            # Try to parse ingredient
            ingredient = self._parse_ingredient_line(text)
            if ingredient:
                ingredient["original_text"] = text

                span = {
                    "field_path": f"ingredients[{len(ingredients)}].original_text",
                    "asset_id": asset_id,
                    "page": line.page,
                    "bbox": line.bbox,
                    "ocr_confidence": line.confidence,
                    "extracted_text": text,
                }

                status = {
                    "field_path": f"ingredients[{len(ingredients)}].original_text",
                    "status": "extracted",
                }

                ingredients.append((ingredient, span, status))

        return ingredients

    def _parse_ingredient_line(self, text: str) -> Optional[dict]:
        """
        Parse a single ingredient line into components.

        Returns:
            dict with quantity, unit, original_text, optional fields
        """
        text = text.strip()
        if not text:
            return None

        # Remove leading bullets/numbers
        text = re.sub(r"^[\d\.\-\*•\s]+", "", text).strip()

        ingredient = {
            "quantity": None,
            "unit": None,
            "optional": "optional" in text.lower(),
        }

        # Try to extract quantity and unit
        match = self.quantity_pattern.match(text)
        if match:
            qty_str, unit, name = match.groups()
            try:
                # Try to parse quantity as a number or fraction
                qty_val = self._parse_quantity(qty_str.strip())
                if qty_val:
                    ingredient["quantity"] = qty_val
                    if unit:
                        ingredient["unit"] = unit.lower()
            except (ValueError, AttributeError):
                pass

        return ingredient

    def _parse_quantity(self, qty_str: str) -> Optional[float]:
        """
        Parse quantity string to float.
        Handles whole numbers, decimals, and simple fractions.
        """
        qty_str = qty_str.strip()

        # Try simple float conversion
        try:
            return float(qty_str)
        except ValueError:
            pass

        # Try fraction (e.g., "1/2", "2 1/3")
        if "/" in qty_str:
            parts = qty_str.split()
            if len(parts) == 1:
                # Simple fraction like "1/2"
                try:
                    num, denom = parts[0].split("/")
                    return float(num) / float(denom)
                except (ValueError, ZeroDivisionError):
                    return None
            elif len(parts) == 2:
                # Mixed number like "2 1/3"
                try:
                    whole = float(parts[0])
                    num, denom = parts[1].split("/")
                    return whole + float(num) / float(denom)
                except (ValueError, ZeroDivisionError):
                    return None

        return None

    def _extract_steps(
        self, ocr_lines: List[OCRLineData], steps_indices: List[int], asset_id: str
    ) -> List[Tuple]:
        """
        Extract cooking steps from OCRLines.

        Returns:
            List of tuples: (step_dict, span_dict, field_status_dict)
        """
        steps = []

        # Find steps section start
        start_idx = 0
        if steps_indices:
            start_idx = steps_indices[0] + 1

        # Parse lines in steps section
        step_num = 0
        for idx in range(start_idx, len(ocr_lines)):
            line = ocr_lines[idx]
            text = line.text.strip()

            # Skip empty lines
            if not text:
                continue

            # Skip if looks like a section header
            if any(
                ind in text.lower()
                for ind in list(self.INGREDIENT_INDICATORS) + list(self.TITLE_INDICATORS)
            ):
                break

            # Create step entry
            step = {"text": text}
            span = {
                "field_path": f"steps[{len(steps)}].text",
                "asset_id": asset_id,
                "page": line.page,
                "bbox": line.bbox,
                "ocr_confidence": line.confidence,
                "extracted_text": text,
            }

            status = {
                "field_path": f"steps[{len(steps)}].text",
                "status": "extracted",
            }

            steps.append((step, span, status))

        return steps

    def _extract_servings(
        self, ocr_lines: List[OCRLineData], asset_id: str
    ) -> Optional[Tuple]:
        """
        Extract servings information from OCRLines.

        Returns:
            Tuple of (servings_int, span_dict, field_status_dict) or None
        """
        for line in ocr_lines:
            text = line.text.lower()

            # Check if line mentions servings
            if any(ind in text for ind in self.SERVINGS_INDICATORS):
                match = self.servings_pattern.search(text)
                if match:
                    servings = int(match.group(1))
                    span = {
                        "field_path": "servings",
                        "asset_id": asset_id,
                        "page": line.page,
                        "bbox": line.bbox,
                        "ocr_confidence": line.confidence,
                        "extracted_text": line.text.strip(),
                    }

                    status = {
                        "field_path": "servings",
                        "status": "extracted",
                    }

                    return (servings, span, status)

        return None
