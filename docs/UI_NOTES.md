# UI Flow Notes

These notes translate `docs/SPEC.md` into concrete review and pantry flows.

## Review UI (Split View)

Layout
- Left: media viewer (image/PDF page) with zoom + pan.
- Right: editable recipe form with sections for title, servings, times,
  ingredients, steps, tags, nutrition.

Interactions
- Clicking a field highlights its provenance bbox on the left.
- Hovering a bbox highlights the matching field on the right.
- Each field shows a badge: extracted, user-entered, or missing.
- Edits flip FieldStatus to user-entered and clear or replace spans.

Verification
- "Mark Verified" button remains disabled until title, 1+ ingredient, and 1+ step
  are present.
- Missing times/servings keep status at needs_review unless user confirms
  "unknown".

Edge Cases
- Multi-column pages: allow manual region selection to re-run OCR/parse.
- Ambiguous values prompt user questions instead of filling automatically.

## Pantry + Match Flow

Pantry
- List view with item name and optional quantity.
- Quick add with typeahead against normalized ingredient names.

Match
- "Suggest Recipes" triggers match API.
- Results show match percent and missing items list (required vs optional).
- Missing items can be sent to a shopping list in one action.

Cook Mode
- Step-by-step view with ingredient checklist.
- Toggle between original text and normalized ingredient names.

## Wireframe Notes (V1)

Library
- Search bar, filters (status/tags/source), sort controls.
- Card list with status badge and last updated.

Review
- Split view layout with persistent badge legend.
- Ingredients and steps in editable list form.
- Inline "add span" action for manual provenance.

Match
- Progress bar for match percent.
- Required vs optional missing split into two lists.
- "Add all to shopping list" action.
