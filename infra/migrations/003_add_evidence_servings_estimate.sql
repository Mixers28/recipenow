-- Migration: Add evidence to source_spans and servings_estimate to recipes
-- Purpose: Support vision-primary extraction with OCR evidence IDs
-- Version: 003
-- Created: Vision-primary alignment

-- Add servings_estimate to recipes
ALTER TABLE recipes
ADD COLUMN IF NOT EXISTS servings_estimate JSONB;

-- Add evidence JSON to source_spans
ALTER TABLE source_spans
ADD COLUMN IF NOT EXISTS evidence JSONB;

-- Backfill source_method default if missing
ALTER TABLE source_spans
ALTER COLUMN source_method SET DEFAULT 'ocr';

-- Index for evidence queries (optional JSONB GIN)
CREATE INDEX IF NOT EXISTS idx_source_spans_evidence_gin
ON source_spans USING GIN (evidence);
