"""
Background jobs and async task processing for RecipeNow.
"""
import re
from typing import Optional


def _extract_ingredient_name(original_text: str) -> Optional[str]:
    """
    Extract ingredient name from text containing quantities and units.

    Examples:
        "2 cups all-purpose flour" -> "flour"
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

    # Remove trailing qualifiers
    text = re.sub(r'\s+(or\s+)?(.*)$', '', text).strip()

    # Clean up remaining whitespace and special characters
    text = re.sub(r'\s+', ' ', text).strip()

    return text if text else None
