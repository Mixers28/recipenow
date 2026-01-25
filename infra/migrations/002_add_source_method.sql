-- Migration: Add source_method to source_spans for tracking OCR vs LLM extraction
-- Purpose: Enable audit trail of which method extracted each recipe field
-- Version: 002
-- Created: Sprint 2 Implementation

-- Add source_method column to source_spans table
ALTER TABLE source_spans
ADD COLUMN IF NOT EXISTS source_method VARCHAR(20) DEFAULT 'ocr' NOT NULL;

-- Create index for efficient filtering by source method
CREATE INDEX IF NOT EXISTS idx_source_spans_source_method 
ON source_spans(source_method);

-- Create composite index for recipe + source method queries
CREATE INDEX IF NOT EXISTS idx_source_spans_recipe_method 
ON source_spans(recipe_id, source_method);

-- Add comment for documentation
COMMENT ON COLUMN source_spans.source_method IS 
'Method used to extract this span: "ocr" for OCR extraction, "llm-vision" for LLM vision reader fallback';
