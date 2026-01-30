-- Migration: Add thumbnail_crop column for meal photo selection
-- Allows users to select a portion of the uploaded image to display as the recipe card thumbnail

ALTER TABLE recipes ADD COLUMN IF NOT EXISTS thumbnail_crop JSONB;

-- Add a comment explaining the column
COMMENT ON COLUMN recipes.thumbnail_crop IS 'JSON object with {x, y, width, height} percentages for cropping meal photo from uploaded image';
