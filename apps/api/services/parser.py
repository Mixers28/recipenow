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
    STEP_VERBS = {
        "add",
        "bake",
        "beat",
        "bring",
        "combine",
        "cook",
        "cover",
        "drain",
        "fold",
        "heat",
        "mix",
        "place",
        "pour",
        "preheat",
        "reduce",
        "remove",
        "return",
        "roll",
        "season",
        "serve",
        "simmer",
        "stir",
        "whisk",
    }
    UNIT_TOKENS = {
        "tsp",
        "tbsp",
        "teaspoon",
        "teaspoons",
        "tablespoon",
        "tablespoons",
        "cup",
        "cups",
        "g",
        "kg",
        "gram",
        "grams",
        "mg",
        "ml",
        "l",
        "oz",
        "lb",
        "lbs",
        "pound",
        "pounds",
        "pinch",
        "clove",
        "cloves",
        "can",
        "cans",
        "package",
        "packages",
        "slice",
        "slices",
        "bunch",
        "bunches",
        "sprig",
        "sprigs",
    }
    NOISE_PHRASES = {
        "nutrition",
        "calories",
        "kcal",
        "protein",
        "carbohydrate",
        "carb",
        "fat",
        "fiber",
        "fibre",
        "sugar",
        "sodium",
        "dietary",
        "healthy",
        "nut-free",
        "nut free",
        "pregnancy",
        "exercise",
        "recovery",
        "refuel",
        "refueling",
        "per serving",
        "print",
        "share",
        "save",
        "shopping list",
        "shop",
        "http",
        "www.",
        "copyright",
        "©",
    }

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
        self.step_prefix_pattern = re.compile(r"^\s*(step\s*)?\d+[\).\:-]?\s+", re.IGNORECASE)
        self.bullet_pattern = re.compile(r"^\s*[\-\*•]\s+")

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
        title_result = self._extract_title(ocr_lines, sections.get("title_indices", []), asset_id)
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
        ingredient_range = self._find_ingredient_range(
            ocr_lines,
            sections.get("ingredients_indices", []),
            sections.get("steps_indices", []),
        )
        ingredient_results = self._extract_ingredients(ocr_lines, ingredient_range, asset_id)
        recipe["ingredients"] = [r[0] for r in ingredient_results]
        spans.extend([r[1] for r in ingredient_results if r[1]])
        field_statuses.extend([r[2] for r in ingredient_results if r[2]])

        if not ingredient_results and ingredient_range:
            fallback_results = self._extract_ingredients(
                ocr_lines,
                ingredient_range,
                asset_id,
                relax_filters=True,
            )
            if fallback_results:
                recipe["ingredients"] = [r[0] for r in fallback_results]
                spans.extend([r[1] for r in fallback_results if r[1]])
                field_statuses.extend([r[2] for r in fallback_results if r[2]])
                ingredient_results = fallback_results

        if not ingredient_results:
            logger.warning(
                f"No ingredients extracted for asset {asset_id}. "
                f"Ingredient indices: {sections.get('ingredients_indices', [])}, "
                f"Ingredient range: {ingredient_range}"
            )
            field_statuses.append(
                {
                    "field_path": "ingredients",
                    "status": "missing",
                    "notes": "Could not detect ingredients section",
                }
            )

        # Extract steps
        steps_start = self._find_steps_start(
            ocr_lines,
            sections.get("steps_indices", []),
            ingredient_range,
        )
        step_results = self._extract_steps(ocr_lines, steps_start, asset_id)
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
            if self._looks_like_header(lower_text) and any(
                ind in lower_text for ind in self.INGREDIENT_INDICATORS
            ):
                sections["ingredients_indices"].append(i)
                logger.debug(f"Found ingredients header at line {i}: '{line.text[:50]}'")

            if self._looks_like_header(lower_text) and any(
                ind in lower_text for ind in self.STEPS_INDICATORS
            ):
                sections["steps_indices"].append(i)
                logger.debug(f"Found steps header at line {i}: '{line.text[:50]}'")

            if self._looks_like_header(lower_text) and any(
                ind in lower_text for ind in self.TITLE_INDICATORS
            ):
                sections["title_indices"].append(i)
                logger.debug(f"Found title header at line {i}: '{line.text[:50]}'")

        # If no explicit indicators found, use heuristics
        if not sections["title_indices"] and ocr_lines:
            # Usually title is near the top
            sections["title_indices"] = [0]

        return sections

    def _extract_title(
        self, ocr_lines: List[OCRLineData], title_indices: List[int], asset_id: str
    ) -> Optional[Tuple]:
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

        title_text = line.text.strip()
        if not title_text or self._is_noise_line(title_text):
            return None

        # Avoid long descriptive sentences as titles
        if len(title_text) > 120 or (". " in title_text and len(title_text.split()) > 8):
            for candidate in ocr_lines[:8]:
                candidate_text = candidate.text.strip()
                if not candidate_text:
                    continue
                if self._is_noise_line(candidate_text):
                    continue
                if len(candidate_text.split()) <= 8 and len(candidate_text) <= 80:
                    line = candidate
                    title_text = candidate_text
                    break

        span = {
            "field_path": "title",
            "asset_id": asset_id,
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
        self,
        ocr_lines: List[OCRLineData],
        ingredient_range: Optional[Tuple[int, int]],
        asset_id: str,
        relax_filters: bool = False,
    ) -> List[Tuple]:
        """
        Extract ingredients from OCRLines.

        Returns:
            List of tuples: (ingredient_dict, span_dict, field_status_dict)
        """
        ingredients = []

        if not ingredient_range:
            return ingredients

        start_idx, end_idx = ingredient_range

        # Parse lines in ingredient section
        for idx in range(start_idx, end_idx):
            line = ocr_lines[idx]
            text = line.text.strip()

            # Skip empty lines
            if not text:
                continue

            # Stop at next section header
            if self._looks_like_header(text):
                continue

            if self._is_noise_line(text):
                continue
            lower_text = text.lower()
            if lower_text.startswith("for ") or lower_text.startswith("for the "):
                continue
            if text.endswith(":"):
                continue
            if any(ind in lower_text for ind in self.TIME_INDICATORS) and re.search(r"\d", lower_text):
                continue
            if not relax_filters:
                if self._is_step_candidate(text):
                    continue
                if not self._looks_like_ingredient(text):
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
        self, ocr_lines: List[OCRLineData], start_idx: Optional[int], asset_id: str
    ) -> List[Tuple]:
        """
        Extract cooking steps from OCRLines.

        Returns:
            List of tuples: (step_dict, span_dict, field_status_dict)
        """
        steps = []

        if start_idx is None:
            return steps

        # Parse lines in steps section
        current_step_idx = None
        for idx in range(start_idx, len(ocr_lines)):
            line = ocr_lines[idx]
            text = line.text.strip()

            # Skip empty lines
            if not text:
                continue

            if self._looks_like_header(text):
                if current_step_idx is None:
                    continue
                break

            if self._is_noise_line(text):
                continue

            if not self._is_step_candidate(text):
                if current_step_idx is not None:
                    steps[current_step_idx][0]["text"] += f" {text}"
                    steps[current_step_idx][1]["extracted_text"] += f" {text}"
                continue

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
            current_step_idx = len(steps) - 1

        return steps

    def _looks_like_header(self, text: str) -> bool:
        lower_text = text.lower().strip().rstrip(":")
        # Relaxed: allow up to 50 chars (was 30) for headers with badges/metadata
        if len(lower_text) > 50:
            return False
        tokens = re.split(r"\s+", lower_text)
        if not tokens:
            return False
        indicators = self.INGREDIENT_INDICATORS | self.STEPS_INDICATORS | self.TITLE_INDICATORS
        # Exact match (e.g., "ingredients")
        if lower_text in indicators:
            return True
        # First word match with <= 3 tokens (was 2)
        if tokens[0] in indicators and len(tokens) <= 3:
            return True
        # Check if any indicator word appears in the text (new)
        if any(ind in lower_text for ind in indicators):
            return True
        return False

    def _is_noise_line(self, text: str) -> bool:
        lower_text = text.lower()
        if any(phrase in lower_text for phrase in self.NOISE_PHRASES):
            return True
        if len(lower_text.split()) <= 2 and lower_text in {"cook", "prep", "serve", "dietary"}:
            return True
        return False

    def _looks_like_ingredient(self, text: str) -> bool:
        lower_text = text.lower()
        if self.step_prefix_pattern.match(lower_text):
            return False
        if self.bullet_pattern.match(lower_text):
            return True
        if self.quantity_pattern.match(lower_text):
            return True
        tokens = re.split(r"[^a-zA-Z]+", lower_text)
        if any(token in self.UNIT_TOKENS for token in tokens):
            return True
        return False

    def _is_step_candidate(self, text: str) -> bool:
        lower_text = text.lower().strip()
        if self.step_prefix_pattern.match(lower_text):
            return True
        if self.bullet_pattern.match(lower_text):
            return True
        first_word = re.split(r"[^a-zA-Z]+", lower_text)[0]
        if first_word in self.STEP_VERBS:
            return True
        return False

    def _find_ingredient_range(
        self,
        ocr_lines: List[OCRLineData],
        ingredient_indices: List[int],
        steps_indices: List[int],
    ) -> Optional[Tuple[int, int]]:
        if ingredient_indices:
            start_idx = ingredient_indices[0] + 1
            end_idx = steps_indices[0] if steps_indices else len(ocr_lines)
            return (start_idx, end_idx)

        start_idx = None
        for idx, line in enumerate(ocr_lines):
            text = line.text.strip()
            if not text or self._looks_like_header(text) or self._is_noise_line(text):
                continue
            if self._looks_like_ingredient(text):
                start_idx = idx
                break

        if start_idx is None:
            return None

        end_idx = start_idx
        gap = 0
        max_gap = 2
        for idx in range(start_idx, len(ocr_lines)):
            text = ocr_lines[idx].text.strip()
            if not text:
                gap += 1
                if gap > max_gap:
                    break
                continue
            if self._looks_like_header(text) or self._is_step_candidate(text):
                break
            if self._is_noise_line(text):
                gap += 1
                if gap > max_gap:
                    break
                continue
            if self._looks_like_ingredient(text):
                end_idx = idx + 1
                gap = 0
            else:
                gap += 1
                if gap > max_gap:
                    break

        return (start_idx, end_idx)

    def _find_steps_start(
        self,
        ocr_lines: List[OCRLineData],
        steps_indices: List[int],
        ingredient_range: Optional[Tuple[int, int]],
    ) -> Optional[int]:
        if steps_indices:
            return steps_indices[0] + 1

        start_idx = ingredient_range[1] if ingredient_range else 0
        for idx in range(start_idx, len(ocr_lines)):
            text = ocr_lines[idx].text.strip()
            if not text or self._looks_like_header(text) or self._is_noise_line(text):
                continue
            if self._is_step_candidate(text):
                return idx

        return None

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
