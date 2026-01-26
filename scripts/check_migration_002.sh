#!/bin/bash
# Check if migration 002 has already been applied
# Usage: ./scripts/check_migration_002.sh [DATABASE_URL]

set -e

DATABASE_URL="${1:-$DATABASE_URL}"

if [ -z "$DATABASE_URL" ]; then
  echo "Error: DATABASE_URL not provided"
  echo "Usage: ./check_migration_002.sh postgresql://user:pass@host:port/dbname"
  exit 1
fi

echo "🔍 Checking migration 002 status..."
echo ""

# Check if source_method column exists
echo "Checking for source_method column in source_spans table..."
COLUMN_EXISTS=$(psql "$DATABASE_URL" -t -c "
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_name='source_spans'
    AND column_name='source_method';
")

COLUMN_EXISTS=$(echo $COLUMN_EXISTS | xargs)

if [ "$COLUMN_EXISTS" = "1" ]; then
  echo "✅ Migration 002 already applied - source_method column exists"

  # Show column details
  echo ""
  echo "Column details:"
  psql "$DATABASE_URL" -c "
    SELECT column_name, data_type, column_default, is_nullable
    FROM information_schema.columns
    WHERE table_name='source_spans'
      AND column_name='source_method';
  "

  # Check indexes
  echo ""
  echo "Checking indexes..."
  psql "$DATABASE_URL" -c "
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE tablename = 'source_spans'
      AND (indexname LIKE '%source_method%');
  "

  exit 0
else
  echo "⚠️  Migration 002 NOT applied - source_method column missing"
  echo ""
  echo "Current source_spans columns:"
  psql "$DATABASE_URL" -c "
    SELECT column_name, data_type, column_default
    FROM information_schema.columns
    WHERE table_name='source_spans'
    ORDER BY ordinal_position;
  "

  exit 1
fi
