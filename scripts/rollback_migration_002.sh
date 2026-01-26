#!/bin/bash
# Rollback migration 002 (remove source_method column)
# Usage: ./scripts/rollback_migration_002.sh [DATABASE_URL]
# WARNING: Only use if migration 002 causes issues

set -e

DATABASE_URL="${1:-$DATABASE_URL}"

if [ -z "$DATABASE_URL" ]; then
  echo "Error: DATABASE_URL not provided"
  echo "Usage: ./rollback_migration_002.sh postgresql://user:pass@host:port/dbname"
  exit 1
fi

echo "⚠️  ROLLBACK Migration 002"
echo "=================================================="
echo ""
echo "This will remove:"
echo "  - source_method column from source_spans"
echo "  - idx_source_spans_source_method index"
echo "  - idx_source_spans_recipe_method index"
echo ""

read -p "Are you sure you want to rollback? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "Rollback cancelled"
  exit 0
fi

echo ""
echo "1️⃣  Backing up current data..."
echo ""

# Count records with non-default source_method
NON_DEFAULT=$(psql "$DATABASE_URL" -t -c "
  SELECT COUNT(*)
  FROM source_spans
  WHERE source_method != 'ocr';
" 2>/dev/null || echo "0")
NON_DEFAULT=$(echo $NON_DEFAULT | xargs)

if [ "$NON_DEFAULT" != "0" ]; then
  echo "⚠️  WARNING: $NON_DEFAULT records have source_method != 'ocr'"
  echo "   Rolling back will lose this data!"
  echo ""
  read -p "Continue? (yes/no): " CONFIRM2
  if [ "$CONFIRM2" != "yes" ]; then
    echo "Rollback cancelled"
    exit 0
  fi
fi

echo ""
echo "2️⃣  Dropping indexes..."
echo ""

psql "$DATABASE_URL" -c "
  DROP INDEX IF EXISTS idx_source_spans_source_method;
  DROP INDEX IF EXISTS idx_source_spans_recipe_method;
"

if [ $? -eq 0 ]; then
  echo "✅ Indexes dropped"
else
  echo "❌ Failed to drop indexes"
  exit 1
fi

echo ""
echo "3️⃣  Dropping source_method column..."
echo ""

psql "$DATABASE_URL" -c "
  ALTER TABLE source_spans DROP COLUMN IF EXISTS source_method;
"

if [ $? -eq 0 ]; then
  echo "✅ source_method column dropped"
else
  echo "❌ Failed to drop column"
  exit 1
fi

echo ""
echo "4️⃣  Verifying rollback..."
echo ""

# Verify column removed
COLUMN_EXISTS=$(psql "$DATABASE_URL" -t -c "
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_name='source_spans'
    AND column_name='source_method';
")
COLUMN_EXISTS=$(echo $COLUMN_EXISTS | xargs)

if [ "$COLUMN_EXISTS" = "0" ]; then
  echo "✅ source_method column removed"
else
  echo "❌ source_method column still exists!"
  exit 1
fi

echo ""
echo "=================================================="
echo "✅ Migration 002 rolled back successfully"
echo ""
echo "Next steps:"
echo "  1. Restart application services"
echo "  2. Verify application works with old schema"
echo "  3. Check logs for errors"
echo ""
