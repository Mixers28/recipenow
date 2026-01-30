-- Migration: Add file_data column for persistent image storage
-- Railway containers have ephemeral storage, so we store images in the database

ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS file_data BYTEA;

-- Add a comment explaining the column
COMMENT ON COLUMN media_assets.file_data IS 'Raw file bytes stored in DB for Railway ephemeral storage compatibility';
