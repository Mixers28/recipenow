"""
Utility functions for ingredient text processing.
Shared between API routers and worker jobs.
"""
import re
from typing import Optional


def extract_ingredient_name(original_text: str) -> Optional[str]:
    """
    Extract normalized ingredient name from original text.

    Examples:
        "2 cups all-purpose flour" -> "flour"
        "3 large eggs" -> "egg"
        "salt and pepper to taste" -> "salt and pepper"
        "1.5 tbsp olive oil" -> "olive oil"
        "salt" -> "salt"

    Args:
        original_text: Raw ingredient text with possible quantities/units

    Returns:
        Normalized ingredient name, or None if cannot extract
    """
    if not original_text or not original_text.strip():
        return None

    text = original_text.strip().lower()

    # Common quantity and unit patterns
    quantity_pattern = r'^[\d\s\-./½⅓¼¾⅔⅛⅜⅝⅞\(\)]+(?:tsp|tbsp|cup|cups|oz|ml|l|g|kg|lb|lbs|pinch|dash|handful|to\s+)?'

    # Remove leading quantities and units
    text = re.sub(quantity_pattern, '', text, flags=re.IGNORECASE).strip()

    # Remove common qualifier words at the start
    qualifiers = r'^(fresh|dried|ground|powdered|minced|chopped|sliced|grated|melted|softened|cooked|raw|roasted)\s+'
    text = re.sub(qualifiers, '', text, flags=re.IGNORECASE).strip()

    # Remove trailing notes in parentheses or after comma
    text = re.sub(r'\s*\(.*?\)\s*', ' ', text)
    text = re.sub(r'\s*,.*$', '', text)

    # Remove common descriptors (optional, to taste, etc.)
    text = re.sub(
        r'\s*(optional|to taste|if desired)\s*',
        ' ',
        text,
        flags=re.IGNORECASE,
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

    # Clean up remaining whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text if text else None
