-- RecipeNow V1 Schema (Postgres 16)
-- Multi-user support: all user-scoped tables include user_id
-- UUIDs for all primary keys

-- MediaAsset: Uploaded recipe images/PDFs
CREATE TABLE media_assets (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  type VARCHAR(10) NOT NULL CHECK (type IN ('image', 'pdf')),
  sha256 VARCHAR(64) NOT NULL,
  storage_path TEXT NOT NULL,
  source_label VARCHAR(255),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_media_assets_user_id ON media_assets (user_id);
CREATE INDEX ix_media_assets_user_sha256 ON media_assets (user_id, sha256);
CREATE INDEX ix_media_assets_user_created ON media_assets (user_id, created_at DESC);

-- OCRLine: OCR-extracted text with bounding boxes
CREATE TABLE ocr_lines (
  id UUID PRIMARY KEY,
  asset_id UUID NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
  page INTEGER NOT NULL DEFAULT 0,
  text TEXT NOT NULL,
  bbox JSONB NOT NULL,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_ocr_lines_asset_id ON ocr_lines (asset_id);

-- Recipe: Complete recipe with status and timestamps
CREATE TABLE recipes (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  title VARCHAR(255),
  servings INTEGER,
  times JSONB,
  ingredients JSONB NOT NULL DEFAULT '[]',
  steps JSONB NOT NULL DEFAULT '[]',
  tags JSONB NOT NULL DEFAULT '[]',
  nutrition JSONB,
  status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'needs_review', 'verified')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMPTZ
);

CREATE INDEX ix_recipes_user_id ON recipes (user_id);
CREATE INDEX ix_recipes_status ON recipes (status);
CREATE INDEX ix_recipes_user_status ON recipes (user_id, status);
CREATE INDEX ix_recipes_user_created ON recipes (user_id, created_at DESC);
CREATE INDEX ix_recipes_deleted_at ON recipes (deleted_at) WHERE deleted_at IS NOT NULL;

-- SourceSpan: Provenance linking fields to OCR sources
CREATE TABLE source_spans (
  id UUID PRIMARY KEY,
  recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  field_path VARCHAR(255) NOT NULL,
  asset_id UUID NOT NULL REFERENCES media_assets(id),
  page INTEGER NOT NULL DEFAULT 0,
  bbox JSONB NOT NULL,
  ocr_confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  extracted_text TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_source_spans_recipe_id ON source_spans (recipe_id);
CREATE INDEX ix_source_spans_recipe_field ON source_spans (recipe_id, field_path);
CREATE INDEX ix_source_spans_asset_id ON source_spans (asset_id);

-- FieldStatus: Status badges for recipe fields
CREATE TABLE field_statuses (
  id UUID PRIMARY KEY,
  recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  field_path VARCHAR(255) NOT NULL,
  status VARCHAR(20) NOT NULL CHECK (status IN ('missing', 'extracted', 'user_entered', 'verified')),
  notes TEXT
);

CREATE INDEX ix_field_statuses_recipe_id ON field_statuses (recipe_id);
CREATE INDEX ix_field_statuses_recipe_field ON field_statuses (recipe_id, field_path);
CREATE UNIQUE INDEX ix_field_statuses_unique ON field_statuses (recipe_id, field_path);

-- PantryItem: User's pantry for recipe matching
CREATE TABLE pantry_items (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  name_original VARCHAR(255) NOT NULL,
  name_norm VARCHAR(255) NOT NULL,
  quantity DOUBLE PRECISION,
  unit VARCHAR(50),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_pantry_items_user_id ON pantry_items (user_id);
CREATE INDEX ix_pantry_items_user_norm ON pantry_items (user_id, name_norm);
CREATE INDEX ix_pantry_items_user_created ON pantry_items (user_id, created_at DESC);
